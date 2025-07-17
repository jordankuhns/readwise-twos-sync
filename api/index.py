"""
Vercel API routes for Readwise to Twos Sync frontend
"""

import os
import json
import requests
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__, template_folder='../templates')

# Backend API URL
BACKEND_API_URL = os.environ.get('BACKEND_API_URL', 'https://your-backend-api.railway.app')

@app.route('/')
def index():
    """Landing page with login/register forms."""
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    """Dashboard page for authenticated users."""
    return render_template('dashboard.html')

@app.route('/settings')
def settings():
    """Settings page for authenticated users."""
    # This would be implemented in a real app
    return redirect('/dashboard')

@app.route('/api/proxy/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_proxy(endpoint):
    """Proxy API requests to backend."""
    # Get request data
    headers = {
        'Content-Type': request.headers.get('Content-Type', 'application/json')
    }
    
    # Forward Authorization header if present
    auth_header = request.headers.get('Authorization')
    if auth_header:
        headers['Authorization'] = auth_header
    
    # Build URL
    url = f"{BACKEND_API_URL}/{endpoint}"
    
    try:
        # Forward request to backend
        if request.method == 'GET':
            response = requests.get(url, headers=headers, params=request.args)
        elif request.method == 'POST':
            response = requests.post(url, headers=headers, json=request.json)
        elif request.method == 'PUT':
            response = requests.put(url, headers=headers, json=request.json)
        elif request.method == 'DELETE':
            response = requests.delete(url, headers=headers)
        
        # Return response from backend
        return (
            response.content,
            response.status_code,
            {'Content-Type': response.headers.get('Content-Type', 'application/json')}
        )
    
    except requests.RequestException as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})

# This is required for Vercel
if __name__ == '__main__':
    app.run(debug=True)