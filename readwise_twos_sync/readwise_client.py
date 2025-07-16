"""Readwise API client."""

import requests
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class ReadwiseClient:
    """Client for interacting with Readwise API."""
    
    BASE_URL = "https://readwise.io/api/v2"
    
    def __init__(self, token: str):
        """Initialize Readwise client.
        
        Args:
            token: Readwise API token
        """
        self.token = token
        self.headers = {"Authorization": f"Token {token}"}
    
    def fetch_all_books(self) -> Dict[int, Dict[str, str]]:
        """Fetch all books from Readwise.
        
        Returns:
            Dictionary mapping book IDs to book metadata
        """
        books = {}
        next_url = f"{self.BASE_URL}/books/"
        
        while next_url:
            try:
                response = requests.get(next_url, headers=self.headers)
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
    
    def fetch_highlights_since(self, since: str) -> List[Dict]:
        """Fetch highlights updated since a given timestamp.
        
        Args:
            since: ISO timestamp string
            
        Returns:
            List of highlight dictionaries
        """
        highlights = []
        next_url = f"{self.BASE_URL}/highlights/"
        params = {"page_size": 1000}
        
        while next_url:
            try:
                response = requests.get(next_url, headers=self.headers, params=params)
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