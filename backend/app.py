"""
Backend API for Readwise to Twos Sync
Handles authentication, user management, and background sync jobs
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from cryptography.fernet import Fernet
import requests
from celery import Celery
import redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///readwise_sync.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CORS for Vercel frontend
CORS(app, origins=[
    'https://readwise-twos-sync.vercel.app',
    'http://localhost:3000',  # For local development
    'http://localhost:5000'
])

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'

# OAuth setup
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Encryption for API tokens
encryption_key = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
cipher_suite = Fernet(encryption_key)

# Celery for background jobs
celery = Celery(
    app.import_name,
    broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
)

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # google, apple, facebook
    provider_id = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    credentials = db.relationship('UserCredentials', backref='user', lazy=True, cascade='all, delete-orphan')
    sync_logs = db.relationship('SyncLog', backref='user', lazy=True, cascade='all, delete-orphan')

class UserCredentials(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    readwise_token_encrypted = db.Column(db.Text, nullable=False)
    twos_user_id = db.Column(db.String(100), nullable=False)
    twos_token_encrypted = db.Column(db.Text, nullable=False)
    sync_enabled = db.Column(db.Boolean, default=True)
    sync_time_utc = db.Column(db.String(5), default='09:00')  # HH:MM format
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def encrypt_token(self, token):
        """Encrypt a token for storage"""
        return cipher_suite.encrypt(token.encode()).decode()
    
    def decrypt_token(self, encrypted_token):
        """Decrypt a token for use"""
        return cipher_suite.decrypt(encrypted_token.encode()).decode()
    
    @property
    def readwise_token(self):
        return self.decrypt_token(self.readwise_token_encrypted)
    
    @readwise_token.setter
    def readwise_token(self, value):
        self.readwise_token_encrypted = self.encrypt_token(value)
    
    @property
    def twos_token(self):
        return self.decrypt_token(self.twos_token_encrypted)
    
    @twos_token.setter
    def twos_token(self, value):
        self.twos_token_encrypted = self.encrypt_token(value)

class SyncLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    sync_date = db.Column(db.Date, nullable=False)
    highlights_count = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), nullable=False)  # success, error, skipped
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Authentication Routes
@app.route('/auth/login/<provider>')
def login(provider):
    """Initiate OAuth login"""
    if provider == 'google':
        redirect_uri = url_for('auth_callback', provider='google', _external=True)
        return google.authorize_redirect(redirect_uri)
    else:
        return jsonify({'error': 'Provider not supported'}), 400

@app.route('/auth/callback/<provider>')
def auth_callback(provider):
    """Handle OAuth callback"""
    if provider == 'google':
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            # Find or create user
            user = User.query.filter_by(provider='google', provider_id=user_info['sub']).first()
            
            if not user:
                user = User(
                    email=user_info['email'],
                    name=user_info['name'],
                    provider='google',
                    provider_id=user_info['sub']
                )
                db.session.add(user)
                db.session.commit()
            
            login_user(user)
            
            # Redirect to frontend with success
            frontend_url = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
            return redirect(f"{frontend_url}/dashboard?login=success")
    
    # Redirect to frontend with error
    frontend_url = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
    return redirect(f"{frontend_url}/?login=error")

@app.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/auth/user')
@login_required
def get_user():
    """Get current user info"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'provider': current_user.provider
    })

# API Routes
@app.route('/api/credentials', methods=['GET'])
@login_required
def get_credentials():
    """Get user's sync credentials (without sensitive data)"""
    creds = UserCredentials.query.filter_by(user_id=current_user.id).first()
    
    if not creds:
        return jsonify({'configured': False})
    
    return jsonify({
        'configured': True,
        'twos_user_id': creds.twos_user_id,
        'sync_enabled': creds.sync_enabled,
        'sync_time_utc': creds.sync_time_utc,
        'readwise_token_preview': creds.readwise_token[:8] + '...' if creds.readwise_token else None,
        'twos_token_preview': creds.twos_token[:8] + '...' if creds.twos_token else None
    })

@app.route('/api/credentials', methods=['POST'])
@login_required
def save_credentials():
    """Save or update user's API credentials"""
    data = request.get_json()
    
    required_fields = ['readwise_token', 'twos_user_id', 'twos_token']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Find or create credentials
    creds = UserCredentials.query.filter_by(user_id=current_user.id).first()
    
    if not creds:
        creds = UserCredentials(user_id=current_user.id)
        db.session.add(creds)
    
    # Update credentials
    creds.readwise_token = data['readwise_token']
    creds.twos_user_id = data['twos_user_id']
    creds.twos_token = data['twos_token']
    creds.sync_enabled = data.get('sync_enabled', True)
    creds.sync_time_utc = data.get('sync_time_utc', '09:00')
    creds.updated_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'Credentials saved successfully'})

@app.route('/api/sync/toggle', methods=['POST'])
@login_required
def toggle_sync():
    """Enable/disable sync for user"""
    creds = UserCredentials.query.filter_by(user_id=current_user.id).first()
    
    if not creds:
        return jsonify({'error': 'No credentials found'}), 404
    
    creds.sync_enabled = not creds.sync_enabled
    creds.updated_at = datetime.utcnow()
    db.session.commit()
    
    return jsonify({
        'sync_enabled': creds.sync_enabled,
        'message': f"Sync {'enabled' if creds.sync_enabled else 'disabled'}"
    })

@app.route('/api/sync/manual', methods=['POST'])
@login_required
def manual_sync():
    """Trigger manual sync for user"""
    creds = UserCredentials.query.filter_by(user_id=current_user.id).first()
    
    if not creds:
        return jsonify({'error': 'No credentials configured'}), 404
    
    # Queue sync job
    sync_user_highlights.delay(current_user.id)
    
    return jsonify({'message': 'Sync started! Check back in a few minutes.'})

@app.route('/api/sync/history')
@login_required
def sync_history():
    """Get user's sync history"""
    logs = SyncLog.query.filter_by(user_id=current_user.id)\
                       .order_by(SyncLog.created_at.desc())\
                       .limit(30).all()
    
    return jsonify([{
        'date': log.sync_date.isoformat(),
        'highlights_count': log.highlights_count,
        'status': log.status,
        'error_message': log.error_message,
        'created_at': log.created_at.isoformat()
    } for log in logs])

# Background Tasks
@celery.task
def sync_user_highlights(user_id):
    """Background task to sync highlights for a user"""
    with app.app_context():
        user = User.query.get(user_id)
        creds = UserCredentials.query.filter_by(user_id=user_id).first()
        
        if not user or not creds or not creds.sync_enabled:
            return
        
        try:
            # Fetch highlights from yesterday
            yesterday = datetime.utcnow() - timedelta(days=1)
            since = yesterday.isoformat()
            
            highlights = fetch_highlights_since(creds.readwise_token, since)
            
            if highlights:
                books = fetch_all_books(creds.readwise_token)
                post_highlights_to_twos(highlights, books, creds.twos_user_id, creds.twos_token)
            
            # Log success
            log = SyncLog(
                user_id=user_id,
                sync_date=datetime.utcnow().date(),
                highlights_count=len(highlights),
                status='success'
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"Synced {len(highlights)} highlights for user {user.email}")
            
        except Exception as e:
            # Log error
            log = SyncLog(
                user_id=user_id,
                sync_date=datetime.utcnow().date(),
                highlights_count=0,
                status='error',
                error_message=str(e)
            )
            db.session.add(log)
            db.session.commit()
            
            logger.error(f"Sync failed for user {user.email}: {e}")

@celery.task
def daily_sync_all_users():
    """Daily task to sync all active users"""
    with app.app_context():
        active_users = db.session.query(User.id).join(UserCredentials)\
                                 .filter(UserCredentials.sync_enabled == True).all()
        
        for (user_id,) in active_users:
            sync_user_highlights.delay(user_id)
        
        logger.info(f"Queued sync jobs for {len(active_users)} users")

# Sync utility functions
def fetch_all_books(readwise_token):
    """Fetch all books from Readwise"""
    headers = {"Authorization": f"Token {readwise_token}"}
    books = {}
    next_url = "https://readwise.io/api/v2/books/"
    
    while next_url:
        try:
            response = requests.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for book in data.get("results", []):
                book_id = book.get("id")
                title = book.get("title", "Untitled")
                author = book.get("author", "Unknown")
                
                if title.strip().lower() == "how to use readwise":
                    continue
                
                books[book_id] = {"title": title, "author": author}
            
            next_url = data.get("next")
            
        except requests.RequestException as e:
            logger.error(f"Error fetching books: {e}")
            raise
    
    return books

def fetch_highlights_since(readwise_token, since):
    """Fetch highlights since timestamp"""
    headers = {"Authorization": f"Token {readwise_token}"}
    highlights = []
    next_url = "https://readwise.io/api/v2/highlights/"
    params = {"page_size": 1000}
    
    while next_url:
        try:
            response = requests.get(next_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for highlight in data.get("results", []):
                if highlight.get("updated") and highlight["updated"] > since:
                    highlights.append(highlight)
            
            next_url = data.get("next")
            params = {}
            
        except requests.RequestException as e:
            logger.error(f"Error fetching highlights: {e}")
            raise
    
    return highlights

def post_highlights_to_twos(highlights, books, twos_user_id, twos_token):
    """Post highlights to Twos"""
    api_url = "https://www.twosapp.com/apiV2/user/addToToday"
    headers = {"Content-Type": "application/json"}
    today_title = datetime.now().strftime("%a %b %d, %Y")
    
    if not highlights:
        payload = {
            "text": "No new highlights found.",
            "title": today_title,
            "token": twos_token,
            "user_id": twos_user_id
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to post no-highlights message: {e}")
        return
    
    successful_posts = 0
    for highlight in highlights:
        try:
            book_id = highlight.get("book_id")
            text = highlight.get("text")
            book_meta = books.get(book_id)
            
            if not book_meta:
                continue
            
            title = book_meta["title"]
            author = book_meta["author"]
            note_text = f"{title}, {author}: {text}"
            
            payload = {
                "text": note_text.strip(),
                "title": today_title,
                "token": twos_token,
                "user_id": twos_user_id
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            successful_posts += 1
            
        except requests.RequestException as e:
            logger.error(f"Failed to post highlight: {e}")
    
    return successful_posts

# Health check
@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')