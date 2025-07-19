#!/usr/bin/env python3
"""
Admin interface for user management
"""

import os
import sys
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Override DATABASE_URL for local admin use
os.environ['DATABASE_URL'] = 'sqlite:///app.db'

# Add backend to path
sys.path.append('backend')

from app import app, User, db

def list_users():
    """List all users"""
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found.")
            return
        
        print("\n=== All Users ===")
        print(f"{'ID':<5} {'Email':<30} {'Name':<20} {'Provider':<10}")
        print("-" * 70)
        
        for user in users:
            print(f"{user.id:<5} {user.email:<30} {user.name or 'N/A':<20} {user.auth_provider:<10}")

def reset_user_password():
    """Reset a user's password"""
    with app.app_context():
        # List users first
        list_users()
        
        print("\n=== Reset Password ===")
        
        # Get user by email or ID
        identifier = input("Enter user email or ID: ").strip()
        
        # Try to find user by email first, then by ID
        user = User.query.filter_by(email=identifier).first()
        if not user and identifier.isdigit():
            user = User.query.get(int(identifier))
        
        if not user:
            print(f"❌ User not found: {identifier}")
            return
        
        print(f"Found user: {user.email} (ID: {user.id})")
        
        # Get new password
        new_password = input("Enter new password: ").strip()
        
        if len(new_password) < 6:
            print("❌ Password must be at least 6 characters long.")
            return
        
        # Confirm
        confirm = input(f"Reset password for {user.email}? (y/N): ").strip().lower()
        if confirm != 'y':
            print("Password reset cancelled.")
            return
        
        # Update password
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        print(f"✅ Password reset successfully for {user.email}")
        print(f"   New password: {new_password}")
        print(f"   User can now log in with this password.")

def create_admin_user():
    """Create a new admin user"""
    with app.app_context():
        print("\n=== Create New User ===")
        
        email = input("Enter email: ").strip()
        name = input("Enter name (optional): ").strip() or "Admin User"
        password = input("Enter password: ").strip()
        
        if len(password) < 6:
            print("❌ Password must be at least 6 characters long.")
            return
        
        # Check if user exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            print(f"❌ User with email {email} already exists!")
            return
        
        # Create user
        user = User(
            email=email,
            name=name,
            password_hash=generate_password_hash(password),
            auth_provider='local'
        )
        
        db.session.add(user)
        db.session.commit()
        
        print(f"✅ User created successfully!")
        print(f"   Email: {user.email}")
        print(f"   Name: {user.name}")
        print(f"   Password: {password}")
        print(f"   ID: {user.id}")

def delete_user():
    """Delete a user"""
    with app.app_context():
        # List users first
        list_users()
        
        print("\n=== Delete User ===")
        
        # Get user by email or ID
        identifier = input("Enter user email or ID to delete: ").strip()
        
        # Try to find user by email first, then by ID
        user = User.query.filter_by(email=identifier).first()
        if not user and identifier.isdigit():
            user = User.query.get(int(identifier))
        
        if not user:
            print(f"❌ User not found: {identifier}")
            return
        
        print(f"Found user: {user.email} (ID: {user.id})")
        
        # Confirm deletion
        confirm = input(f"DELETE user {user.email}? This cannot be undone! (type 'DELETE' to confirm): ").strip()
        if confirm != 'DELETE':
            print("User deletion cancelled.")
            return
        
        # Delete user (this will cascade delete related records)
        db.session.delete(user)
        db.session.commit()
        
        print(f"✅ User {user.email} deleted successfully.")

def main_menu():
    """Main admin menu"""
    while True:
        print("\n" + "="*50)
        print("         ADMIN INTERFACE")
        print("="*50)
        print("1. List all users")
        print("2. Reset user password")
        print("3. Create new user")
        print("4. Delete user")
        print("5. Exit")
        print("-"*50)
        
        choice = input("Select option (1-5): ").strip()
        
        if choice == '1':
            list_users()
        elif choice == '2':
            reset_user_password()
        elif choice == '3':
            create_admin_user()
        elif choice == '4':
            delete_user()
        elif choice == '5':
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please select 1-5.")

if __name__ == "__main__":
    main_menu()