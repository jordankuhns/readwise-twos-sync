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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize extensions
db = SQLAlchemy(app)
jwt = JWTManager(app)
CORS(app, resources={r"/api/*": {"origins": app.config['FRONTEND_URL']}})

# Import models after db initialization to avoid circular imports
from models import User, ApiCredential, SyncLog

# Initialize encryption key
encryption_key = Fernet(app.config['ENCRYPTION_KEY'])

# Initialize scheduler
jobstores = {
    'default': SQLAlchemyJobStore(url=app.config['SQLALCHEMY_DATABASE_URI'])
}
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()

# Import sync service
from sync_service import perform_sync

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

@app.route('/api/credentials', methods=['POST'])
@jwt_required()
def save_credentials():
    """Save API credentials for a user."""
    user_id = get_jwt_identity()
    data = request.json
    
    # Encrypt sensitive data
    encrypted_readwise_token = encryption_key.encrypt(data['readwise_token'].encode()).decode()
    encrypted_twos_token = encryption_key.encrypt(data['twos_token'].encode()).decode()
    
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
    
    # Schedule daily sync job
    schedule_sync_job(user_id)
    
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
        readwise_token = encryption_key.decrypt(creds.readwise_token.encode()).decode()
        twos_token = encryption_key.decrypt(creds.twos_token.encode()).decode()
        
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
    
    # Update scheduled job
    if user.sync_enabled:
        schedule_sync_job(user_id)
    else:
        # Remove scheduled job
        try:
            scheduler.remove_job(f"sync_user_{user_id}")
            logger.info(f"Removed sync job for user {user_id}")
        except:
            pass
    
    return jsonify({
        "message": "Sync settings updated",
        "settings": {
            "sync_enabled": user.sync_enabled,
            "sync_time": user.sync_time,
            "sync_frequency": user.sync_frequency
        }
    }), 200

# ---- User Routes ----

@app.route('/api/user', methods=['GET'])
@jwt_required()
def get_user():
    """Get user profile."""
    user_id = get_jwt_identity()
    
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
    
    # Remove scheduled job
    try:
        scheduler.remove_job(f"sync_user_{user_id}")
    except:
        pass
    
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
        readwise_token = encryption_key.decrypt(creds.readwise_token.encode()).decode()
        twos_token = encryption_key.decrypt(creds.twos_token.encode()).decode()
        
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