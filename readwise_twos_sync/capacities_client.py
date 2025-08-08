"""Capacities API client."""

import requests
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class CapacitiesClient:
    """Client for interacting with the Capacities API."""

    API_URL_TEMPLATE = "https://api.capacities.io/spaces/{space_id}/objects"
    SPACE_INFO_URL = "https://api.capacities.io/spaces/{space_id}/space-info"

    def __init__(
        self,
        token: str,
        space_id: str,
        structure_id: Optional[str] = None,
        property_definition_ids: Optional[Dict[str, str]] = None,
    ):
        """Initialize Capacities client.

        Args:
            token: Capacities API token
            space_id: Capacities space identifier
            structure_id: Optional Capacities structure identifier
            property_definition_ids: Optional mapping of property names to definition IDs
        """
        self.token = token
        self.space_id = space_id
        self.structure_id = structure_id
        self.property_definition_ids = property_definition_ids or {}
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def _fetch_space_info(self) -> Dict:
        """Fetch space information including structures and property definitions."""
        url = self.SPACE_INFO_URL.format(space_id=self.space_id)
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def _ensure_structure_and_properties(
        self,
        structure_id: Optional[str],
        property_definition_ids: Optional[Dict[str, str]],
    ) -> (str, Dict[str, str]):
        """Ensure structure ID and property IDs are available.

        Fetches space info if either value is missing.
        """

        structure_id = structure_id or self.structure_id
        property_definition_ids = property_definition_ids or self.property_definition_ids

        if structure_id and property_definition_ids:
            return structure_id, property_definition_ids

        info = self._fetch_space_info()

        if not structure_id:
            structures = info.get("structures", [])
            structure_id = next(
                (s.get("id") for s in structures if s.get("name") == "RootPage"),
                structures[0]["id"] if structures else None,
            )

        if not property_definition_ids:
            property_definition_ids = {
                pd.get("name"): pd.get("id")
                for pd in info.get("propertyDefinitions", [])
            }

        return structure_id, property_definition_ids

    def post_highlights(
        self,
        highlights: List[Dict],
        books: Dict[int, Dict[str, str]],
        structure_id: Optional[str] = None,
        property_definition_ids: Optional[Dict[str, str]] = None,
    ):
        """Post highlights to Capacities."""

        structure_id, property_definition_ids = self._ensure_structure_and_properties(
            structure_id, property_definition_ids
        )

        url = self.API_URL_TEMPLATE.format(space_id=self.space_id)
        today_title = datetime.now().strftime("%Y-%m-%d")

        def _build_properties(text: str, title: Optional[str] = None, author: Optional[str] = None) -> Dict[str, str]:
            properties: Dict[str, str] = {}
            text_id = property_definition_ids.get("text")
            if text_id:
                properties[text_id] = text
            title_id = property_definition_ids.get("title")
            if title_id and title:
                properties[title_id] = title
            author_id = property_definition_ids.get("author")
            if author_id and author:
                properties[author_id] = author
            return properties

        if not highlights:
            properties = _build_properties(f"No new highlights for {today_title}")
            payload = {"structureId": structure_id, "properties": properties}
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

                title = book_meta.get("title")
                author = book_meta.get("author")

                properties = _build_properties(text, title, author)
                payload = {"structureId": structure_id, "properties": properties}
                response = requests.post(url, headers=self.headers, json=payload)
                response.raise_for_status()
                successful_posts += 1
            except requests.RequestException as e:
                logger.error(f"Failed to post highlight to Capacities: {e}")
                failed_posts += 1

        logger.info(f"Posted {successful_posts} highlights to Capacities")
        if failed_posts:
            logger.warning(f"Failed to post {failed_posts} highlights")

