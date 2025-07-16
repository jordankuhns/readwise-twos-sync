"""Flask web application for Readwise to Twos sync."""

import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for
from werkzeug.exceptions import BadRequest

from readwise_twos_sync.config import Config
from readwise_twos_sync.sync_manager import SyncManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'dev-key-change-in-production')

@app.route('/')
def index():
    """Main page with sync form."""
    return render_template('index.html')

@app.route('/sync', methods=['POST'])
def sync():
    """Handle sync request."""
    try:
        # Get form data
        readwise_token = request.form.get('readwise_token', '').strip()
        twos_user_id = request.form.get('twos_user_id', '').strip()
        twos_token = request.form.get('twos_token', '').strip()
        sync_days_back = int(request.form.get('sync_days_back', 7))
        
        # Validate required fields
        if not all([readwise_token, twos_user_id, twos_token]):
            return jsonify({
                'success': False,
                'error': 'All API credentials are required'
            }), 400
        
        # Set environment variables temporarily
        original_env = {}
        env_vars = {
            'READWISE_TOKEN': readwise_token,
            'TWOS_USER_ID': twos_user_id,
            'TWOS_TOKEN': twos_token,
            'SYNC_DAYS_BACK': str(sync_days_back),
            'LAST_SYNC_FILE': f'last_sync_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        }
        
        # Backup and set environment variables
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
        
        try:
            # Create config and sync manager
            config = Config()
            sync_manager = SyncManager(config)
            
            # Perform sync
            sync_manager.sync()
            
            # Clean up temporary sync file
            if config.last_sync_file.exists():
                config.last_sync_file.unlink()
            
            return jsonify({
                'success': True,
                'message': 'Sync completed successfully!'
            })
            
        finally:
            # Restore original environment variables
            for key, original_value in original_env.items():
                if original_value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original_value
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return jsonify({
            'success': False,
            'error': f'Configuration error: {str(e)}'
        }), 400
    
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return jsonify({
            'success': False,
            'error': f'Sync failed: {str(e)}'
        }), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=os.environ.get('FLASK_ENV') == 'development')