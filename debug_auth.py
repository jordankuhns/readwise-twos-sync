#!/usr/bin/env python3
"""
Debug script to check authentication issues
"""

import os
import sys
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append('backend')

from app import app, User, db

def debug_user_auth():
    """Debug user authentication"""
    with app.app_context():
        email = input("Enter your email: ")
        password = input("Enter your password: ")
        
        # Find user
        user = User.query.filter_by(email=email).first()
        
        if not user:
            print(f"❌ No user found with email: {email}")
            return
            
        print(f"✅ User found: {user.email}")
        print(f"   - ID: {user.id}")
        print(f"   - Name: {user.name}")
        print(f"   - Auth Provider: {user.auth_provider}")
        
        # Check password field
        if hasattr(user, 'password_hash'):
            if user.password_hash:
                print(f"   - Has password_hash: Yes (length: {len(user.password_hash)})")
                # Test password
                if check_password_hash(user.password_hash, password):
                    print("✅ Password verification: SUCCESS")
                else:
                    print("❌ Password verification: FAILED")
            else:
                print("   - Has password_hash: No (field is empty/null)")
        else:
            print("   - password_hash field: NOT FOUND")
            
        # Check old password field (just in case)
        if hasattr(user, 'password'):
            if user.password:
                print(f"   - Has old password field: Yes (length: {len(user.password)})")
            else:
                print("   - Has old password field: No (field is empty/null)")
        else:
            print("   - old password field: NOT FOUND")

if __name__ == "__main__":
    debug_user_auth()