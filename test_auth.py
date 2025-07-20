#!/usr/bin/env python3
"""
Test authentication functionality
"""

import os
import sys
import requests
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append('backend')

def test_login():
    """Test login functionality"""
    from app import app
    
    # Start a test client
    with app.test_client() as client:
        print("🔐 Testing Authentication")
        print("=" * 50)
        
        # Test login
        login_data = {
            "email": "jkuhns13@gmail.com",
            "password": "481816Test!"
        }
        
        print("Testing login...")
        response = client.post('/api/auth/login', 
                             json=login_data,
                             content_type='application/json')
        
        print(f"Login response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.get_json()
            print("✅ Login successful!")
            print(f"   User ID: {data['user']['id']}")
            print(f"   Email: {data['user']['email']}")
            print(f"   Name: {data['user']['name']}")
            
            # Test admin endpoints
            token = data['access_token']
            print(f"\n🔧 Testing Admin Endpoints")
            
            # Test admin users endpoint
            response = client.get('/api/admin/users',
                                headers={'Authorization': 'Bearer admin-access'})
            
            print(f"Admin users endpoint: {response.status_code}")
            if response.status_code == 200:
                users = response.get_json()
                print(f"✅ Found {len(users)} users in admin endpoint")
            else:
                print(f"❌ Admin endpoint failed: {response.get_json()}")
            
            return True
        else:
            print(f"❌ Login failed: {response.get_json()}")
            return False

def main():
    """Main function"""
    try:
        test_login()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()