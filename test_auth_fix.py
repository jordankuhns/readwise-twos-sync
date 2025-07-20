#!/usr/bin/env python3
"""
Test authentication endpoints to ensure they're working
"""

import requests
import json
import sys

def test_auth_endpoints():
    """Test authentication endpoints"""
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 Testing Authentication Endpoints")
    print("=" * 50)
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Health check: {response.status_code}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Registration
    test_user = {
        "email": "test@example.com",
        "name": "Test User",
        "password": "testpass123"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/register",
            json=test_user,
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ Registration test: {response.status_code}")
        if response.status_code == 201:
            data = response.json()
            print(f"   User created: {data.get('user', {}).get('email')}")
        elif response.status_code == 400:
            print(f"   Expected error (user exists): {response.json().get('error')}")
    except Exception as e:
        print(f"❌ Registration test failed: {e}")
    
    # Test 3: Login with existing user
    login_data = {
        "email": "jkuhns13@gmail.com",
        "password": "481816Test!"
    }
    
    try:
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"}
        )
        print(f"✅ Login test: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Login successful: {data.get('user', {}).get('email')}")
            token = data.get('access_token')
            if token:
                print(f"   Token received: {token[:20]}...")
                return token
        else:
            print(f"   Login failed: {response.json()}")
    except Exception as e:
        print(f"❌ Login test failed: {e}")
    
    # Test 4: Admin endpoints
    try:
        response = requests.get(
            f"{base_url}/api/admin/users",
            headers={"Authorization": "Bearer admin-access"}
        )
        print(f"✅ Admin users endpoint: {response.status_code}")
        if response.status_code == 200:
            users = response.json()
            print(f"   Found {len(users)} users")
    except Exception as e:
        print(f"❌ Admin test failed: {e}")
    
    return True

def main():
    """Main function"""
    print("Starting authentication tests...")
    print("Make sure your Flask app is running on http://127.0.0.1:5000")
    print()
    
    input("Press Enter when your app is running...")
    
    test_auth_endpoints()

if __name__ == "__main__":
    main()