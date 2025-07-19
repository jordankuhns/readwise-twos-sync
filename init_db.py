#!/usr/bin/env python3
"""
Initialize the local database
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Override DATABASE_URL for local use
os.environ['DATABASE_URL'] = 'sqlite:///app.db'

# Add backend to path
sys.path.append('backend')

from app import app, db, PasswordResetToken

def init_database():
    """Initialize the database with all tables"""
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        
        # List the tables that were created
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        print(f"Created tables: {', '.join(tables)}")

if __name__ == "__main__":
    init_database()