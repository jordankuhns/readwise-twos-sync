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
    def twos_user_id(self) -> Optional[str]:
        """Get Twos user ID if provided."""
        return os.environ.get("TWOS_USER_ID")

    @property
    def twos_token(self) -> Optional[str]:
        """Get Twos API token if provided."""
        return os.environ.get("TWOS_TOKEN")

    @property
    def capacities_token(self) -> Optional[str]:
        """Get Capacities API token if provided."""
        return os.environ.get("CAPACITIES_TOKEN")

    @property
    def capacities_space_id(self) -> Optional[str]:
        """Get Capacities space ID if provided."""
        return os.environ.get("CAPACITIES_SPACE_ID")

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
        if not os.environ.get("READWISE_TOKEN"):
            raise ValueError("Missing required environment variable: READWISE_TOKEN")

        # Collect provided credentials
        twos_user = os.environ.get("TWOS_USER_ID")
        twos_token = os.environ.get("TWOS_TOKEN")
        cap_token = os.environ.get("CAPACITIES_TOKEN")
        cap_space = os.environ.get("CAPACITIES_SPACE_ID")

        # Validate Twos credentials if either is provided
        if twos_user or twos_token:
            missing = []
            if not twos_user:
                missing.append("TWOS_USER_ID")
            if not twos_token:
                missing.append("TWOS_TOKEN")
            if missing:
                raise ValueError(
                    f"Missing required Twos environment variables: {', '.join(missing)}"
                )

        # Validate Capacities credentials if either is provided
        if cap_token or cap_space:
            missing = []
            if not cap_token:
                missing.append("CAPACITIES_TOKEN")
            if not cap_space:
                missing.append("CAPACITIES_SPACE_ID")
            if missing:
                raise ValueError(
                    f"Missing required Capacities environment variables: {', '.join(missing)}"
                )

        # Ensure at least one destination is configured
        if not ((twos_user and twos_token) or (cap_token and cap_space)):
            raise ValueError(
                "Please provide Twos or Capacities credentials to enable syncing"
            )

