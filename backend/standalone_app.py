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
from cryptography.fernet import Fernet
import requests
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
    password = db.Column(db.String(255), nullable=True)
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
            password=generate_password_hash(data['password']),
            auth_provider='local'
        )
        
        logger.info(f"Creating user: {user.email}")
        db.session.add(user)
        db.session.commit()
        logger.info(f"User created successfully: {user.id}")
        
        # Generate token
        access_token = create_access_token(identity=user.id)
        
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
        
        if user.password and not check_password_hash(user.password, data['password']):
            logger.info(f"Invalid password for user: {data['email']}")
            return jsonify({"error": "Invalid email or password"}), 401
        
        access_token = create_access_token(identity=user.id)
        
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
            access_token = create_access_token(identity=user.id)
            
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
            access_token = create_access_token(identity=user.id)
            
            # Redirect to frontend with token
            frontend_url = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
            return redirect(f"{frontend_url}/dashboard?token={access_token}")
        
        else:
            return jsonify({"error": "Failed to get user info from Google"}), 400
            
    except Exception as e:
        logger.error(f"Google callback error: {str(e)}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    port = int(os.environ.get('PORT', 8000))
    app.run(host='0.0.0.0', port=port, debug=False)