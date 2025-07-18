"""
Combined server for Railway deployment
Runs both the web server and the scheduler in the same process
"""

import os
import logging
import threading
import time
from datetime import datetime
from flask import Flask
from app import app, db, User, start_scheduler, logger

def run_scheduler_thread():
    """Run the scheduler in a separate thread."""
    logger.info("Starting scheduler thread...")
    
    # Wait a bit for the database to be ready
    time.sleep(5)
    
    try:
        with app.app_context():
            start_scheduler()
            
            # Keep the scheduler thread alive
            while True:
                time.sleep(60)  # Check every minute
                
    except Exception as e:
        logger.error(f"Scheduler thread error: {e}")

def main():
    """Main function to start both web server and scheduler."""
    logger.info("Starting combined server (web + scheduler)...")
    
    # Create database tables
    with app.app_context():
        db.create_all()
        logger.info("Database tables created/verified")
    
    # Start scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler_thread, daemon=True)
    scheduler_thread.start()
    logger.info("Scheduler thread started")
    
    # Start the Flask web server
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting web server on port {port}")
    
    app.run(host='0.0.0.0', port=port, debug=False)

if __name__ == "__main__":
    main()