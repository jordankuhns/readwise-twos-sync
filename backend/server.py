"""
Simple server for Heroku deployment
"""

import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from app import app

# Add CORS handling directly to the app
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Add a global OPTIONS handler
@app.route('/api/<path:path>', methods=['OPTIONS'])
def options_handler(path):
    return jsonify({}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)