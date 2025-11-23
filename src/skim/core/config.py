"""Configuration management for Skim trading bot"""

import os
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class ScannerConfig:
    """Configuration for IBKR gap scanner parameters"""

    # Minimum gap percentage for scanning
    gap_threshold: float = 9.0

    # Minimum volume filter for gap scanning (shares) - ASX optimized
    volume_filter: int = 10000

    # Minimum price filter for gap scanning (dollars) - ASX optimized for 4c+ stocks
    price_filter: float = 0.05

    # Opening Range duration in minutes
    or_duration_minutes: int = 10

    # Polling interval for OR tracking (seconds)
    or_poll_interval_seconds: int = 30

    # Gap fill tolerance for position management (dollars)
    gap_fill_tolerance: float = 0.05

    # Breakout buffer above ORH (dollars)
    or_breakout_buffer: float = 0.1


def get_db_path() -> Path:
    """Get database path that works both locally and in production.

    Priority order:
    1. Production path: /opt/skim/data/skim.db (production deployment)
    2. Local development path: project_root/data/skim.db (development)

    Returns:
        Path object for the database file

    Raises:
        FileNotFoundError: If data directory cannot be created/accessed
    """
    # First try production path (production deployment)
    production_path = Path("/opt/skim/data/skim.db")
    if production_path.parent.exists():
        logger.debug(f"Using production database path: {production_path}")
        return production_path

    # Fallback to local development path (project root + data)
    # Use __file__ to reliably find project root from config.py location
    project_root = Path(__file__).parent.parent.parent.parent
    local_path = project_root / "data" / "skim.db"

    # Ensure data directory exists for local development
    local_path.parent.mkdir(parents=True, exist_ok=True)

    logger.debug(f"Using local database path: {local_path}")
    return local_path


def get_oauth_key_paths() -> dict[str, Path]:
    """Get OAuth key paths that work both locally and in production.

    Priority order:
    1. Production path: /opt/skim/oauth_keys (production deployment)
    2. Local development path: project_root/oauth_keys (development)

    Returns:
        Dictionary with 'signature' and 'encryption' Path objects

    Raises:
        FileNotFoundError: If OAuth keys directory is not found
    """
    # First try production path (production deployment)
    production_path = Path("/opt/skim/oauth_keys")
    if (
        production_path.exists()
        and (production_path / "private_signature.pem").exists()
    ):
        logger.debug(f"Using production OAuth key path: {production_path}")
        return {
            "signature": production_path / "private_signature.pem",
            "encryption": production_path / "private_encryption.pem",
        }

    # Fallback to local development path (project root + oauth_keys)
    # Use __file__ to reliably find project root from config.py location
    project_root = Path(__file__).parent.parent.parent.parent
    local_path = project_root / "oauth_keys"
    if local_path.exists() and (local_path / "private_signature.pem").exists():
        logger.debug(f"Using local OAuth key path: {local_path}")
        return {
            "signature": local_path / "private_signature.pem",
            "encryption": local_path / "private_encryption.pem",
        }

    # If neither path works, raise an informative error
    raise FileNotFoundError(
        f"OAuth keys directory not found. Tried:\n"
        f"  - Production: {production_path}\n"
        f"  - Local: {local_path}\n"
        f"Please ensure oauth_keys/ directory exists with private_signature.pem and private_encryption.pem"
    )


@dataclass
class Config:
    """Configuration for Skim trading bot loaded from environment variables"""

    # Fields without defaults (required parameters)
    ib_client_id: int
    discord_webhook_url: str | None
    scanner_config: ScannerConfig

    # Fields with defaults (optional parameters with sensible defaults)
    paper_trading: bool = True
    max_position_size: int = 10000
    max_positions: int = 50
    db_path: str = "/opt/skim/data/skim.db"

    # OAuth key paths - dynamically determined at runtime
    oauth_signature_key_path: str = ""
    oauth_encryption_key_path: str = ""

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables

        Returns:
            Config instance with values from environment

        Raises:
            ValueError: If required environment variables are missing or invalid
            FileNotFoundError: If OAuth key files are not found
        """
        # Allow override of paper trading via environment variable
        paper_trading_env = os.getenv("PAPER_TRADING", "true").lower() == "true"
        paper_trading = cls.paper_trading and paper_trading_env

        # Validate paper trading requirement
        if not paper_trading:
            raise ValueError(
                "PAPER_TRADING must be set to 'true'. "
                "This bot is designed for paper trading only."
            )

        # Get OAuth key paths dynamically
        oauth_paths = get_oauth_key_paths()

        # Get database path dynamically
        db_path = get_db_path()

        config = cls(
            ib_client_id=1,
            paper_trading=paper_trading,
            max_position_size=cls.max_position_size,
            max_positions=cls.max_positions,
            db_path=str(db_path),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            oauth_signature_key_path=str(oauth_paths["signature"]),
            oauth_encryption_key_path=str(oauth_paths["encryption"]),
            scanner_config=ScannerConfig(),
        )

        logger.info("Configuration loaded:")
        logger.info(f"  Client ID: {config.ib_client_id}")
        logger.info(f"  Paper Trading: {config.paper_trading}")
        logger.info(f"  Max Position Size: {config.max_position_size} shares")
        logger.info(f"  Max Positions: {config.max_positions}")
        logger.info(f"  Database: {config.db_path}")
        logger.info(
            f"  Discord Webhook: {'Configured' if config.discord_webhook_url else 'Not configured'}"
        )
        logger.info(f"  OAuth Signature Key: {config.oauth_signature_key_path}")
        logger.info(
            f"  OAuth Encryption Key: {config.oauth_encryption_key_path}"
        )
        logger.info(
            f"  Scanner Gap Threshold: {config.scanner_config.gap_threshold}%"
        )
        logger.info(
            f"  Scanner Volume Filter: {config.scanner_config.volume_filter:,} shares"
        )
        logger.info(
            f"  Scanner Price Filter: ${config.scanner_config.price_filter}"
        )
        logger.info(
            f"  OR Duration: {config.scanner_config.or_duration_minutes} minutes"
        )
        logger.info(
            f"  OR Poll Interval: {config.scanner_config.or_poll_interval_seconds} seconds"
        )
        logger.info(
            f"  Gap Fill Tolerance: ${config.scanner_config.gap_fill_tolerance}"
        )
        logger.info(
            f"  OR Breakout Buffer: ${config.scanner_config.or_breakout_buffer}"
        )

        return config
