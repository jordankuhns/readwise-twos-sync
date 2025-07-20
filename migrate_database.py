#!/usr/bin/env python3
"""
Database migration script to update schema for Railway deployment
"""

import os
import sys
from dotenv import load_dotenv
from sqlalchemy import text, inspect
from werkzeug.security import generate_password_hash

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append('backend')

def migrate_database():
    """Migrate database schema to match current models"""
    from app import app, db, User
    
    with app.app_context():
        print("🔄 Database Migration Script")
        print("=" * 50)
        
        # Get database inspector
        inspector = inspect(db.engine)
        
        # Check if users table exists
        if not inspector.has_table('users'):
            print("📋 Creating users table from scratch...")
            db.create_all()
            print("✅ All tables created")
            return True
        
        # Get current columns
        columns = [col['name'] for col in inspector.get_columns('users')]
        print(f"📋 Current columns: {columns}")
        
        # Check for missing columns and add them
        migrations_needed = []
        
        if 'password_hash' not in columns:
            migrations_needed.append("ADD COLUMN password_hash VARCHAR(255)")
        
        if 'auth_provider' not in columns:
            migrations_needed.append("ADD COLUMN auth_provider VARCHAR(50) DEFAULT 'local'")
        
        if 'auth_provider_id' not in columns:
            migrations_needed.append("ADD COLUMN auth_provider_id VARCHAR(255)")
        
        if 'sync_enabled' not in columns:
            migrations_needed.append("ADD COLUMN sync_enabled BOOLEAN DEFAULT true")
        
        if 'sync_time' not in columns:
            migrations_needed.append("ADD COLUMN sync_time VARCHAR(5) DEFAULT '09:00'")
        
        if 'sync_frequency' not in columns:
            migrations_needed.append("ADD COLUMN sync_frequency VARCHAR(20) DEFAULT 'daily'")
        
        if 'created_at' not in columns:
            migrations_needed.append("ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        if 'updated_at' not in columns:
            migrations_needed.append("ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        
        # Apply migrations
        if migrations_needed:
            print(f"🔧 Applying {len(migrations_needed)} migrations...")
            
            for migration in migrations_needed:
                try:
                    sql = f"ALTER TABLE users {migration}"
                    print(f"   Executing: {sql}")
                    db.session.execute(text(sql))
                    db.session.commit()
                    print(f"   ✅ Success")
                except Exception as e:
                    print(f"   ⚠️  Warning: {e}")
                    db.session.rollback()
        else:
            print("✅ No migrations needed")
        
        # Update existing users to have password_hash if they don't
        print("\n🔑 Checking user passwords...")
        users = User.query.all()
        
        for user in users:
            if not user.password_hash:
                # Set a default password for existing users
                default_password = "481816Test!"
                user.password_hash = generate_password_hash(default_password)
                print(f"   Setting password for {user.email}: {default_password}")
        
        # Ensure auth_provider is set
        for user in users:
            if not user.auth_provider:
                user.auth_provider = 'local'
                print(f"   Setting auth_provider for {user.email}: local")
        
        db.session.commit()
        
        print(f"\n✅ Migration completed successfully!")
        print(f"📊 Total users: {len(users)}")
        
        return True

def main():
    """Main function"""
    try:
        migrate_database()
        print("\n🎯 Database is ready for deployment!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()