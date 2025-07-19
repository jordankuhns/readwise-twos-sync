"""
Test authentication functionality
"""

import pytest
import json
from werkzeug.security import generate_password_hash
from backend.app import User, db


class TestAuthentication:
    """Test user authentication and JWT handling."""
    
    def test_health_endpoint(self, client):
        """Test basic health endpoint."""
        response = client.get('/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    def test_register_user(self, app, client):
        """Test user registration."""
        with app.app_context():
            response = client.post('/api/register', 
                json={
                    'name': 'New User',
                    'email': 'newuser@example.com',
                    'password': 'password123'
                }
            )
            assert response.status_code == 201
            data = json.loads(response.data)
            assert 'access_token' in data
            assert data['user']['email'] == 'newuser@example.com'
    
    def test_register_duplicate_email(self, app, client):
        """Test registration with duplicate email."""
        with app.app_context():
            # Create first user
            user = User(
                name="Existing User",
                email="existing@example.com",
                password_hash=generate_password_hash("password123")
            )
            db.session.add(user)
            db.session.commit()
            
            # Try to register with same email
            response = client.post('/api/register',
                json={
                    'name': 'Another User',
                    'email': 'existing@example.com',
                    'password': 'password123'
                }
            )
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'already exists' in data['error']
    
    def test_login_success(self, app, client):
        """Test successful login."""
        with app.app_context():
            # Create test user
            user = User(
                name="Test User",
                email="test@example.com",
                password_hash=generate_password_hash("password123")
            )
            db.session.add(user)
            db.session.commit()
            
            # Login
            response = client.post('/api/login',
                json={
                    'email': 'test@example.com',
                    'password': 'password123'
                }
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert 'access_token' in data
            assert data['user']['email'] == 'test@example.com'
    
    def test_login_invalid_credentials(self, app, client):
        """Test login with invalid credentials."""
        with app.app_context():
            response = client.post('/api/login',
                json={
                    'email': 'nonexistent@example.com',
                    'password': 'wrongpassword'
                }
            )
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'Invalid credentials' in data['error']
    
    def test_protected_endpoint_without_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get('/api/user')
        assert response.status_code == 401
    
    def test_protected_endpoint_with_token(self, client, auth_headers):
        """Test accessing protected endpoint with valid token."""
        headers, user_id = auth_headers
        response = client.get('/api/user', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['email'] == 'test@example.com'