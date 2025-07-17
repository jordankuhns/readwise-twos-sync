"""
Database models for Readwise to Twos Sync
"""

from datetime import datetime
from app import db

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
    
    # Relationships
    credentials = db.relationship('ApiCredential', backref='user', lazy=True, cascade='all, delete-orphan')
    sync_logs = db.relationship('SyncLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
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