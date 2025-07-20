#!/usr/bin/env python3
"""
Initialize the database with tables and create a default admin user
"""

import os
import sys
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append('backend')

def init_database():
    """Initialize database and create tables"""
    from app import app, db, User
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # Check if any users exist
        user_count = User.query.count()
        print(f"Found {user_count} existing users")
        
        if user_count == 0:
            print("\nNo users found. Creating default admin user...")
            
            # Create default admin user
            admin_email = "admin@example.com"
            admin_password = "admin123"
            
            admin_user = User(
                email=admin_email,
                name="Admin User",
                password_hash=generate_password_hash(admin_password),
                auth_provider='local'
            )
            
            db.session.add(admin_user)
            db.session.commit()
            
            print(f"✅ Default admin user created!")
            print(f"   Email: {admin_email}")
            print(f"   Password: {admin_password}")
            print(f"   User ID: {admin_user.id}")
        
        return True

def list_users():
    """List all users in the database"""
    from app import app, User
    
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found in database.")
            return
        
        print(f"\n=== Found {len(users)} users ===")
        print(f"{'ID':<5} {'Email':<30} {'Name':<20} {'Provider':<10}")
        print("-" * 70)
        
        for user in users:
            print(f"{user.id:<5} {user.email:<30} {user.name or 'N/A':<20} {user.auth_provider:<10}")

def main():
    """Main function"""
    print("🔧 Database Initialization Script")
    print("=" * 50)
    
    try:
        # Initialize database
        if init_database():
            print("\n✅ Database initialization completed successfully!")
            
            # List users
            list_users()
            
            print("\n📝 Next Steps:")
            print("1. Start your Flask app: python backend/app.py")
            print("2. Visit /admin to access the admin console")
            print("3. Use the default admin credentials to log in")
            print("4. Create additional users as needed")
            
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()