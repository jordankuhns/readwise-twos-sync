#!/usr/bin/env python3
"""
Debug Railway deployment issues
"""

import requests
import json

def test_railway_endpoints():
    """Test Railway endpoints"""
    # Replace with your actual Railway URL
    base_url = "https://web-production-0b0f42.up.railway.app"
    
    print("🚂 Testing Railway Deployment")
    print("=" * 50)
    print(f"Base URL: {base_url}")
    print()
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        print(f"✅ Health check: {response.status_code}")
        if response.status_code == 200:
            print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False
    
    # Test 2: Debug users endpoint (no auth required)
    try:
        response = requests.get(f"{base_url}/debug/users", timeout=10)
        print(f"✅ Debug users: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Found {len(data.get('users', []))} users")
            for user in data.get('users', []):
                print(f"   - {user.get('email')} (ID: {user.get('id')})")
        else:
            print(f"   Error: {response.text}")
    except Exception as e:
        print(f"❌ Debug users failed: {e}")
    
    # Test 3: Admin page
    try:
        response = requests.get(f"{base_url}/admin", timeout=10)
        print(f"✅ Admin page: {response.status_code}")
        if response.status_code != 200:
            print(f"   Error: {response.text[:200]}...")
    except Exception as e:
        print(f"❌ Admin page failed: {e}")
    
    # Test 4: Login attempt
    try:
        login_data = {
            "email": "jkuhns13@gmail.com",
            "password": "481816Test!"
        }
        response = requests.post(
            f"{base_url}/api/auth/login",
            json=login_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        print(f"✅ Login attempt: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Login successful: {data.get('user', {}).get('email')}")
            token = data.get('access_token')
            
            # Test admin API with token
            if token:
                admin_response = requests.get(
                    f"{base_url}/api/admin/users",
                    headers={"Authorization": f"Bearer admin-access"},
                    timeout=10
                )
                print(f"✅ Admin API: {admin_response.status_code}")
                if admin_response.status_code == 200:
                    users = admin_response.json()
                    print(f"   Admin API found {len(users)} users")
                else:
                    print(f"   Admin API error: {admin_response.text}")
        else:
            print(f"   Login failed: {response.json()}")
    except Exception as e:
        print(f"❌ Login test failed: {e}")
    
    # Test 5: CORS preflight
    try:
        response = requests.options(
            f"{base_url}/api/admin/users",
            headers={
                "Origin": base_url,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization"
            },
            timeout=10
        )
        print(f"✅ CORS preflight: {response.status_code}")
    except Exception as e:
        print(f"❌ CORS test failed: {e}")

def main():
    """Main function"""
    print("This script tests your Railway deployment endpoints.")
    print("Make sure to update the base_url with your actual Railway URL.")
    print()
    
    test_railway_endpoints()
    
    print("\n" + "=" * 50)
    print("🔧 Troubleshooting Tips:")
    print("1. Check Railway logs for startup errors")
    print("2. Verify environment variables are set in Railway")
    print("3. Ensure database migration completed successfully")
    print("4. Check if CORS headers are properly configured")

if __name__ == "__main__":
    main()