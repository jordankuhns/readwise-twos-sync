"""Twos API client."""

import requests
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TwosClient:
    """Client for interacting with Twos API."""
    
    API_URL = "https://www.twosapp.com/apiV2/user/addToToday"
    
    def __init__(self, user_id: str, token: str):
        """Initialize Twos client.
        
        Args:
            user_id: Twos user ID
            token: Twos API token
        """
        self.user_id = user_id
        self.token = token
        self.headers = {"Content-Type": "application/json"}
    
    def post_highlights(self, highlights: List[Dict], books: Dict[int, Dict[str, str]]):
        """Post highlights to Twos.
        
        Args:
            highlights: List of highlight dictionaries from Readwise
            books: Dictionary mapping book IDs to book metadata
        """
        today_title = datetime.now().strftime("%a %b %d, %Y")
        
        if not highlights:
            self._post_no_highlights_message(today_title)
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
                    "token": self.token,
                    "user_id": self.user_id
                }
                
                response = requests.post(self.API_URL, headers=self.headers, json=payload)
                response.raise_for_status()
                successful_posts += 1
                
            except requests.RequestException as e:
                logger.error(f"Failed to post highlight to Twos: {e}")
                failed_posts += 1
        
        logger.info(f"Posted {successful_posts} highlights to Twos")
        if failed_posts > 0:
            logger.warning(f"Failed to post {failed_posts} highlights")
    
    def _post_no_highlights_message(self, today_title: str):
        """Post a message when no new highlights are found."""
        payload = {
            "text": "No new highlights found.",
            "title": today_title,
            "token": self.token,
            "user_id": self.user_id
        }
        
        try:
            response = requests.post(self.API_URL, headers=self.headers, json=payload)
            response.raise_for_status()
            logger.info("Posted 'no highlights' message to Twos")
        except requests.RequestException as e:
            logger.error(f"Failed to post no-highlights message to Twos: {e}")