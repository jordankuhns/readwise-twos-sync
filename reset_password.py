#!/usr/bin/env python3
"""
Password reset script for the Readwise-Twos sync app
Run this script to reset a user's password
"""

import os
import sys
from werkzeug.security import generate_password_hash
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def reset_password():
    # Get database URL
    database_url = os.environ.get('postgresql://postgres:mQDVhXdxkhrbiCbiVKOYMnbGIdGvECDc@postgres.railway.internal:5432/railway')
    if not database_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        return
    
    # Handle Railway's postgres:// URL format
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    
    try:
        # Connect to database
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Show existing users
        cursor.execute("SELECT id, email, name FROM users ORDER BY id")
        users = cursor.fetchall()
        
        print("Existing users:")
        for user in users:
            print(f"  ID: {user[0]}, Email: {user[1]}, Name: {user[2]}")
        
        # Get user input
        user_id = input("\nEnter the user ID to reset password for: ")
        new_password = input("Enter the new password: ")
        
        # Generate password hash
        password_hash = generate_password_hash(new_password)
        
        # Update the password
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (password_hash, user_id)
        )
        
        if cursor.rowcount == 0:
            print(f"ERROR: No user found with ID {user_id}")
        else:
            conn.commit()
            print(f"SUCCESS: Password updated for user ID {user_id}")
            print(f"You can now log in with the new password")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    reset_password()