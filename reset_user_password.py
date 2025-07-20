#!/usr/bin/env python3
"""
Reset a user's password - Emergency access script
"""

import os
import sys
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append('backend')

def reset_password():
    """Reset a user's password"""
    from app import app, db, User
    
    with app.app_context():
        # List all users first
        users = User.query.all()
        
        if not users:
            print("❌ No users found in database.")
            return False
        
        print("=== Available Users ===")
        print(f"{'ID':<5} {'Email':<30} {'Name':<20}")
        print("-" * 60)
        
        for user in users:
            print(f"{user.id:<5} {user.email:<30} {user.name or 'N/A':<20}")
        
        print("\n" + "="*50)
        
        # Get user selection
        try:
            user_input = input("Enter user ID or email: ").strip()
            
            # Try to find user by email first, then by ID
            user = User.query.filter_by(email=user_input).first()
            if not user and user_input.isdigit():
                user = User.query.get(int(user_input))
            
            if not user:
                print(f"❌ User not found: {user_input}")
                return False
            
            print(f"\n✅ Found user: {user.email} (ID: {user.id})")
            
            # Get new password
            new_password = input("Enter new password (min 6 chars): ").strip()
            
            if len(new_password) < 6:
                print("❌ Password must be at least 6 characters long.")
                return False
            
            # Confirm
            confirm = input(f"Reset password for {user.email}? (y/N): ").strip().lower()
            if confirm != 'y':
                print("Password reset cancelled.")
                return False
            
            # Update password
            user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            print(f"\n✅ Password reset successfully!")
            print(f"   User: {user.email}")
            print(f"   New password: {new_password}")
            print(f"   You can now log in with these credentials.")
            
            return True
            
        except KeyboardInterrupt:
            print("\n\nPassword reset cancelled.")
            return False
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

def main():
    """Main function"""
    print("🔑 Password Reset Script")
    print("=" * 50)
    
    try:
        reset_password()
    except Exception as e:
        print(f"❌ Script failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()