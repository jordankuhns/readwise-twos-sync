"""
Test configuration and fixtures
"""

import pytest
import os
import tempfile
from unittest.mock import Mock, patch
from cryptography.fernet import Fernet
from datetime import datetime

# Set test environment
os.environ['FLASK_ENV'] = 'testing'
os.environ['ENCRYPTION_KEY'] = Fernet.generate_key().decode()

@pytest.fixture
def app():
    """Create and configure a test app."""
    from backend.app import app, db
    
    # Create a temporary database
    db_fd, db_path = tempfile.mkstemp()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()
    
    os.close(db_fd)
    os.unlink(db_path)

@pytest.fixture
def client(app):
    """Create a test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner."""
    return app.test_cli_runner()

@pytest.fixture
def auth_headers(app, client):
    """Create authentication headers for API requests."""
    from backend.app import User, db
    from werkzeug.security import generate_password_hash
    from flask_jwt_extended import create_access_token
    
    with app.app_context():
        # Create a test user
        user = User(
            name="Test User",
            email="test@example.com",
            password_hash=generate_password_hash("testpass123"),
            sync_enabled=True,
            sync_time="09:00",
            sync_frequency="daily"
        )
        db.session.add(user)
        db.session.commit()
        
        # Create JWT token
        token = create_access_token(identity=str(user.id))
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }, user.id

@pytest.fixture
def mock_readwise_api():
    """Mock Readwise API responses."""
    now = datetime.utcnow().isoformat() + "Z"
    mock_highlights = [
        {
            "id": 1,
            "text": "This is a test highlight",
            "book_id": 1,
            "updated": now
        },
        {
            "id": 2,
            "text": "Another test highlight",
            "book_id": 2,
            "updated": now
        }
    ]
    
    mock_books = [
        {
            "id": 1,
            "title": "Test Book 1",
            "author": "Test Author 1"
        },
        {
            "id": 2,
            "title": "Test Book 2",
            "author": "Test Author 2"
        }
    ]
    
    with patch('requests.get') as mock_get:
        def side_effect(url, **kwargs):
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            
            if 'highlights' in url:
                mock_response.json.return_value = {
                    "results": mock_highlights,
                    "next": None
                }
            elif 'books' in url:
                mock_response.json.return_value = {
                    "results": mock_books,
                    "next": None
                }
            
            return mock_response
        
        mock_get.side_effect = side_effect
        yield mock_get

@pytest.fixture
def mock_post_requests():
    """Mock external POST requests to third-party services."""
    with patch('requests.post') as mock_post:
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_post.return_value = mock_response
        yield mock_post

