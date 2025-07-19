"""
Test scheduler functionality
"""

import pytest
import pytz
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from backend.app import User, ApiCredential, db, cipher_suite, schedule_sync_job


class TestScheduler:
    """Test scheduled sync functionality."""
    
    def test_schedule_sync_job_daily(self, app):
        """Test scheduling a daily sync job."""
        with app.app_context():
            # Create test user
            user = User(
                name="Test User",
                email="test@example.com",
                password_hash="test_hash",
                sync_enabled=True,
                sync_time="09:00",
                sync_frequency="daily"
            )
            db.session.add(user)
            db.session.commit()
            
            # Mock scheduler
            with patch('backend.app.scheduler') as mock_scheduler:
                mock_scheduler.running = True
                mock_scheduler.get_jobs.return_value = []
                
                # Schedule the job
                schedule_sync_job(user.id)
                
                # Verify add_job was called with correct parameters
                mock_scheduler.add_job.assert_called_once()
                call_args = mock_scheduler.add_job.call_args
                
                assert call_args[1]['hour'] == 9
                assert call_args[1]['minute'] == 0
                assert 'timezone' in call_args[1]
                assert call_args[1]['id'] == f'sync_user_{user.id}'
    
    def test_schedule_sync_job_weekly(self, app):
        """Test scheduling a weekly sync job."""
        with app.app_context():
            # Create test user with weekly sync
            user = User(
                name="Test User",
                email="test@example.com",
                password_hash="test_hash",
                sync_enabled=True,
                sync_time="14:30",
                sync_frequency="weekly"
            )
            db.session.add(user)
            db.session.commit()
            
            # Mock scheduler
            with patch('backend.app.scheduler') as mock_scheduler:
                mock_scheduler.running = True
                mock_scheduler.get_jobs.return_value = []
                
                # Schedule the job
                schedule_sync_job(user.id)
                
                # Verify add_job was called with correct parameters
                mock_scheduler.add_job.assert_called_once()
                call_args = mock_scheduler.add_job.call_args
                
                assert call_args[1]['hour'] == 14
                assert call_args[1]['minute'] == 30
                assert call_args[1]['day_of_week'] == 'mon'
                assert 'timezone' in call_args[1]
    
    def test_schedule_sync_job_disabled_user(self, app):
        """Test that disabled users don't get scheduled."""
        with app.app_context():
            # Create disabled user
            user = User(
                name="Test User",
                email="test@example.com",
                password_hash="test_hash",
                sync_enabled=False,
                sync_time="09:00",
                sync_frequency="daily"
            )
            db.session.add(user)
            db.session.commit()
            
            # Mock scheduler
            with patch('backend.app.scheduler') as mock_scheduler:
                mock_scheduler.running = True
                
                # Try to schedule the job
                schedule_sync_job(user.id)
                
                # Verify add_job was NOT called
                mock_scheduler.add_job.assert_not_called()
    
    def test_timezone_handling(self, app):
        """Test that timezone is properly handled in scheduling."""
        with app.app_context():
            user = User(
                name="Test User",
                email="test@example.com",
                password_hash="test_hash",
                sync_enabled=True,
                sync_time="15:45",
                sync_frequency="daily"
            )
            db.session.add(user)
            db.session.commit()
            
            with patch('backend.app.scheduler') as mock_scheduler:
                mock_scheduler.running = True
                mock_scheduler.get_jobs.return_value = []
                
                schedule_sync_job(user.id)
                
                call_args = mock_scheduler.add_job.call_args
                timezone = call_args[1]['timezone']
                
                # Should be America/Chicago timezone
                assert isinstance(timezone, pytz.BaseTzInfo)
                assert 'America/Chicago' in str(timezone)
    
    @patch('backend.app.perform_sync')
    def test_run_scheduled_sync(self, mock_perform_sync, app):
        """Test the scheduled sync execution."""
        with app.app_context():
            # Create user and credentials
            user = User(
                name="Test User",
                email="test@example.com",
                password_hash="test_hash",
                sync_enabled=True,
                sync_time="09:00",
                sync_frequency="daily"
            )
            db.session.add(user)
            db.session.commit()
            
            # Add credentials
            encrypted_readwise = cipher_suite.encrypt('test_readwise_token'.encode())
            encrypted_twos = cipher_suite.encrypt('test_twos_token'.encode())
            
            creds = ApiCredential(
                user_id=user.id,
                readwise_token=encrypted_readwise.decode(),
                twos_user_id='test_twos_user',
                twos_token=encrypted_twos.decode()
            )
            db.session.add(creds)
            db.session.commit()
            
            # Mock successful sync
            mock_perform_sync.return_value = {
                'success': True,
                'highlights_synced': 3,
                'message': 'Test sync completed'
            }
            
            # Import and run the scheduled sync function
            from backend.app import run_scheduled_sync
            
            # Execute scheduled sync
            run_scheduled_sync(user.id)
            
            # Verify perform_sync was called with correct parameters
            mock_perform_sync.assert_called_once()
            call_args = mock_perform_sync.call_args[1]  # keyword arguments
            
            assert call_args['twos_user_id'] == 'test_twos_user'
            assert call_args['days_back'] == 1
            assert call_args['user_id'] == user.id