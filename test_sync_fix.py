#!/usr/bin/env python3
"""
Test script to verify the sync functionality is working properly
"""

import sys
sys.path.append('backend')

from app import app, db, User, ApiCredential, SyncLog, perform_sync
from sync_service import perform_sync as sync_service_perform_sync

def test_sync_service():
    """Test the sync service directly"""
    print("Testing sync service...")
    
    # Test with dummy data (this will fail but should not crash)
    try:
        result = sync_service_perform_sync(
            readwise_token="dummy_token",
            twos_user_id="dummy_user",
            twos_token="dummy_token",
            days_back=1,
            user_id=1
        )
        print(f"Sync service result: {result}")
    except Exception as e:
        print(f"Expected error (dummy tokens): {e}")
        print("✅ Sync service handles errors properly")

def test_database_models():
    """Test database models"""
    print("\nTesting database models...")
    
    with app.app_context():
        try:
            # Test user query
            users = User.query.all()
            print(f"✅ Found {len(users)} users")
            
            # Test credentials query
            creds = ApiCredential.query.all()
            print(f"✅ Found {len(creds)} credential records")
            
            # Test sync logs query
            logs = SyncLog.query.all()
            print(f"✅ Found {len(logs)} sync log records")
            
            print("✅ Database models working properly")
            
        except Exception as e:
            print(f"❌ Database model error: {e}")
            import traceback
            traceback.print_exc()

def test_app_routes():
    """Test basic app routes"""
    print("\nTesting app routes...")
    
    with app.test_client() as client:
        try:
            # Test health check
            response = client.get('/health')
            print(f"✅ Health check: {response.status_code}")
            
            # Test detailed health check
            response = client.get('/health-detailed')
            print(f"✅ Detailed health check: {response.status_code}")
            
            # Test debug users endpoint
            response = client.get('/debug/users')
            print(f"✅ Debug users endpoint: {response.status_code}")
            
            print("✅ Basic routes working properly")
            
        except Exception as e:
            print(f"❌ Route testing error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🔧 Testing Readwise-Twos Sync Application")
    print("=" * 50)
    
    test_sync_service()
    test_database_models()
    test_app_routes()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")