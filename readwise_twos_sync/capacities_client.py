"""Capacities API client."""

import requests
from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CapacitiesClient:
    """Client for interacting with the Capacities API."""

    API_URL_TEMPLATE = "https://api.capacities.io/spaces/{space_id}/blocks"

    def __init__(self, token: str, space_id: str):
        """Initialize Capacities client.

        Args:
            token: Capacities API token
            space_id: Capacities space identifier
        """
        self.token = token
        self.space_id = space_id
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def post_highlights(self, highlights: List[Dict], books: Dict[int, Dict[str, str]]):
        """Post highlights to Capacities."""
        url = self.API_URL_TEMPLATE.format(space_id=self.space_id)
        today_title = datetime.now().strftime("%Y-%m-%d")

        if not highlights:
            payload = {"content": f"No new highlights for {today_title}"}
            try:
                response = requests.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                logger.info("Posted 'no highlights' message to Capacities")
            except requests.RequestException as e:
                logger.error(f"Failed to post no-highlights message to Capacities: {e}")
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

                payload = {"content": note_text.strip()}
                response = requests.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                successful_posts += 1
            except requests.RequestException as e:
                logger.error(f"Failed to post highlight to Capacities: {e}")
                failed_posts += 1

        logger.info(f"Posted {successful_posts} highlights to Capacities")
        if failed_posts:
            logger.warning(f"Failed to post {failed_posts} highlights")

