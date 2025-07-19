#!/usr/bin/env python3
"""
Test email sending functionality
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_email_config():
    """Test email configuration and sending"""
    
    # Get email configuration
    smtp_server = os.environ.get('SMTP_SERVER')
    smtp_port = os.environ.get('SMTP_PORT')
    smtp_username = os.environ.get('SMTP_USERNAME')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    from_email = os.environ.get('FROM_EMAIL')
    
    print("=== Email Configuration ===")
    print(f"SMTP_SERVER: {smtp_server}")
    print(f"SMTP_PORT: {smtp_port}")
    print(f"SMTP_USERNAME: {smtp_username}")
    print(f"SMTP_PASSWORD: {'*' * len(smtp_password) if smtp_password else 'Not set'}")
    print(f"FROM_EMAIL: {from_email}")
    print()
    
    # Check if all required settings are present
    missing = []
    if not smtp_server:
        missing.append('SMTP_SERVER')
    if not smtp_port:
        missing.append('SMTP_PORT')
    if not smtp_username:
        missing.append('SMTP_USERNAME')
    if not smtp_password:
        missing.append('SMTP_PASSWORD')
    if not from_email:
        missing.append('FROM_EMAIL')
    
    if missing:
        print(f"❌ Missing environment variables: {', '.join(missing)}")
        return False
    
    # Test email sending
    try:
        print("=== Testing Email Connection ===")
        
        # Get test recipient
        to_email = input("Enter email address to send test email to: ")
        
        # Create test message
        msg = MIMEMultipart()
        msg['Subject'] = "Test Email - Readwise Twos Sync"
        msg['From'] = from_email
        msg['To'] = to_email
        
        body = "This is a test email from your Readwise Twos Sync app. If you received this, email sending is working correctly!"
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        print(f"Connecting to {smtp_server}:{smtp_port}...")
        if int(smtp_port) == 465:
            # Use SSL for port 465
            print("Using SSL connection...")
            with smtplib.SMTP_SSL(smtp_server, int(smtp_port)) as server:
                print("Logging in...")
                server.login(smtp_username, smtp_password)
                print("Sending email...")
                server.send_message(msg)
        else:
            # Use STARTTLS for port 587
            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                print("Starting TLS...")
                server.starttls()
                print("Logging in...")
                server.login(smtp_username, smtp_password)
                print("Sending email...")
                server.send_message(msg)
        
        print("✅ Test email sent successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")
        print(f"Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    test_email_config()