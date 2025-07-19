#!/usr/bin/env python3
"""
Create a test user for local development
"""

import os
import sys
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Override DATABASE_URL for local use
os.environ['DATABASE_URL'] = 'sqlite:///app.db'

# Add backend to path
sys.path.append('backend')

from app import app, User, db

def create_user():
    """Create a test user"""
    with app.app_context():
        email = input("Enter email: ")
        password = input("Enter password: ")
        name = input("Enter name (optional): ") or "Test User"
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            return
        
        # Create new user
        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password),
            auth_provider='local'
        )
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ User created successfully!")
        print(f"   - Email: {user.email}")
        print(f"   - Name: {user.name}")
        print(f"   - ID: {user.id}")

if __name__ == "__main__":
    create_user()