"""Command line interface for Readwise to Twos sync."""

import argparse
import logging
import os
import sys
from pathlib import Path

from .config import Config
from .sync_manager import SyncManager


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Sync Readwise highlights to Twos and Capacities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Environment Variables:
  READWISE_TOKEN    Your Readwise API token (required)
  TWOS_USER_ID      Your Twos user ID (required)
  TWOS_TOKEN        Your Twos API token (required)
  CAPACITIES_TOKEN  Capacities API token (optional)
  CAPACITIES_SPACE_ID Capacities space ID (optional)
  CAPACITIES_STRUCTURE_ID Capacities structure ID (optional)
  CAPACITIES_TEXT_PROPERTY_ID Capacities text property ID (optional)
  SYNC_DAYS_BACK    Days to look back for initial sync (default: 7)
  LAST_SYNC_FILE    Path to sync timestamp file (default: last_sync.json)

Examples:
  readwise-twos-sync                    # Run sync with default settings
  readwise-twos-sync --env-file .env    # Use specific .env file
  readwise-twos-sync --verbose          # Enable debug logging
        """
    )
    
    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file (default: .env in current directory)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    parser.add_argument(
        "--capacities-structure-id",
        type=str,
        help="Capacities structure ID (optional)"
    )

    parser.add_argument(
        "--capacities-text-property-id",
        type=str,
        help="Capacities text property ID (optional)"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0"
    )
    
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    # Allow CLI args to override environment variables
    if args.capacities_structure_id:
        os.environ["CAPACITIES_STRUCTURE_ID"] = args.capacities_structure_id
    if args.capacities_text_property_id:
        os.environ["CAPACITIES_TEXT_PROPERTY_ID"] = args.capacities_text_property_id

    try:
        # Initialize configuration
        config = Config(env_file=args.env_file)
        
        # Run sync
        sync_manager = SyncManager(config)
        sync_manager.sync()
        
        logger.info("Sync completed successfully!")
        
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
