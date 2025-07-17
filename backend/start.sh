#!/bin/bash
set -e

# Debug information
echo "=== System Information ==="
echo "Current directory: $(pwd)"
echo "Python version: $(python --version 2>&1)"
echo "PATH: $PATH"
echo "User: $(whoami)"

# Install dependencies explicitly
echo "=== Installing Dependencies ==="
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install gunicorn

# Debug environment
echo "=== Running Environment Debug ==="
python debug_env.py

# Find gunicorn
GUNICORN_PATH=$(which gunicorn || echo "gunicorn not found")
echo "Gunicorn path: $GUNICORN_PATH"

if [ "$GUNICORN_PATH" = "gunicorn not found" ]; then
    echo "Gunicorn not found in PATH, trying to find it..."
    GUNICORN_PATH=$(find / -name gunicorn -type f 2>/dev/null | head -n 1)
    echo "Found gunicorn at: $GUNICORN_PATH"
fi

# Start the application
echo "=== Starting Application ==="
if [ "$GUNICORN_PATH" != "gunicorn not found" ] && [ -n "$GUNICORN_PATH" ]; then
    echo "Starting with gunicorn: $GUNICORN_PATH"
    exec "$GUNICORN_PATH" wsgi:app
else
    echo "Falling back to Flask development server"
    exec python server.py
fi