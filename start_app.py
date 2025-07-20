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
    from sqlalchemy import text, inspect
    
    with app.app_context():
        print("🚀 Starting Readwise Twos Sync Application")
        print("=" * 50)
        
        # Create tables if they don't exist
        print("Setting up database...")
        
        # Check if we need to migrate existing schema
        try:
            inspector = inspect(db.engine)
            if inspector.has_table('users'):
                columns = [col['name'] for col in inspector.get_columns('users')]
                if 'password_hash' not in columns:
                    print("🔄 Migrating existing database schema...")
                    # Add missing columns
                    try:
                        db.session.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                        db.session.execute(text("ALTER TABLE users ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'"))
                        db.session.execute(text("ALTER TABLE users ADD COLUMN auth_provider_id VARCHAR(255)"))
                        db.session.execute(text("ALTER TABLE users ADD COLUMN sync_enabled BOOLEAN DEFAULT true"))
                        db.session.execute(text("ALTER TABLE users ADD COLUMN sync_time VARCHAR(5) DEFAULT '09:00'"))
                        db.session.execute(text("ALTER TABLE users ADD COLUMN sync_frequency VARCHAR(20) DEFAULT 'daily'"))
                        db.session.execute(text("ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                        db.session.execute(text("ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"))
                        db.session.commit()
                        print("✅ Database migration complete")
                    except Exception as e:
                        print(f"⚠️  Migration warning: {e}")
                        db.session.rollback()
        except Exception as e:
            print(f"⚠️  Schema check warning: {e}")
        
        # Create all tables (safe to run multiple times)
        db.create_all()
        print("✅ Database setup complete")
        
        # Show database info
        database_url = app.config['SQLALCHEMY_DATABASE_URI']
        if 'sqlite' in database_url:
            print("📁 Using SQLite database (local development)")
        else:
            print("🐘 Using PostgreSQL database (Railway)")
        
        # Ensure admin user exists and has proper password
        is_production = os.environ.get('RAILWAY_ENVIRONMENT') or os.environ.get('PORT', '5000') != '5000'
        admin_email = "jkuhns13@gmail.com"
        admin_password = "481816Test!"
        
        try:
            existing_user = User.query.filter_by(email=admin_email).first()
            
            if not existing_user:
                print("Creating admin user...")
                admin_user = User(
                    email=admin_email,
                    name="Jordan Kuhns",
                    password_hash=generate_password_hash(admin_password),
                    auth_provider='local'
                )
                db.session.add(admin_user)
                db.session.commit()
                print(f"✅ Admin user created: {admin_email}")
            else:
                # Ensure existing user has password_hash set
                if not existing_user.password_hash:
                    print("Setting password for existing admin user...")
                    existing_user.password_hash = generate_password_hash(admin_password)
                    existing_user.auth_provider = existing_user.auth_provider or 'local'
                    db.session.commit()
                    print(f"✅ Password set for existing user: {admin_email}")
                else:
                    print(f"✅ Admin user exists: {admin_email}")
        except Exception as e:
            print(f"⚠️  User setup warning: {e}")
            # Continue anyway
        
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