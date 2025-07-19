"""
Standalone Flask app for Railway deployment
All dependencies included in one file to avoid import issues
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, redirect, url_for, session
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.integrations.flask_client import OAuth
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from cryptography.fernet import Fernet
import requests
from dotenv import load_dotenv
import pytz

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
oauth = OAuth(app)

# Configure Google OAuth
google = oauth.register(
    name='google',
    client_id=os.environ.get('GOOGLE_CLIENT_ID', 'demo-client-id'),
    client_secret=os.environ.get('GOOGLE_CLIENT_SECRET', 'demo-client-secret'),
    server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# CORS configuration
frontend_url = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

# Encryption for API tokens
encryption_key = os.environ.get('ENCRYPTION_KEY')
if encryption_key:
    cipher_suite = Fernet(encryption_key.encode())
else:
    cipher_suite = Fernet(Fernet.generate_key())
    logger.warning("No ENCRYPTION_KEY provided, using generated key")

# Database Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255))
    password_hash = db.Column(db.String(255), nullable=True)
    auth_provider = db.Column(db.String(50), default='local')
    auth_provider_id = db.Column(db.String(255))
    
    sync_enabled = db.Column(db.Boolean, default=True)
    sync_time = db.Column(db.String(5), default='09:00')
    sync_frequency = db.Column(db.String(20), default='daily')
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ApiCredential(db.Model):
    __tablename__ = 'api_credentials'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    readwise_token = db.Column(db.Text, nullable=False)
    twos_user_id = db.Column(db.String(255), nullable=False)
    twos_token = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SyncLog(db.Model):
    __tablename__ = 'sync_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    highlights_synced = db.Column(db.Integer, default=0)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Routes
@app.route('/')
def root():
    return jsonify({
        'message': 'Readwise to Twos Sync API',
        'status': 'running',
        'endpoints': {
            'health': '/health',
            'register': '/api/auth/register',
            'login': '/api/auth/login',
            'google_login': '/auth/login/google'
        }
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/debug')
def debug():
    """Debug endpoint to check if the app is running."""
    logger.info("Debug endpoint called")
    
    # Get all users
    users = User.query.all()
    user_count = len(users)
    
    # Get all credentials
    creds = ApiCredential.query.all()
    cred_count = len(creds)
    
    # Get all sync logs
    logs = SyncLog.query.all()
    log_count = len(logs)
    
    return jsonify({
        'message': 'Debug endpoint',
        'user_count': user_count,
        'credential_count': cred_count,
        'log_count': log_count,
        'users': [
            {
                'id': user.id,
                'email': user.email,
                'sync_enabled': user.sync_enabled,
                'sync_time': user.sync_time,
                'sync_frequency': user.sync_frequency
            }
            for user in users
        ],
        'credentials': [
            {
                'id': cred.id,
                'user_id': cred.user_id,
                'twos_user_id': cred.twos_user_id
            }
            for cred in creds
        ],
        'logs': [
            {
                'id': log.id,
                'user_id': log.user_id,
                'status': log.status,
                'highlights_synced': log.highlights_synced,
                'created_at': log.created_at.isoformat() if log.created_at else None
            }
            for log in logs[:10]  # Only show the 10 most recent logs
        ]
    })

@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def register():
    # Handle CORS preflight
    if request.method == 'OPTIONS':
        return '', 200
        
    try:
        # Log request data for debugging
        logger.info(f"Registration request received")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request data: {request.data}")
        
        # Handle both JSON and form data
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()
        
        logger.info(f"Parsed data: {data}")
        
        # Validate required fields
        if not data or 'email' not in data or 'password' not in data:
            logger.error(f"Missing required fields: {data}")
            return jsonify({"error": "Email and password are required"}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        if existing_user:
            logger.info(f"User already exists: {data['email']}")
            return jsonify({"error": "Email already registered"}), 400
        
        # Create new user
        user = User(
            email=data['email'],
            name=data.get('name', ''),
            password_hash=generate_password_hash(data['password']),
            auth_provider='local'
        )
        
        logger.info(f"Creating user: {user.email}")
        db.session.add(user)
        db.session.commit()
        logger.info(f"User created successfully: {user.id}")
        
        # Generate token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            "message": "User registered successfully",
            "access_token": access_token,
            "user": {"id": user.id, "email": user.email, "name": user.name}
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        db.session.rollback()
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        # Handle both JSON and form data
        if request.is_json:
            data = request.json
        else:
            data = request.form.to_dict()
        
        logger.info(f"Login attempt for email: {data.get('email', 'unknown')}")
        
        # Validate required fields
        if not data or 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password are required"}), 400
        
        user = User.query.filter_by(email=data['email']).first()
        
        if not user:
            logger.info(f"User not found: {data['email']}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        if user.password_hash and not check_password_hash(user.password_hash, data['password']):
            logger.info(f"Invalid password for user: {data['email']}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        access_token = create_access_token(identity=str(user.id))
        
        logger.info(f"Successful login for user: {data['email']}")
        return jsonify({
            "access_token": access_token,
            "user": {"id": user.id, "email": user.email, "name": user.name}
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({"error": "Login failed"}), 500

@app.route('/auth/login/google')
def google_login():
    """Initiate Google OAuth login"""
    try:
        # Check if we have Google OAuth configured
        if (os.environ.get('GOOGLE_CLIENT_ID', 'demo-client-id') == 'demo-client-id' or 
            os.environ.get('GOOGLE_CLIENT_SECRET', 'demo-client-secret') == 'demo-client-secret'):
            
            # Demo mode - create a test user
            logger.info("Google OAuth not configured, using demo mode")
            user = User.query.filter_by(email="demo@example.com").first()
            
            if not user:
                user = User(
                    email="demo@example.com",
                    name="Demo User (Google)",
                    auth_provider="google",
                    auth_provider_id="demo123"
                )
                db.session.add(user)
                db.session.commit()
                logger.info("Created demo Google user")
            
            # Generate token
            access_token = create_access_token(identity=str(user.id))
            
            # Redirect to frontend with token
            frontend_url = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
            return redirect(f"{frontend_url}/dashboard?token={access_token}")
        
        else:
            # Real Google OAuth
            redirect_uri = url_for('google_callback', _external=True)
            return google.authorize_redirect(redirect_uri)
            
    except Exception as e:
        logger.error(f"Google login error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/auth/callback/google')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        # Get the authorization token
        token = google.authorize_access_token()
        user_info = token.get('userinfo')
        
        if user_info:
            # Find or create user
            user = User.query.filter_by(
                auth_provider='google',
                auth_provider_id=user_info['sub']
            ).first()
            
            if not user:
                # Check if user exists with same email
                user = User.query.filter_by(email=user_info['email']).first()
                if user:
                    # Update existing user with Google info
                    user.auth_provider = 'google'
                    user.auth_provider_id = user_info['sub']
                else:
                    # Create new user
                    user = User(
                        email=user_info['email'],
                        name=user_info.get('name', ''),
                        auth_provider='google',
                        auth_provider_id=user_info['sub']
                    )
                    db.session.add(user)
                
                db.session.commit()
            
            # Generate token
            access_token = create_access_token(identity=str(user.id))
            
            # Redirect to frontend with token
            frontend_url = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
            return redirect(f"{frontend_url}/dashboard?token={access_token}")
        
        else:
            return jsonify({"error": "Failed to get user info from Google"}), 400
            
    except Exception as e:
        logger.error(f"Google callback error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ---- API Credential Routes ----

@app.route('/api/credentials', methods=['POST', 'OPTIONS'])
def save_credentials():
    """Save API credentials for a user."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For POST requests, require JWT
    try:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("No Bearer token found in Authorization header")
            return jsonify({"error": "Authentication required"}), 401
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        # Manually decode the token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        
        logger.info(f"Successfully authenticated user {user_id}")
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        data = request.json
        logger.info(f"Saving credentials for user {user_id}")
        
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
            logger.info(f"Updated credentials for user {user_id}")
        else:
            # Create new credentials
            creds = ApiCredential(
                user_id=user_id,
                readwise_token=encrypted_readwise_token,
                twos_user_id=data['twos_user_id'],
                twos_token=encrypted_twos_token
            )
            db.session.add(creds)
            logger.info(f"Created new credentials for user {user_id}")
        
        db.session.commit()
        
        return jsonify({"message": "Credentials saved successfully"}), 200
    
    except Exception as e:
        logger.error(f"Error saving credentials: {str(e)}")
        db.session.rollback()
        return jsonify({"error": f"Failed to save credentials: {str(e)}"}), 500

@app.route('/api/credentials', methods=['GET', 'OPTIONS'])
def get_credentials():
    """Get API credentials for a user."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For GET requests, require JWT
    try:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("No Bearer token found in Authorization header")
            return jsonify({"error": "Authentication required"}), 401
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        # Manually decode the token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        
        logger.info(f"Successfully authenticated user {user_id}")
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        creds = ApiCredential.query.filter_by(user_id=user_id).first()
        
        if not creds:
            return jsonify({"message": "No credentials found", "has_credentials": False}), 404
        
        # Return credentials with masked tokens for security
        return jsonify({
            "readwise_token": "••••••••" + creds.readwise_token[-4:] if len(creds.readwise_token) > 4 else "••••••••",
            "twos_user_id": creds.twos_user_id,
            "twos_token": "••••••••" + creds.twos_token[-4:] if len(creds.twos_token) > 4 else "••••••••",
            "has_credentials": True
        }), 200
    
    except Exception as e:
        logger.error(f"Error getting credentials: {str(e)}")
        return jsonify({"error": f"Failed to get credentials: {str(e)}"}), 500

# Sync functions
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
    
    # Debug logging
    logger.info(f"Posting to Twos with user_id: {twos_user_id}")
    logger.info(f"Token length: {len(twos_token)}")
    
    if not highlights:
        payload = {
            "text": "No new highlights found.",
            "user_id": twos_user_id,
            "token": twos_token
        }
        
        # Debug logging
        logger.info(f"Sending payload to Twos: {payload}")
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            logger.info(f"Twos API response status: {response.status_code}")
            logger.info(f"Twos API response: {response.text}")
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
                "user_id": twos_user_id,
                "token": twos_token
            }
            
            # Debug logging
            logger.info(f"Sending highlight to Twos: {note_text[:50]}...")
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            logger.info(f"Twos API response status: {response.status_code}")
            if response.status_code != 200:
                logger.info(f"Twos API error response: {response.text}")
            response.raise_for_status()
            successful_posts += 1
            
        except requests.RequestException as e:
            logger.error(f"Failed to post highlight: {e}")
    
    return successful_posts

# ---- Sync Routes ----

@app.route('/api/sync', methods=['POST', 'OPTIONS'])
def trigger_sync():
    """Manually trigger a sync for a user."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For POST requests, require JWT
    try:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("No Bearer token found in Authorization header")
            return jsonify({"error": "Authentication required"}), 401
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        # Manually decode the token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        
        logger.info(f"Successfully authenticated user {user_id}")
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        data = request.json or {}
        days_back = data.get('days_back', 7)
        logger.info(f"Triggering sync for user {user_id} with days_back={days_back}")
        
        # Get user credentials
        creds = ApiCredential.query.filter_by(user_id=user_id).first()
        
        if not creds:
            return jsonify({"error": "No API credentials found"}), 404
        
        # Decrypt tokens
        readwise_token = cipher_suite.decrypt(creds.readwise_token.encode()).decode()
        twos_token = cipher_suite.decrypt(creds.twos_token.encode()).decode()
        
        # Perform actual sync
        try:
            result = perform_sync(
                readwise_token=readwise_token,
                twos_user_id=creds.twos_user_id,
                twos_token=twos_token,
                days_back=days_back,
                user_id=user_id
            )
            
            return jsonify(result), 200
            
        except Exception as e:
            logger.error(f"Sync operation failed: {str(e)}")
            
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
    
    except Exception as e:
        logger.error(f"Error in sync endpoint: {str(e)}")
        return jsonify({"error": f"Sync request failed: {str(e)}"}), 500

@app.route('/api/sync/settings', methods=['POST', 'OPTIONS'])
def update_sync_settings():
    """Update sync settings for a user."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For POST requests, require JWT
    try:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("No Bearer token found in Authorization header")
            return jsonify({"error": "Authentication required"}), 401
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        # Manually decode the token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        
        logger.info(f"Successfully authenticated user {user_id}")
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return jsonify({"error": "Authentication required"}), 401
    
    try:
        data = request.json
        logger.info(f"Updating sync settings for user {user_id}: {data}")
        
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Update sync settings
        if 'sync_enabled' in data:
            user.sync_enabled = data['sync_enabled']
            logger.info(f"Updated sync_enabled to {user.sync_enabled}")
        
        if 'sync_time' in data:
            user.sync_time = data['sync_time']
            logger.info(f"Updated sync_time to {user.sync_time}")
        
        if 'sync_frequency' in data:
            user.sync_frequency = data['sync_frequency']
            logger.info(f"Updated sync_frequency to {user.sync_frequency}")
        
        db.session.commit()
        
        return jsonify({
            "message": "Sync settings updated",
            "settings": {
                "sync_enabled": user.sync_enabled,
                "sync_time": user.sync_time,
                "sync_frequency": user.sync_frequency
            }
        }), 200
    
    except Exception as e:
        logger.error(f"Error updating sync settings: {str(e)}")
        return jsonify({"error": f"Failed to update sync settings: {str(e)}"}), 500

@app.route('/api/sync/history', methods=['GET', 'OPTIONS'])
def get_sync_history():
    """Get sync history for a user."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For GET requests, require JWT
    try:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("No Bearer token found in Authorization header")
            return jsonify({"error": "Authentication required"}), 401
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        # Manually decode the token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        
        logger.info(f"Successfully authenticated user {user_id}")
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return jsonify({"error": "Authentication required"}), 401
    
    try:
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
    
    except Exception as e:
        logger.error(f"Error getting sync history: {str(e)}")
        return jsonify({"error": f"Failed to get sync history: {str(e)}"}), 500

# ---- User Routes ----

@app.route('/api/user', methods=['GET', 'OPTIONS'])
def get_user_profile():
    """Get user profile."""
    # Handle OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    # For GET requests, require JWT
    try:
        # Get the Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            logger.error("No Bearer token found in Authorization header")
            return jsonify({"error": "Authentication required"}), 401
        
        # Extract the token
        token = auth_header.split(' ')[1]
        
        # Manually decode the token
        from flask_jwt_extended import decode_token
        decoded_token = decode_token(token)
        user_id = decoded_token['sub']
        
        logger.info(f"Successfully authenticated user {user_id}")
    except Exception as e:
        logger.error(f"JWT verification failed: {str(e)}")
        return jsonify({"error": "Authentication required"}), 401
    
    try:
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
    
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        return jsonify({"error": f"Failed to get user profile: {str(e)}"}), 500

# ---- Scheduler Functions ----

def schedule_sync_job(user_id):
    """Schedule a daily sync job for a user."""
    user = User.query.get(user_id)
    
    if not user or not user.sync_enabled:
        return
    
    # Parse sync time (format: "HH:MM")
    hour, minute = map(int, user.sync_time.split(':'))
    
    # Get the system's local timezone - detect automatically
    try:
        # Try to get system timezone
        import time
        local_tz_name = time.tzname[time.daylight]
        if local_tz_name in ['CDT', 'CST']:
            local_tz = pytz.timezone('America/Chicago')
        else:
            # Fallback to system timezone
            local_tz = pytz.timezone('America/Chicago')  # Default for this deployment
    except:
        # Fallback to Chicago timezone
        local_tz = pytz.timezone('America/Chicago')
    
    # Remove existing job if it exists
    try:
        scheduler.remove_job(f"sync_user_{user_id}")
    except:
        pass
    
    # Schedule new job with timezone
    if user.sync_frequency == 'daily':
        scheduler.add_job(
            run_scheduled_sync,
            'cron',
            hour=hour,
            minute=minute,
            timezone=local_tz,
            id=f"sync_user_{user_id}",
            args=[user_id]
        )
        logger.info(f"Scheduled daily sync for user {user_id} at {hour}:{minute} {local_tz}")
    elif user.sync_frequency == 'weekly':
        scheduler.add_job(
            run_scheduled_sync,
            'cron',
            day_of_week='mon',
            hour=hour,
            minute=minute,
            timezone=local_tz,
            id=f"sync_user_{user_id}",
            args=[user_id]
        )
        logger.info(f"Scheduled weekly sync for user {user_id} at {hour}:{minute} on Mondays {local_tz}")

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

# ---- Debug Endpoints ----

@app.route('/debug/users', methods=['GET'])
def debug_list_users():
    """List all users for debugging."""
    logger.info("Debug: Listing all users")
    
    try:
        users = User.query.all()
        
        user_list = []
        for user in users:
            # Check if user has credentials
            creds = ApiCredential.query.filter_by(user_id=user.id).first()
            
            user_list.append({
                "id": user.id,
                "email": user.email,
                "sync_enabled": user.sync_enabled,
                "sync_time": user.sync_time,
                "has_credentials": creds is not None,
                "twos_user_id": creds.twos_user_id if creds else None
            })
        
        return jsonify({
            "users": user_list
        }), 200
    except Exception as e:
        logger.error(f"Debug: Error listing users: {e}")
        import traceback
        logger.error(f"Debug: Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Error listing users: {str(e)}"}), 500

@app.route('/debug/trigger-sync/<user_id>', methods=['GET'])
def debug_trigger_sync(user_id):
    """Manually trigger a sync for debugging."""
    logger.info(f"Debug: Manually triggering sync for user {user_id}")
    
    try:
        # Log the user ID
        logger.info(f"Debug: User ID is {user_id}, type: {type(user_id)}")
        
        # Get user credentials
        creds = ApiCredential.query.filter_by(user_id=user_id).first()
        
        if not creds:
            logger.error(f"Debug: No API credentials found for user {user_id}")
            return jsonify({"error": "No API credentials found"}), 404
        
        # Log credential info
        logger.info(f"Debug: Found credentials for user {user_id}")
        logger.info(f"Debug: Twos User ID: {creds.twos_user_id}")
        logger.info(f"Debug: Readwise token length: {len(creds.readwise_token)}")
        logger.info(f"Debug: Twos token length: {len(creds.twos_token)}")
        
        try:
            # Decrypt tokens
            readwise_token = cipher_suite.decrypt(creds.readwise_token.encode()).decode()
            logger.info(f"Debug: Successfully decrypted Readwise token")
            
            twos_token = cipher_suite.decrypt(creds.twos_token.encode()).decode()
            logger.info(f"Debug: Successfully decrypted Twos token")
            
            # Perform sync
            logger.info(f"Debug: Starting sync for user {user_id}")
            result = perform_sync(
                readwise_token=readwise_token,
                twos_user_id=creds.twos_user_id,
                twos_token=twos_token,
                days_back=1,  # Only sync yesterday's highlights
                user_id=user_id
            )
            logger.info(f"Debug: Sync completed successfully: {result}")
            
            return jsonify({
                "message": "Debug sync triggered",
                "result": result
            }), 200
        except Exception as e:
            logger.error(f"Debug: Error during sync: {e}")
            import traceback
            logger.error(f"Debug: Traceback: {traceback.format_exc()}")
            return jsonify({"error": f"Error during sync: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Debug sync failed: {e}")
        import traceback
        logger.error(f"Debug: Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Debug sync failed: {str(e)}"}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Initialize scheduler
    jobstores = {
        'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
    }
    scheduler = BackgroundScheduler(jobstores=jobstores)
    scheduler.start()
    
    # Schedule sync jobs for all users
    with app.app_context():
        users = User.query.filter_by(sync_enabled=True).all()
        for user in users:
            schedule_sync_job(user.id)
    
    # Update sync settings endpoint to reschedule jobs
    old_update_sync_settings = update_sync_settings
    
    def new_update_sync_settings(*args, **kwargs):
        response = old_update_sync_settings(*args, **kwargs)
        
        # Extract user_id from the request
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            try:
                from flask_jwt_extended import decode_token
                decoded_token = decode_token(token)
                user_id = decoded_token['sub']
                
                # Reschedule sync job
                schedule_sync_job(user_id)
            except:
                pass
        
        return response
    
    # Replace the update_sync_settings function
    update_sync_settings = new_update_sync_settings
    
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)