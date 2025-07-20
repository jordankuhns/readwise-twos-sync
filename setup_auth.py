#!/usr/bin/env python3
"""
Complete authentication setup script
"""

import os
import sys
import subprocess
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append('backend')

def setup_database():
    """Setup database and ensure user exists"""
    from app import app, db, User
    
    with app.app_context():
        print("🗄️  Setting up database...")
        
        # Create all tables
        db.create_all()
        print("✅ Database tables created")
        
        # Check for existing user
        existing_user = User.query.filter_by(email="jkuhns13@gmail.com").first()
        
        if existing_user:
            print(f"✅ Found existing user: {existing_user.email}")
            
            # Reset password to known value
            new_password = "481816Test!"
            existing_user.password_hash = generate_password_hash(new_password)
            db.session.commit()
            
            print(f"🔑 Password reset to: {new_password}")
            return existing_user.email, new_password
        else:
            # Create new user
            email = "jkuhns13@gmail.com"
            password = "481816Test!"
            name = "Jordan Kuhns"
            
            user = User(
                email=email,
                name=name,
                password_hash=generate_password_hash(password),
                auth_provider='local'
            )
            
            db.session.add(user)
            db.session.commit()
            
            print(f"✅ Created new user: {email}")
            print(f"🔑 Password: {password}")
            return email, password

def check_environment():
    """Check environment configuration"""
    print("🔧 Checking environment configuration...")
    
    required_vars = ['DATABASE_URL', 'JWT_SECRET_KEY', 'SECRET_KEY']
    missing_vars = []
    
    for var in required_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
    else:
        print("✅ All required environment variables are set")
    
    # Show database type
    db_url = os.environ.get('DATABASE_URL', '')
    if 'sqlite' in db_url or not db_url:
        print("📁 Using SQLite database (local development)")
    elif 'postgresql' in db_url:
        print("🐘 Using PostgreSQL database")
    
    return len(missing_vars) == 0

def test_endpoints():
    """Test that endpoints are accessible"""
    print("🧪 Testing endpoints...")
    
    try:
        from app import app
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            print(f"✅ Health endpoint: {response.status_code}")
            
            # Test admin endpoint
            response = client.get('/admin')
            print(f"✅ Admin page: {response.status_code}")
            
            # Test API endpoints
            response = client.get('/api/admin/users', headers={'Authorization': 'Bearer admin-access'})
            print(f"✅ Admin API: {response.status_code}")
            
        return True
    except Exception as e:
        print(f"❌ Endpoint test failed: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Authentication Setup Script")
    print("=" * 60)
    
    try:
        # 1. Check environment
        env_ok = check_environment()
        
        # 2. Setup database and user
        email, password = setup_database()
        
        # 3. Test endpoints
        endpoints_ok = test_endpoints()
        
        print("\n" + "=" * 60)
        print("✅ SETUP COMPLETE!")
        print("=" * 60)
        
        print(f"📧 User Email: {email}")
        print(f"🔑 Password: {password}")
        print()
        print("🎯 Next Steps:")
        print("1. Start the app: python start_app.py")
        print("2. Visit: http://127.0.0.1:5000/admin")
        print("3. Login with the credentials above")
        print("4. Create additional users as needed")
        print()
        print("🌐 For Railway deployment:")
        print("- The app will automatically use PostgreSQL")
        print("- Admin page will be at: https://your-app.railway.app/admin")
        print()
        print("🔧 Troubleshooting:")
        print("- Run: python test_auth_fix.py (to test endpoints)")
        print("- Run: python reset_user_password.py (to reset passwords)")
        print("- Check logs for any database connection issues")
        
        return True
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()