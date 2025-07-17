"""
Configuration for the backend API
"""

import os
from datetime import timedelta
from dotenv import load_dotenv
import secrets
from cryptography.fernet import Fernet

# Load environment variables
load_dotenv()

class Config:
    """Base configuration."""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_hex(32))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=30)
    
    # CORS
    FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://readwise-twos-sync.vercel.app')
    
    # Encryption
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY', Fernet.generate_key())
    
    # OAuth
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    
    APPLE_CLIENT_ID = os.environ.get('APPLE_CLIENT_ID', '')
    APPLE_CLIENT_SECRET = os.environ.get('APPLE_CLIENT_SECRET', '')
    
    FACEBOOK_CLIENT_ID = os.environ.get('FACEBOOK_CLIENT_ID', '')
    FACEBOOK_CLIENT_SECRET = os.environ.get('FACEBOOK_CLIENT_SECRET', '')