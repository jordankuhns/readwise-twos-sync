"""Sync manager for coordinating the sync process."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

from .config import Config
from .readwise_client import ReadwiseClient
from .twos_client import TwosClient
from .capacities_client import CapacitiesClient

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages the sync process between Readwise and destinations."""

    def __init__(self, config: Optional[Config] = None):
        """Initialize sync manager.

        Args:
            config: Configuration object. If None, creates a new one.
        """
        self.config = config or Config()
        self.readwise_client = ReadwiseClient(self.config.readwise_token)
        self.twos_client: Optional[TwosClient] = None
        if self.config.twos_user_id and self.config.twos_token:
            self.twos_client = TwosClient(
                self.config.twos_user_id, self.config.twos_token
            )
        self.capacities_client: Optional[CapacitiesClient] = None
        if self.config.capacities_token and self.config.capacities_space_id:
            self.capacities_client = CapacitiesClient(
                self.config.capacities_token, self.config.capacities_space_id
            )

    def sync(self):
        """Perform a full sync of highlights from Readwise to targets."""
        logger.info("Starting sync process")

        try:
            last_sync = self._get_last_sync_time()
            logger.info(f"Last sync: {last_sync}")

            highlights = self.readwise_client.fetch_highlights_since(last_sync)

            if not self.twos_client and not self.capacities_client:
                raise ValueError("No sync destinations configured")

            if highlights:
                books = self.readwise_client.fetch_all_books()
                if self.twos_client:
                    self.twos_client.post_highlights(highlights, books)
                if self.capacities_client:
                    self.capacities_client.post_highlights(highlights, books)
            else:
                logger.info("No new highlights found")
                if self.twos_client:
                    self.twos_client.post_highlights([], {})
                if self.capacities_client:
                    self.capacities_client.post_highlights([], {})

            self._save_last_sync_time(datetime.utcnow().isoformat())
            logger.info("Sync completed successfully")

        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise

    def _get_last_sync_time(self) -> str:
        """Get the last sync timestamp."""
        sync_file = self.config.last_sync_file

        if sync_file.exists():
            try:
                with open(sync_file, "r") as f:
                    data = json.load(f)
                    return data["last_sync"]
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid sync file format: {e}")

        default_time = datetime.utcnow() - timedelta(days=self.config.sync_days_back)
        return default_time.isoformat()

    def _save_last_sync_time(self, timestamp: str):
        """Save the last sync timestamp."""
        sync_file = self.config.last_sync_file

        try:
            with open(sync_file, "w") as f:
                json.dump({"last_sync": timestamp}, f, indent=2)
            logger.debug(f"Saved last sync time: {timestamp}")
        except IOError as e:
            logger.error(f"Failed to save sync time: {e}")
            raise

