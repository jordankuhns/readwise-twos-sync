"""
Backend API for Readwise to Twos Sync
Handles authentication, database, and scheduled syncs
"""

import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from cryptography.fernet import Fernet
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)

# Handle PostgreSQL URL format for Railway
if app.config['SQLALCHEMY_DATABASE_URI'].startswith('postgres://'):
    app.config['SQLALCHEMY_DATABASE_URI'] = app.config['SQLALCHEMY_DATABASE_URI'].replace('postgres://', 'postgresql://', 1)

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)

# CORS configuration
frontend_url = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
CORS(app, resources={
    r"/api/*": {
        "origins": [frontend_url, "http://localhost:3000", "http://localhost:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# Encryption for API tokens
encryption_key = os.environ.get('ENCRYPTION_KEY')
if encryption_key:
    cipher_suite = Fernet(encryption_key.encode())
else:
    cipher_suite = Fernet(Fernet.generate_key())
    logger.warning("No ENCRYPTION_KEY provided, using generated key (data will be lost on restart)")

# Database Models
class User(db.Model):
    """User model."""
    
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    password = db.Column(db.String(255), nullable=True)  # Nullable for social login
    auth_provider = db.Column(db.String(50), default='local')  # 'local', 'google', 'apple', 'facebook'
    auth_provider_id = db.Column(db.String(255))  # ID from auth provider
    
    # Sync settings
    sync_enabled = db.Column(db.Boolean, default=True)
    sync_time = db.Column(db.String(5), default='09:00')  # Format: "HH:MM"
    sync_frequency = db.Column(db.String(20), default='daily')  # 'daily', 'weekly'
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<User {self.email}>'

class ApiCredential(db.Model):
    """API credentials model."""
    
    __tablename__ = 'api_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Encrypted API tokens
    readwise_token = db.Column(db.Text, nullable=False)
    twos_user_id = db.Column(db.String(255), nullable=False)
    twos_token = db.Column(db.Text, nullable=False)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ApiCredential user_id={self.user_id}>'

class SyncLog(db.Model):
    """Sync log model."""
    
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    status = db.Column(db.String(50), nullable=False)  # 'success', 'failed'
    highlights_synced = db.Column(db.Integer, default=0)
    details = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<SyncLog user_id={self.user_id} status={self.status}>'

# Import sync service functions
import requests

def perform_sync(readwise_token, twos_user_id, twos_token, days_back=7, user_id=None):
    """Perform a sync from Readwise to Twos."""
    logger.info(f"Starting sync for user {user_id}, looking back {days_back} days")
    
    try:
        # Calculate since timestamp
        since_time = datetime.utcnow() - timedelta(days=days_back)
        since = since_time.isoformat()
        
        # Fetch highlights
        highlights = fetch_highlights_since(readwise_token, since)
        
        if highlights:
            # Fetch books metadata
            books = fetch_all_books(readwise_token)
            
            # Post to Twos
            post_highlights_to_twos(highlights, books, twos_user_id, twos_token)
            
            message = f"Successfully synced {len(highlights)} highlights to Twos!"
        else:
            # Still post a message to Twos
            post_highlights_to_twos([], {}, twos_user_id, twos_token)
            message = "No new highlights found, but posted update to Twos."
        
        # Log successful sync
        if user_id:
            log = SyncLog(
                user_id=user_id,
                status="success",
                highlights_synced=len(highlights),
                details=message
            )
            db.session.add(log)
            db.session.commit()
        
        return {
            "success": True,
            "message": message,
            "highlights_synced": len(highlights)
        }
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        
        # Log failed sync
        if user_id:
            log = SyncLog(
                user_id=user_id,
                status="failed",
                highlights_synced=0,
                details=str(e)
            )
            db.session.add(log)
            db.session.commit()
        
        raise

def fetch_all_books(readwise_token):
    """Fetch all books from Readwise."""
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
    """Fetch highlights updated since a given timestamp."""
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
    """Post highlights to Twos."""
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

# ---- Authentication Routes ----

@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user."""
    data = request.json
    
    # Check if user already exists
    if User.query.filter_by(email=data['email']).first():
        return jsonify({"error": "Email already registered"}), 400
    
    # Create new user
    user = User(
        email=data['email'],
        name=data.get('name', ''),
        password=generate_password_hash(data['password']) if 'password' in data else None,
        auth_provider=data.get('auth_provider', 'local'),
        auth_provider_id=data.get('auth_provider_id', '')
    )
    
    db.session.add(user)
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        "message": "User registered successfully",
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login a user."""
    data = request.json
    
    # Find user by email
    user = User.query.filter_by(email=data['email']).first()
    
    # Check if user exists and password is correct
    if not user or (user.password and not check_password_hash(user.password, data['password'])):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }), 200

@app.route('/api/auth/social-login', methods=['POST'])
def social_login():
    """Handle social login (Google, Apple, Facebook)."""
    data = request.json
    
    # Find user by provider ID or email
    user = User.query.filter_by(
        auth_provider=data['provider'],
        auth_provider_id=data['provider_id']
    ).first()
    
    if not user:
        # Try to find by email
        user = User.query.filter_by(email=data['email']).first()
        
        if user:
            # Update existing user with provider info
            user.auth_provider = data['provider']
            user.auth_provider_id = data['provider_id']
        else:
            # Create new user
            user = User(
                email=data['email'],
                name=data.get('name', ''),
                auth_provider=data['provider'],
                auth_provider_id=data['provider_id']
            )
            db.session.add(user)
    
    db.session.commit()
    
    # Create access token
    access_token = create_access_token(identity=user.id)
    
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }), 200

# ---- API Credential Routes ----

@app.route('/api/credentials', methods=['POST', 'OPTIONS'])
def save_credentials():
    """Save API credentials for a user."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For POST requests, require JWT
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception as e:
        return jsonify({"error": "Authentication required"}), 401
    
    data = request.json
    
    # Encrypt sensitive data
    encrypted_readwise_token = cipher_suite.encrypt(data['readwise_token'].encode()).decode()
    encrypted_twos_token = cipher_suite.encrypt(data['twos_token'].encode()).decode()
    
    # Check if credentials already exist
    creds = ApiCredential.query.filter_by(user_id=user_id).first()
    
    if creds:
        # Update existing credentials
        creds.readwise_token = encrypted_readwise_token
        creds.twos_user_id = data['twos_user_id']
        creds.twos_token = encrypted_twos_token
        creds.updated_at = datetime.utcnow()
    else:
        # Create new credentials
        creds = ApiCredential(
            user_id=user_id,
            readwise_token=encrypted_readwise_token,
            twos_user_id=data['twos_user_id'],
            twos_token=encrypted_twos_token
        )
        db.session.add(creds)
    
    db.session.commit()
    
    # Note: Scheduling would be implemented with a proper job queue
    
    return jsonify({"message": "Credentials saved successfully"}), 200

@app.route('/api/credentials', methods=['GET'])
@jwt_required()
def get_credentials():
    """Get API credentials for a user."""
    user_id = get_jwt_identity()
    
    creds = ApiCredential.query.filter_by(user_id=user_id).first()
    
    if not creds:
        return jsonify({"message": "No credentials found"}), 404
    
    # Return credentials with masked tokens for security
    return jsonify({
        "readwise_token": "••••••••" + creds.readwise_token[-4:],
        "twos_user_id": creds.twos_user_id,
        "twos_token": "••••••••" + creds.twos_token[-4:],
        "has_credentials": True
    }), 200

# ---- Sync Routes ----

@app.route('/api/sync', methods=['POST'])
@jwt_required()
def trigger_sync():
    """Manually trigger a sync for a user."""
    user_id = get_jwt_identity()
    data = request.json
    days_back = data.get('days_back', 7)
    
    # Get user credentials
    creds = ApiCredential.query.filter_by(user_id=user_id).first()
    
    if not creds:
        return jsonify({"error": "No API credentials found"}), 404
    
    try:
        # Decrypt tokens
        readwise_token = cipher_suite.decrypt(creds.readwise_token.encode()).decode()
        twos_token = cipher_suite.decrypt(creds.twos_token.encode()).decode()
        
        # Perform sync
        result = perform_sync(
            readwise_token=readwise_token,
            twos_user_id=creds.twos_user_id,
            twos_token=twos_token,
            days_back=days_back,
            user_id=user_id
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        
        # Log the error
        log = SyncLog(
            user_id=user_id,
            status="failed",
            details=str(e),
            highlights_synced=0
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({"error": f"Sync failed: {str(e)}"}), 500

@app.route('/api/sync/history', methods=['GET'])
@jwt_required()
def get_sync_history():
    """Get sync history for a user."""
    user_id = get_jwt_identity()
    
    # Get last 10 sync logs
    logs = SyncLog.query.filter_by(user_id=user_id).order_by(SyncLog.created_at.desc()).limit(10).all()
    
    return jsonify({
        "history": [
            {
                "id": log.id,
                "status": log.status,
                "highlights_synced": log.highlights_synced,
                "details": log.details,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }), 200

@app.route('/api/sync/settings', methods=['POST'])
@jwt_required()
def update_sync_settings():
    """Update sync settings for a user."""
    user_id = get_jwt_identity()
    data = request.json
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Update sync settings
    user.sync_enabled = data.get('sync_enabled', user.sync_enabled)
    user.sync_time = data.get('sync_time', user.sync_time)
    user.sync_frequency = data.get('sync_frequency', user.sync_frequency)
    
    db.session.commit()
    
    # Note: Scheduling functionality would be implemented with a proper job queue
    # For now, we'll just update the settings
    
    return jsonify({
        "message": "Sync settings updated",
        "settings": {
            "sync_enabled": user.sync_enabled,
            "sync_time": user.sync_time,
            "sync_frequency": user.sync_frequency
        }
    }), 200

# ---- User Routes ----

@app.route('/api/user', methods=['GET', 'OPTIONS'])
def get_user():
    """Get user profile."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For GET requests, require JWT
    try:
        from flask_jwt_extended import verify_jwt_in_request
        verify_jwt_in_request()
        user_id = get_jwt_identity()
    except Exception as e:
        return jsonify({"error": "Authentication required"}), 401
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Get latest sync
    latest_sync = SyncLog.query.filter_by(user_id=user_id).order_by(SyncLog.created_at.desc()).first()
    
    # Check if user has credentials
    has_credentials = ApiCredential.query.filter_by(user_id=user_id).first() is not None
    
    return jsonify({
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "sync_enabled": user.sync_enabled,
        "sync_time": user.sync_time,
        "sync_frequency": user.sync_frequency,
        "has_credentials": has_credentials,
        "last_sync": {
            "status": latest_sync.status,
            "time": latest_sync.created_at.isoformat(),
            "highlights_synced": latest_sync.highlights_synced
        } if latest_sync else None
    }), 200

@app.route('/api/user', methods=['PUT'])
@jwt_required()
def update_user():
    """Update user profile."""
    user_id = get_jwt_identity()
    data = request.json
    
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Update user fields
    if 'name' in data:
        user.name = data['name']
    
    db.session.commit()
    
    return jsonify({
        "message": "Profile updated",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name
        }
    }), 200

@app.route('/api/user', methods=['DELETE'])
@jwt_required()
def delete_user():
    """Delete user account."""
    user_id = get_jwt_identity()
    
    # Delete user's data
    ApiCredential.query.filter_by(user_id=user_id).delete()
    SyncLog.query.filter_by(user_id=user_id).delete()
    
    # Note: Job removal would be implemented with a proper job queue
    
    # Delete user
    User.query.filter_by(id=user_id).delete()
    
    db.session.commit()
    
    return jsonify({"message": "Account deleted successfully"}), 200

# ---- Helper Functions ----

def schedule_sync_job(user_id):
    """Schedule a daily sync job for a user."""
    user = User.query.get(user_id)
    
    if not user or not user.sync_enabled:
        return
    
    # Parse sync time (format: "HH:MM")
    hour, minute = map(int, user.sync_time.split(':'))
    
    # Remove existing job if it exists
    try:
        scheduler.remove_job(f"sync_user_{user_id}")
    except:
        pass
    
    # Schedule new job
    if user.sync_frequency == 'daily':
        scheduler.add_job(
            run_scheduled_sync,
            'cron',
            hour=hour,
            minute=minute,
            id=f"sync_user_{user_id}",
            args=[user_id]
        )
        logger.info(f"Scheduled daily sync for user {user_id} at {hour}:{minute}")
    elif user.sync_frequency == 'weekly':
        scheduler.add_job(
            run_scheduled_sync,
            'cron',
            day_of_week='mon',
            hour=hour,
            minute=minute,
            id=f"sync_user_{user_id}",
            args=[user_id]
        )
        logger.info(f"Scheduled weekly sync for user {user_id} at {hour}:{minute} on Mondays")

def run_scheduled_sync(user_id):
    """Run a scheduled sync for a user."""
    logger.info(f"Running scheduled sync for user {user_id}")
    
    # Get user credentials
    creds = ApiCredential.query.filter_by(user_id=user_id).first()
    
    if not creds:
        logger.error(f"No credentials found for user {user_id}")
        return
    
    try:
        # Decrypt tokens
        readwise_token = cipher_suite.decrypt(creds.readwise_token.encode()).decode()
        twos_token = cipher_suite.decrypt(creds.twos_token.encode()).decode()
        
        # Perform sync (only 1 day back for scheduled syncs)
        result = perform_sync(
            readwise_token=readwise_token,
            twos_user_id=creds.twos_user_id,
            twos_token=twos_token,
            days_back=1,  # Only sync yesterday's highlights
            user_id=user_id
        )
        
        logger.info(f"Scheduled sync completed for user {user_id}: {result}")
        
    except Exception as e:
        logger.error(f"Scheduled sync failed for user {user_id}: {e}")
        
        # Log the error
        log = SyncLog(
            user_id=user_id,
            status="failed",
            details=str(e),
            highlights_synced=0
        )
        db.session.add(log)
        db.session.commit()

# ---- Global OPTIONS Handler ----

@app.before_request
def handle_preflight():
    """Handle CORS preflight requests."""
    if request.method == "OPTIONS":
        response = jsonify({})
        response.headers.add("Access-Control-Allow-Origin", "*")
        response.headers.add('Access-Control-Allow-Headers', "*")
        response.headers.add('Access-Control-Allow-Methods', "*")
        return response

# ---- Error Handlers ----

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle all exceptions with proper logging."""
    logger.error(f"Unhandled exception: {str(e)}")
    return jsonify({"error": "Internal server error"}), 500

# ---- Health Check ----

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })

if __name__ == '__main__':
    # Create tables if they don't exist
    with app.app_context():
        db.create_all()
    
    # Start the app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)