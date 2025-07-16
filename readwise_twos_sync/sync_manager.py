"""Sync manager for coordinating the sync process."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import logging

from .config import Config
from .readwise_client import ReadwiseClient
from .twos_client import TwosClient

logger = logging.getLogger(__name__)


class SyncManager:
    """Manages the sync process between Readwise and Twos."""
    
    def __init__(self, config: Optional[Config] = None):
        """Initialize sync manager.
        
        Args:
            config: Configuration object. If None, creates a new one.
        """
        self.config = config or Config()
        self.readwise_client = ReadwiseClient(self.config.readwise_token)
        self.twos_client = TwosClient(self.config.twos_user_id, self.config.twos_token)
    
    def sync(self):
        """Perform a full sync of highlights from Readwise to Twos."""
        logger.info("Starting sync process")
        
        try:
            # Get last sync time
            last_sync = self._get_last_sync_time()
            logger.info(f"Last sync: {last_sync}")
            
            # Fetch new highlights
            highlights = self.readwise_client.fetch_highlights_since(last_sync)
            
            if highlights:
                # Fetch books metadata
                books = self.readwise_client.fetch_all_books()
                
                # Post to Twos
                self.twos_client.post_highlights(highlights, books)
            else:
                logger.info("No new highlights found")
                # Still post a message to Twos
                self.twos_client.post_highlights([], {})
            
            # Update last sync time
            self._save_last_sync_time(datetime.utcnow().isoformat())
            logger.info("Sync completed successfully")
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise
    
    def _get_last_sync_time(self) -> str:
        """Get the last sync timestamp.
        
        Returns:
            ISO timestamp string
        """
        sync_file = self.config.last_sync_file
        
        if sync_file.exists():
            try:
                with open(sync_file, "r") as f:
                    data = json.load(f)
                    return data["last_sync"]
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Invalid sync file format: {e}")
        
        # Default to configured days back
        default_time = datetime.utcnow() - timedelta(days=self.config.sync_days_back)
        return default_time.isoformat()
    
    def _save_last_sync_time(self, timestamp: str):
        """Save the last sync timestamp.
        
        Args:
            timestamp: ISO timestamp string
        """
        sync_file = self.config.last_sync_file
        
        try:
            with open(sync_file, "w") as f:
                json.dump({"last_sync": timestamp}, f, indent=2)
            logger.debug(f"Saved last sync time: {timestamp}")
        except IOError as e:
            logger.error(f"Failed to save sync time: {e}")
            raise