"""Capacities API client."""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


class CapacitiesClient:
    """Client for interacting with the Capacities API."""

    SAVE_DAILY_NOTE_URL = "https://api.capacities.io/save-to-daily-note"

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

    def post_highlights(
        self,
        highlights: List[Dict],
        books: Dict[int, Dict[str, str]],
        structure_id: Optional[str] = None,
        property_definition_ids: Optional[Dict[str, str]] = None,
    ):
        """Post highlights to today's daily note in Capacities."""

        today_title = datetime.now().strftime("%Y-%m-%d")

        if not highlights:
            md_text = f"No new highlights for {today_title}"
        else:
            lines = []
            for highlight in highlights:
                text = highlight.get("text", "")
                book_id = highlight.get("book_id")
                book_meta = books.get(book_id, {})
                title = book_meta.get("title")
                author = book_meta.get("author")
                meta_parts = [part for part in [title, author] if part]
                meta = " — " + ", ".join(meta_parts) if meta_parts else ""
                lines.append(f"- {text}{meta}")
            md_text = "\n".join(lines)

        payload = {"spaceId": self.space_id, "mdText": md_text}

        try:
            response = requests.post(
                self.SAVE_DAILY_NOTE_URL, headers=self.headers, json=payload
            )
            response.raise_for_status()
            logger.info("Posted highlights to Capacities daily note")
        except requests.RequestException as e:
            logger.error(f"Failed to post highlights to Capacities: {e}")

