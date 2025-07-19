#!/usr/bin/env python3
"""
Minimal test server to debug Railway deployment
"""

import os
from flask import Flask

# Create a minimal Flask app
test_app = Flask(__name__)

@test_app.route('/')
def home():
    return "Test server is working!"

@test_app.route('/admin')
def admin():
    return "Admin route is working!"

@test_app.route('/test')
def test():
    return "Test route is working!"

@test_app.route('/debug')
def debug():
    return f"""
    <h1>Debug Info</h1>
    <p>PORT: {os.environ.get('PORT', 'Not set')}</p>
    <p>Python working directory: {os.getcwd()}</p>
    <p>Available routes:</p>
    <ul>
        <li><a href="/">/</a></li>
        <li><a href="/admin">/admin</a></li>
        <li><a href="/test">/test</a></li>
        <li><a href="/debug">/debug</a></li>
    </ul>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting test server on port {port}")
    test_app.run(host="0.0.0.0", port=port, debug=True)