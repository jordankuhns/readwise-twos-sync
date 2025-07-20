#!/usr/bin/env python3
"""
Start the application with proper database setup
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append('backend')

def setup_and_start():
    """Setup database and start the application"""
    from app import app, db, User
    from werkzeug.security import generate_password_hash
    
    with app.app_context():
        print("🚀 Starting Readwise Twos Sync Application")
        print("=" * 50)
        
        # Create tables if they don't exist
        print("Setting up database...")
        db.create_all()
        print("✅ Database setup complete")
        
        # Show database info
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        if 'sqlite' in database_url:
            print("📁 Using SQLite database (local development)")
        else:
            print("🐘 Using PostgreSQL database (Railway)")
        
        # Ensure admin user exists in production
        is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PORT', '5000') != '5000'
        if is_production:
            admin_email = "jkuhns13@gmail.com"
            existing_user = User.query.filter_by(email=admin_email).first()
            
            if not existing_user:
                print("Creating admin user for production...")
                admin_user = User(
                    email=admin_email,
                    name="Jordan Kuhns",
                    password_hash=generate_password_hash("481816Test!"),
                    auth_provider='local'
                )
                db.session.add(admin_user)
                db.session.commit()
                print(f"✅ Admin user created: {admin_email}")
            else:
                print(f"✅ Admin user exists: {admin_email}")
        
        print(f"🌐 Frontend URL: {os.environ.get('FRONTEND_URL', 'Not set')}")
        print(f"🔑 JWT Secret: {'Set' if os.environ.get('JWT_SECRET_KEY') else 'Not set'}")
        
        # Start the application
        port = int(os.environ.get('PORT', 5000))
        host = '0.0.0.0' if is_production else '127.0.0.1'
        debug_mode = not is_production
        
        print(f"\n🎯 Starting server on {host}:{port}")
        print(f"🔧 Debug mode: {debug_mode}")
        print("📋 Available routes:")
        print("   - / : Main application")
        print("   - /admin : Admin console")
        print("   - /api/auth/login : Login endpoint")
        print("   - /api/auth/register : Registration endpoint")
        print("   - /debug/users : Debug user list")
        print("\n" + "="*50)
        
        app.run(host=host, port=port, debug=debug_mode)

if __name__ == "__main__":
    setup_and_start()