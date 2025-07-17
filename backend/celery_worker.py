"""
Celery worker for background tasks
"""

import os
from celery import Celery
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure Celery
celery = Celery(
    'readwise_twos_sync',
    broker=os.environ.get('REDIS_URL', 'redis://localhost:6379/0'),
    include=['tasks']
)

# Optional configuration
celery.conf.update(
    result_expires=3600,  # Results expire after 1 hour
    worker_prefetch_multiplier=1,  # Don't prefetch more than one task
    task_acks_late=True,  # Acknowledge tasks after execution
)

if __name__ == '__main__':
    celery.start()