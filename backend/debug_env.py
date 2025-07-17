"""
Debug script to print environment information
"""

import sys
import os
import subprocess

def main():
    print("=== Python Environment Debug ===")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Python path: {sys.path}")
    print("\n=== Environment Variables ===")
    for key, value in os.environ.items():
        if key.lower() in ('secret_key', 'jwt_secret_key', 'encryption_key'):
            print(f"{key}: [REDACTED]")
        else:
            print(f"{key}: {value}")
    
    print("\n=== Installed Packages ===")
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', 'list'], 
                               capture_output=True, text=True)
        print(result.stdout)
    except Exception as e:
        print(f"Error listing packages: {e}")
    
    print("\n=== System PATH ===")
    print(os.environ.get('PATH', 'PATH not set'))
    
    print("\n=== Working Directory ===")
    print(os.getcwd())
    print("\n=== Directory Contents ===")
    print(os.listdir('.'))

if __name__ == "__main__":
    main()