web: gunicorn wsgi:app
worker: celery -A app.celery worker --loglevel=info