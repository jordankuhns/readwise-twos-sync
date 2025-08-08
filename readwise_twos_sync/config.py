"""Configuration management for Readwise to Twos/Capacities sync."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Configuration class for managing environment variables and settings."""

    def __init__(self, env_file: Optional[str] = None):
        """Initialize configuration.

        Args:
            env_file: Path to .env file. If None, looks for .env in current directory.
        """
        if os.getenv("GITHUB_ACTIONS") != "true":
            env_path = Path(env_file) if env_file else Path('.') / '.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)

        self._validate_required_vars()

    @property
    def readwise_token(self) -> str:
        """Get Readwise API token."""
        return os.environ["READWISE_TOKEN"]

    @property
    def twos_user_id(self) -> str:
        """Get Twos user ID."""
        return os.environ["TWOS_USER_ID"]

    @property
    def twos_token(self) -> str:
        """Get Twos API token."""
        return os.environ["TWOS_TOKEN"]

    @property
    def capacities_token(self) -> Optional[str]:
        """Get Capacities API token if provided."""
        return os.environ.get("CAPACITIES_TOKEN")

    @property
    def capacities_space_id(self) -> Optional[str]:
        """Get Capacities space ID if provided."""
        return os.environ.get("CAPACITIES_SPACE_ID")

    @property
    def capacities_structure_id(self) -> Optional[str]:
        """Get Capacities structure ID if provided."""
        return os.environ.get("CAPACITIES_STRUCTURE_ID")

    @property
    def capacities_text_property_id(self) -> Optional[str]:
        """Get Capacities text property ID if provided."""
        return os.environ.get("CAPACITIES_TEXT_PROPERTY_ID")

    @property
    def sync_days_back(self) -> int:
        """Number of days to look back for initial sync."""
        return int(os.environ.get("SYNC_DAYS_BACK", "7"))

    @property
    def last_sync_file(self) -> Path:
        """Path to last sync timestamp file."""
        return Path(os.environ.get("LAST_SYNC_FILE", "last_sync.json"))

    def _validate_required_vars(self):
        """Validate that all required environment variables are set."""
        required_vars = ["READWISE_TOKEN", "TWOS_USER_ID", "TWOS_TOKEN"]
        missing_vars = [var for var in required_vars if not os.environ.get(var)]

        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}\n"
                "Please set these in your environment or .env file.",
            )

        # Capacities credentials are optional, but if any is provided,
        # ensure CAPACITIES_TOKEN, CAPACITIES_SPACE_ID, CAPACITIES_STRUCTURE_ID,
        # and CAPACITIES_TEXT_PROPERTY_ID are all set.
        cap_token = os.environ.get("CAPACITIES_TOKEN")
        cap_space = os.environ.get("CAPACITIES_SPACE_ID")
        cap_structure = os.environ.get("CAPACITIES_STRUCTURE_ID")
        cap_text_prop = os.environ.get("CAPACITIES_TEXT_PROPERTY_ID")
        if any([cap_token, cap_space, cap_structure, cap_text_prop]):
            missing = []
            if not cap_token:
                missing.append("CAPACITIES_TOKEN")
            if not cap_space:
                missing.append("CAPACITIES_SPACE_ID")
            if not cap_structure:
                missing.append("CAPACITIES_STRUCTURE_ID")
            if not cap_text_prop:
                missing.append("CAPACITIES_TEXT_PROPERTY_ID")
            if missing:
                raise ValueError(
                    f"Missing required Capacities environment variables: {', '.join(missing)}"
                )

