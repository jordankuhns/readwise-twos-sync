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
                    'twos_token': 'test_twos_token',
                    'capacities_space_id': 'space123',
                    'capacities_token': 'cap_token',
                    'capacities_structure_id': 'struct123',
                    'capacities_text_property_id': 'textprop123'
                }
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['message'] == 'Credentials saved successfully'
            
            # Verify credentials were stored
            creds = ApiCredential.query.filter_by(user_id=user_id).first()
            assert creds is not None
            assert creds.twos_user_id == 'test_twos_user'
            assert creds.capacities_space_id == 'space123'
            assert creds.capacities_structure_id == 'struct123'
            assert creds.capacities_text_property_id == 'textprop123'
    
    def test_get_credentials(self, app, client, auth_headers):
        """Test retrieving API credentials."""
        headers, user_id = auth_headers
        
        with app.app_context():
            # First, store some credentials
            encrypted_readwise = cipher_suite.encrypt('test_readwise_token'.encode())
            encrypted_twos = cipher_suite.encrypt('test_twos_token'.encode())
            encrypted_cap = cipher_suite.encrypt('cap_token'.encode())

            creds = ApiCredential(
                user_id=user_id,
                readwise_token=encrypted_readwise.decode(),
                twos_user_id='test_twos_user',
                twos_token=encrypted_twos.decode(),
                capacities_space_id='space123',
                capacities_token=encrypted_cap.decode(),
                capacities_structure_id='struct123',
                capacities_text_property_id='textprop123'
            )
            db.session.add(creds)
            db.session.commit()
            
            # Retrieve credentials
            response = client.get('/api/credentials', headers=headers)
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['readwise_token'] == 'test_readwise_token'
            assert data['twos_user_id'] == 'test_twos_user'
            assert data['capacities_space_id'] == 'space123'
            assert data['capacities_structure_id'] == 'struct123'
            assert data['capacities_text_property_id'] == 'textprop123'
    
    def test_manual_sync(self, app, client, auth_headers, mock_readwise_api, mock_post_requests):
        """Test manual sync operation."""
        headers, user_id = auth_headers
        
        with app.app_context():
            # Store credentials
            encrypted_readwise = cipher_suite.encrypt('test_readwise_token'.encode())
            encrypted_twos = cipher_suite.encrypt('test_twos_token'.encode())
            encrypted_cap = cipher_suite.encrypt('cap_token'.encode())

            creds = ApiCredential(
                user_id=user_id,
                readwise_token=encrypted_readwise.decode(),
                twos_user_id='test_twos_user',
                twos_token=encrypted_twos.decode(),
                capacities_space_id='space123',
                capacities_token=encrypted_cap.decode(),
                capacities_structure_id='struct123',
                capacities_text_property_id='textprop123'
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

            # Ensure posts were made to both services (2 highlights each)
            twos_calls = [c for c in mock_post_requests.call_args_list if 'twosapp' in c.args[0]]
            cap_calls = [c for c in mock_post_requests.call_args_list if 'capacities' in c.args[0]]
            assert len(twos_calls) == 2
            assert len(cap_calls) == 2
    
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
            assert len(data['history']) == 2
            assert data['history'][0]['status'] in ['success', 'failed']

