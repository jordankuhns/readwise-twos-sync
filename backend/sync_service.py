"""
Sync service for Readwise to Twos
"""

import requests
import logging
from datetime import datetime, timedelta
from app import db
from models import SyncLog

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def perform_sync(readwise_token, twos_user_id, twos_token, days_back=7, user_id=None):
    """
    Perform a sync from Readwise to Twos.
    
    Args:
        readwise_token: Readwise API token
        twos_user_id: Twos user ID
        twos_token: Twos API token
        days_back: Number of days to look back for highlights
        user_id: User ID for logging (optional)
        
    Returns:
        Dict with sync results
    """
    logger.info(f"Starting sync for user {user_id}, looking back {days_back} days")
    
    try:
        # Calculate since timestamp
        since_time = datetime.utcnow() - timedelta(days=days_back)
        since = since_time.isoformat()
        
        # Fetch highlights
        highlights = fetch_highlights_since(readwise_token, since)
        
        if highlights:
            # Fetch books metadata
            books = fetch_all_books(readwise_token)
            
            # Post to Twos
            post_highlights_to_twos(highlights, books, twos_user_id, twos_token)
            
            message = f"Successfully synced {len(highlights)} highlights to Twos!"
        else:
            # Still post a message to Twos
            post_highlights_to_twos([], {}, twos_user_id, twos_token)
            message = "No new highlights found, but posted update to Twos."
        
        # Log successful sync
        if user_id:
            log = SyncLog(
                user_id=user_id,
                status="success",
                highlights_synced=len(highlights),
                details=message
            )
            db.session.add(log)
            db.session.commit()
        
        return {
            "success": True,
            "message": message,
            "highlights_synced": len(highlights)
        }
        
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        
        # Log failed sync
        if user_id:
            log = SyncLog(
                user_id=user_id,
                status="failed",
                highlights_synced=0,
                details=str(e)
            )
            db.session.add(log)
            db.session.commit()
        
        raise

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
                
                # Skip Readwise tutorial book
                if title.strip().lower() == "how to use readwise":
                    continue
                
                books[book_id] = {
                    "title": title,
                    "author": author
                }
            
            next_url = data.get("next")
            
        except requests.RequestException as e:
            logger.error(f"Error fetching books: {e}")
            raise
    
    logger.info(f"Fetched {len(books)} books from Readwise")
    return books

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
            params = {}  # Only use params on first request
            
        except requests.RequestException as e:
            logger.error(f"Error fetching highlights: {e}")
            raise
    
    logger.info(f"Fetched {len(highlights)} new highlights since {since}")
    return highlights

def post_highlights_to_twos(highlights, books, twos_user_id, twos_token):
    """Post highlights to Twos."""
    api_url = "https://www.twosapp.com/apiV2/user/addToToday"
    headers = {"Content-Type": "application/json"}
    today_title = datetime.now().strftime("%a %b %d, %Y")
    
    if not highlights:
        # Post no highlights message
        payload = {
            "text": "No new highlights found.",
            "title": today_title,
            "token": twos_token,
            "user_id": twos_user_id
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            logger.info("Posted 'no highlights' message to Twos")
        except requests.RequestException as e:
            logger.error(f"Failed to post no-highlights message to Twos: {e}")
        return
    
    successful_posts = 0
    failed_posts = 0
    
    for highlight in highlights:
        try:
            book_id = highlight.get("book_id")
            text = highlight.get("text")
            book_meta = books.get(book_id)
            
            if not book_meta:
                logger.warning(f"No book metadata found for book ID {book_id}")
                continue
            
            title = book_meta["title"]
            author = book_meta["author"]
            note_text = f"{title}, {author}: {text}"
            
            payload = {
                "text": note_text.strip(),
                "title": today_title,
                "token": twos_token,
                "user_id": twos_user_id
            }
            
            response = requests.post(api_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            successful_posts += 1
            
        except requests.RequestException as e:
            logger.error(f"Failed to post highlight to Twos: {e}")
            failed_posts += 1
    
    logger.info(f"Posted {successful_posts} highlights to Twos")
    if failed_posts > 0:
        logger.warning(f"Failed to post {failed_posts} highlights")