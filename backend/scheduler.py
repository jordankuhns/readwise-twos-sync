"""
Scheduler for running periodic sync jobs
"""

import os
import logging
import time
from datetime import datetime, timedelta
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from dotenv import load_dotenv
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
import pytz
from db_utils import ensure_capacities_columns
from readwise_twos_sync.capacities_client import CapacitiesClient

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///app.db')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

# Create database engine and session
engine = sa.create_engine(DATABASE_URL)
ensure_capacities_columns(engine)
Session = sessionmaker(bind=engine)

# Encryption for API tokens
encryption_key = os.environ.get('ENCRYPTION_KEY')
if encryption_key:
    cipher_suite = Fernet(encryption_key.encode())
else:
    cipher_suite = Fernet(Fernet.generate_key())
    logger.warning("No ENCRYPTION_KEY provided, using generated key")

# Define ORM models
metadata = sa.MetaData()

users = sa.Table(
    'users',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('email', sa.String(255)),
    sa.Column('sync_enabled', sa.Boolean, default=True),
    sa.Column('sync_time', sa.String(5), default='09:00'),
    sa.Column('sync_frequency', sa.String(20), default='daily'),
)

api_credentials = sa.Table(
    'api_credentials',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('user_id', sa.Integer),
    sa.Column('readwise_token', sa.Text),
    sa.Column('twos_user_id', sa.String(255)),
    sa.Column('twos_token', sa.Text),
    sa.Column('capacities_space_id', sa.String(255)),
    sa.Column('capacities_token', sa.Text),
)

sync_logs = sa.Table(
    'sync_logs',
    metadata,
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('user_id', sa.Integer),
    sa.Column('status', sa.String(50)),
    sa.Column('highlights_synced', sa.Integer, default=0),
    sa.Column('details', sa.Text),
    sa.Column('created_at', sa.DateTime, default=datetime.utcnow),
)

def fetch_highlights_since(readwise_token, since):
    """Fetch highlights updated since a given timestamp."""
    headers = {"Authorization": f"Token {readwise_token}"}
    highlights = []
    next_url = "https://readwise.io/api/v2/highlights/"
    params = {"page_size": 1000}
    
    while next_url:
        try:
            response = requests.get(next_url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for highlight in data.get("results", []):
                if highlight.get("updated") and highlight["updated"] > since:
                    highlights.append(highlight)
            
            next_url = data.get("next")
            params = {}
            
        except requests.RequestException as e:
            logger.error(f"Error fetching highlights: {e}")
            raise
    
    return highlights

def fetch_all_books(readwise_token):
    """Fetch all books from Readwise."""
    headers = {"Authorization": f"Token {readwise_token}"}
    books = {}
    next_url = "https://readwise.io/api/v2/books/"
    
    while next_url:
        try:
            response = requests.get(next_url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for book in data.get("results", []):
                book_id = book.get("id")
                title = book.get("title", "Untitled")
                author = book.get("author", "Unknown")
                
                if title.strip().lower() == "how to use readwise":
                    continue
                
                books[book_id] = {"title": title, "author": author}
            
            next_url = data.get("next")
            
        except requests.RequestException as e:
            logger.error(f"Error fetching books: {e}")
            raise
    
    return books

def post_highlights_to_twos(highlights, books, twos_user_id, twos_token):
    """Post highlights to Twos."""
    api_url = "https://www.twosapp.com/apiV2/user/addToToday"
    headers = {"Content-Type": "application/json"}
    today_title = datetime.now().strftime("%a %b %d, %Y")
    
    # Debug logging
    logger.info(f"Posting to Twos with user_id: {twos_user_id}")
    logger.info(f"Token length: {len(twos_token)}")
    
    if not highlights:
        payload = {
            "text": "No new highlights found.",
            "user_id": twos_user_id,
            "token": twos_token
        }
        
        # Debug logging
        logger.info(f"Sending payload to Twos: {payload}")
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            logger.info(f"Twos API response status: {response.status_code}")
            logger.info(f"Twos API response: {response.text}")
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to post no-highlights message: {e}")
        return
    
    successful_posts = 0
    for highlight in highlights:
        try:
            book_id = highlight.get("book_id")
            text = highlight.get("text")
            book_meta = books.get(book_id)
            
            if not book_meta:
                continue
            
            title = book_meta["title"]
            author = book_meta["author"]
            note_text = f"{title}, {author}: {text}"
            
            payload = {
                "text": note_text.strip(),
                "user_id": twos_user_id,
                "token": twos_token
            }
            
            # Debug logging
            logger.info(f"Sending highlight to Twos: {note_text[:50]}...")
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            logger.info(f"Twos API response status: {response.status_code}")
            if response.status_code != 200:
                logger.info(f"Twos API error response: {response.text}")
            response.raise_for_status()
            successful_posts += 1
            
        except requests.RequestException as e:
            logger.error(f"Failed to post highlight: {e}")

    return successful_posts


def perform_sync(readwise_token, twos_user_id, twos_token, capacities_token=None, capacities_space_id=None, days_back=1, user_id=None):
    """Perform a sync from Readwise to Twos and Capacities."""
    logger.info(f"Starting sync for user {user_id}, looking back {days_back} days")
    
    try:
        # Calculate since timestamp
        since_time = datetime.utcnow() - timedelta(days=days_back)
        since = since_time.isoformat()
        
        # Fetch highlights
        highlights = fetch_highlights_since(readwise_token, since)

        capacities_client = None
        if capacities_token and capacities_space_id:
            capacities_client = CapacitiesClient(
                token=capacities_token, space_id=capacities_space_id
            )

        if highlights:
            books = fetch_all_books(readwise_token)
            post_highlights_to_twos(highlights, books, twos_user_id, twos_token)
            if capacities_client:
                capacities_client.post_highlights(highlights, books)
            message = f"Successfully synced {len(highlights)} highlights to destinations!"
        else:
            post_highlights_to_twos([], {}, twos_user_id, twos_token)
            if capacities_client:
                capacities_client.post_highlights([], {})
            message = "No new highlights found, but posted update to destinations."
        
        # Log successful sync
        if user_id:
            session = Session()
            log = {
                'user_id': user_id,
                'status': 'success',
                'highlights_synced': len(highlights),
                'details': message,
                'created_at': datetime.utcnow()
            }
            session.execute(sync_logs.insert().values(**log))
            session.commit()
            session.close()
        
        return {
            "success": True,
            "message": message,
            "highlights_synced": len(highlights)
        }
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        
        # Log failed sync
        if user_id:
            session = Session()
            log = {
                'user_id': user_id,
                'status': 'failed',
                'highlights_synced': 0,
                'details': str(e),
                'created_at': datetime.utcnow()
            }
            session.execute(sync_logs.insert().values(**log))
            session.commit()
            session.close()
        
        raise

def run_scheduled_sync(user_id):
    """Run a scheduled sync for a user."""
    logger.info(f"Running scheduled sync for user {user_id}")
    
    # Get user credentials
    session = Session()
    creds_result = session.execute(
        sa.select([api_credentials]).where(api_credentials.c.user_id == user_id)
    ).fetchone()
    
    if not creds_result:
        logger.error(f"No credentials found for user {user_id}")
        session.close()
        return
    
    try:
        # Decrypt tokens
        readwise_token = cipher_suite.decrypt(creds_result.readwise_token.encode()).decode()
        twos_token = cipher_suite.decrypt(creds_result.twos_token.encode()).decode()
        capacities_token = (
            cipher_suite.decrypt(creds_result.capacities_token.encode()).decode()
            if creds_result.capacities_token else None
        )

        # Perform sync (only 1 day back for scheduled syncs)
        result = perform_sync(
            readwise_token=readwise_token,
            twos_user_id=creds_result.twos_user_id,
            twos_token=twos_token,
            capacities_token=capacities_token,
            capacities_space_id=creds_result.capacities_space_id,
            days_back=1,  # Only sync yesterday's highlights
            user_id=user_id
        )
        
        logger.info(f"Scheduled sync completed for user {user_id}: {result}")
        
    except Exception as e:
        logger.error(f"Scheduled sync failed for user {user_id}: {e}")
        
        # Log the error
        log = {
            'user_id': user_id,
            'status': 'failed',
            'highlights_synced': 0,
            'details': str(e),
            'created_at': datetime.utcnow()
        }
        session.execute(sync_logs.insert().values(**log))
        session.commit()
    
    finally:
        session.close()

def schedule_sync_job(user_id, scheduler):
    """Schedule a daily sync job for a user."""
    session = Session()
    user_result = session.execute(
        sa.select([users]).where(users.c.id == user_id)
    ).fetchone()
    
    if not user_result or not user_result.sync_enabled:
        session.close()
        return
    
    # Parse sync time (format: "HH:MM")
    hour, minute = map(int, user_result.sync_time.split(':'))
    
    # Get the system's local timezone - detect automatically
    try:
        # Try to get system timezone
        import time
        local_tz_name = time.tzname[time.daylight]
        if local_tz_name in ['CDT', 'CST']:
            local_tz = pytz.timezone('America/Chicago')
        else:
            # Fallback to system timezone
            local_tz = pytz.timezone('America/Chicago')  # Default for this deployment
    except:
        # Fallback to Chicago timezone
        local_tz = pytz.timezone('America/Chicago')
    
    # Remove existing job if it exists
    try:
        scheduler.remove_job(f"sync_user_{user_id}")
    except:
        pass
    
    # Schedule new job with timezone
    if user_result.sync_frequency == 'daily':
        scheduler.add_job(
            run_scheduled_sync,
            'cron',
            hour=hour,
            minute=minute,
            timezone=local_tz,
            id=f"sync_user_{user_id}",
            args=[user_id]
        )
        logger.info(f"Scheduled daily sync for user {user_id} at {hour}:{minute} {local_tz}")
    elif user_result.sync_frequency == 'weekly':
        scheduler.add_job(
            run_scheduled_sync,
            'cron',
            day_of_week='mon',
            hour=hour,
            minute=minute,
            timezone=local_tz,
            id=f"sync_user_{user_id}",
            args=[user_id]
        )
        logger.info(f"Scheduled weekly sync for user {user_id} at {hour}:{minute} on Mondays {local_tz}")
    
    session.close()

def main():
    """Main function to run the scheduler."""
    logger.info("Starting scheduler...")
    
    # Log environment variables (without sensitive info)
    logger.info(f"DATABASE_URL: {DATABASE_URL.split('@')[0]}...")
    logger.info(f"ENCRYPTION_KEY set: {bool(encryption_key)}")
    
    # Initialize scheduler
    jobstores = {
        'default': SQLAlchemyJobStore(url=DATABASE_URL)
    }
    scheduler = BackgroundScheduler(jobstores=jobstores)
    scheduler.start()
    
    # Schedule sync jobs for all users
    session = Session()
    try:
        users_result = session.execute(
            sa.select([users]).where(users.c.sync_enabled == True)
        ).fetchall()
        
        logger.info(f"Found {len(users_result)} users with sync_enabled=True")
        
        for user in users_result:
            logger.info(f"Scheduling sync job for user {user.id} at {user.sync_time}")
            schedule_sync_job(user.id, scheduler)
        
        # Log all scheduled jobs
        jobs = scheduler.get_jobs()
        logger.info(f"Total scheduled jobs: {len(jobs)}")
        for job in jobs:
            logger.info(f"Job ID: {job.id}, Next run time: {job.next_run_time}")
        
    except Exception as e:
        logger.error(f"Error scheduling sync jobs: {e}")
    finally:
        session.close()
    
    # Keep the scheduler running
    try:
        logger.info("Scheduler is running. Press Ctrl+C to exit.")
        while True:
            time.sleep(60)
            # Log a heartbeat every minute
            logger.info("Scheduler heartbeat")
            
            # Check for any jobs that should run in the next minute
            jobs = scheduler.get_jobs()
            now = datetime.now(pytz.UTC)  # Use timezone-aware datetime
            for job in jobs:
                if job.next_run_time:
                    # Make sure both datetimes are timezone-aware for comparison
                    next_run = job.next_run_time
                    if next_run.tzinfo is None:
                        next_run = pytz.UTC.localize(next_run)
                    
                    time_diff = (next_run - now).total_seconds()
                    if time_diff < 60:
                        logger.info(f"Job {job.id} will run soon at {job.next_run_time} (in {time_diff:.0f} seconds)")
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()

if __name__ == "__main__":
    main()
