"""
Test sync functionality
"""

import pytest
import json
from unittest.mock import patch, Mock
from backend.app import ApiCredential, SyncLog, db, cipher_suite


class TestSyncFunctionality:
    """Test sync operations between Readwise and Twos."""
    
    def test_update_credentials(self, app, client, auth_headers):
        """Test updating API credentials."""
        headers, user_id = auth_headers
        
        with app.app_context():
            response = client.post('/api/credentials',
                headers=headers,
                json={
                    'readwise_token': 'test_readwise_token',
                    'twos_user_id': 'test_twos_user',
                    'twos_token': 'test_twos_token'
                }
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['message'] == 'Credentials updated successfully'
            
            # Verify credentials were stored
            creds = ApiCredential.query.filter_by(user_id=user_id).first()
            assert creds is not None
            assert creds.twos_user_id == 'test_twos_user'
    
    def test_get_credentials(self, app, client, auth_headers):
        """Test retrieving API credentials."""
        headers, user_id = auth_headers
        
        with app.app_context():
            # First, store some credentials
            encrypted_readwise = cipher_suite.encrypt('test_readwise_token'.encode())
            encrypted_twos = cipher_suite.encrypt('test_twos_token'.encode())
            
            creds = ApiCredential(
                user_id=user_id,
                readwise_token=encrypted_readwise.decode(),
                twos_user_id='test_twos_user',
                twos_token=encrypted_twos.decode()
            )
            db.session.add(creds)
            db.session.commit()
            
            # Retrieve credentials
            response = client.get('/api/credentials', headers=headers)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['readwise_token'] == 'test_readwise_token'
            assert data['twos_user_id'] == 'test_twos_user'
    
    def test_manual_sync(self, app, client, auth_headers, mock_readwise_api, mock_twos_api):
        """Test manual sync operation."""
        headers, user_id = auth_headers
        
        with app.app_context():
            # Store credentials
            encrypted_readwise = cipher_suite.encrypt('test_readwise_token'.encode())
            encrypted_twos = cipher_suite.encrypt('test_twos_token'.encode())
            
            creds = ApiCredential(
                user_id=user_id,
                readwise_token=encrypted_readwise.decode(),
                twos_user_id='test_twos_user',
                twos_token=encrypted_twos.decode()
            )
            db.session.add(creds)
            db.session.commit()
            
            # Perform sync
            response = client.post('/api/sync',
                headers=headers,
                json={'days_back': 1}
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'highlights_synced' in data
            
            # Verify sync log was created
            sync_log = SyncLog.query.filter_by(user_id=user_id).first()
            assert sync_log is not None
            assert sync_log.status == 'success'
    
    def test_sync_without_credentials(self, client, auth_headers):
        """Test sync without stored credentials."""
        headers, user_id = auth_headers
        
        response = client.post('/api/sync',
            headers=headers,
            json={'days_back': 1}
        )
        assert response.status_code == 404
        data = json.loads(response.data)
        assert 'No API credentials found' in data['error']
    
    def test_update_sync_settings(self, app, client, auth_headers):
        """Test updating sync settings."""
        headers, user_id = auth_headers
        
        with app.app_context():
            response = client.post('/api/sync/settings',
                headers=headers,
                json={
                    'sync_enabled': False,
                    'sync_time': '10:30',
                    'sync_frequency': 'weekly'
                }
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['settings']['sync_enabled'] is False
            assert data['settings']['sync_time'] == '10:30'
            assert data['settings']['sync_frequency'] == 'weekly'
    
    def test_sync_history(self, app, client, auth_headers):
        """Test retrieving sync history."""
        headers, user_id = auth_headers
        
        with app.app_context():
            # Create some sync logs
            log1 = SyncLog(
                user_id=user_id,
                status='success',
                highlights_synced=5,
                details='Test sync 1'
            )
            log2 = SyncLog(
                user_id=user_id,
                status='failed',
                highlights_synced=0,
                details='Test sync 2 failed'
            )
            db.session.add_all([log1, log2])
            db.session.commit()
            
            response = client.get('/api/sync/history', headers=headers)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert len(data) == 2
            assert data[0]['status'] in ['success', 'failed']