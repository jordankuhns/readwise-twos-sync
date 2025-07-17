FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install gunicorn explicitly
RUN pip install --no-cache-dir gunicorn==21.2.0

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Create a shell script to run the application
RUN echo '#!/bin/bash\npython -m gunicorn --bind 0.0.0.0:$PORT wsgi:app' > /app/start.sh && \
    chmod +x /app/start.sh

# Run the application
CMD ["/app/start.sh"]