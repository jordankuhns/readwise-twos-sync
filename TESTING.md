# Testing Guide

This document explains how to run and maintain tests for the Readwise-Twos sync application.

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Test configuration and fixtures
├── test_auth.py            # Authentication tests
├── test_sync.py            # Sync functionality tests
├── test_scheduler.py       # Scheduler tests
├── test_api_integration.py # External API integration tests
└── test_utils.py           # Utility function tests
```

## Running Tests

### Install Test Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
# Using the test runner script
python run_tests.py

# Or directly with pytest
python -m pytest tests/ -v
```

### Run Specific Tests

```bash
# Run a specific test file
python run_tests.py tests/test_auth.py

# Run a specific test function
python -m pytest tests/test_auth.py::TestAuthentication::test_login_success -v

# Run tests by marker
python -m pytest -m "not slow" -v
```

### Run Tests with Coverage

```bash
python -m pytest tests/ --cov=backend --cov-report=html --cov-report=term-missing
```

This generates an HTML coverage report in `htmlcov/index.html`.

## Test Categories

### Unit Tests
- **Authentication** (`test_auth.py`): User registration, login, JWT handling
- **Utilities** (`test_utils.py`): Encryption, time parsing, data processing
- **Scheduler** (`test_scheduler.py`): Job scheduling, timezone handling

### Integration Tests
- **Sync Operations** (`test_sync.py`): End-to-end sync functionality
- **API Integration** (`test_api_integration.py`): External API interactions

## Test Fixtures

### Available Fixtures
- `app`: Flask test application with temporary database
- `client`: Test client for making HTTP requests
- `auth_headers`: Authentication headers with test user
- `mock_readwise_api`: Mocked Readwise API responses
- `mock_twos_api`: Mocked Twos API responses

### Example Usage

```python
def test_my_feature(client, auth_headers):
    headers, user_id = auth_headers
    response = client.get('/api/user', headers=headers)
    assert response.status_code == 200
```

## Writing New Tests

### Test Naming Convention
- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test

```python
def test_new_feature(app, client, auth_headers):
    """Test description of what this test validates."""
    headers, user_id = auth_headers
    
    with app.app_context():
        # Setup test data
        # ...
        
        # Make request
        response = client.post('/api/new-endpoint', 
            headers=headers,
            json={'data': 'value'}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
```

## Mocking External APIs

### Readwise API
```python
@patch('requests.get')
def test_readwise_integration(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {'results': [...]}
    mock_get.return_value = mock_response
    # ... test code
```

### Twos API
```python
@patch('requests.post')
def test_twos_integration(mock_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_post.return_value = mock_response
    # ... test code
```

## Continuous Integration

Tests run automatically on:
- Push to `main` or `develop` branches
- Pull requests to `main`

The CI pipeline:
1. Sets up Python 3.9, 3.10, and 3.11
2. Installs dependencies
3. Runs linting checks
4. Executes the full test suite
5. Generates coverage reports

## Test Database

Tests use a temporary SQLite database by default. For integration tests requiring PostgreSQL features, the CI environment provides a PostgreSQL service.

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Use fixtures**: Leverage pytest fixtures for common setup
3. **Mock external services**: Don't make real API calls in tests
4. **Test edge cases**: Include error conditions and boundary cases
5. **Keep tests fast**: Use mocks to avoid slow operations
6. **Clear test names**: Test names should describe what they validate

## Debugging Tests

### Run with verbose output
```bash
python -m pytest tests/ -v -s
```

### Run specific failing test
```bash
python -m pytest tests/test_auth.py::test_login_success -v -s --tb=long
```

### Use debugger
```python
def test_something():
    import pdb; pdb.set_trace()
    # ... test code
```

## Coverage Goals

- Aim for >90% code coverage
- Focus on critical paths (auth, sync, scheduler)
- Don't obsess over 100% - quality over quantity