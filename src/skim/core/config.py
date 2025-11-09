"""Configuration management for Skim trading bot"""

import os
from dataclasses import dataclass

from loguru import logger


@dataclass
class ScannerConfig:
    """Configuration for IBKR gap scanner parameters"""

    # Minimum volume filter for gap scanning (shares)
    volume_filter: int = 50000

    # Minimum price filter for gap scanning (dollars)
    price_filter: float = 0.50

    # Opening Range duration in minutes
    or_duration_minutes: int = 10

    # Polling interval for OR tracking (seconds)
    or_poll_interval_seconds: int = 30

    # Gap fill tolerance for position management (dollars)
    gap_fill_tolerance: float = 1.0

    # Breakout buffer above ORH (dollars)
    or_breakout_buffer: float = 0.1


@dataclass
class Config:
    """Configuration for Skim trading bot loaded from environment variables"""

    # Fields without defaults (required parameters)
    ib_client_id: int
    discord_webhook_url: str | None
    scanner_config: ScannerConfig

    # Fields with defaults (optional parameters with sensible defaults)
    paper_trading: bool = True
    gap_threshold: float = 3.0
    max_position_size: int = 1000
    max_positions: int = 5
    db_path: str = "/app/data/skim.db"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables

        Returns:
            Config instance with values from environment

        Raises:
            ValueError: If required environment variables are missing or invalid
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

        config = cls(
            ib_client_id=int(os.getenv("IB_CLIENT_ID", "1")),
            paper_trading=paper_trading,
            gap_threshold=float(
                os.getenv("GAP_THRESHOLD", str(cls.gap_threshold))
            ),
            max_position_size=int(
                os.getenv("MAX_POSITION_SIZE", str(cls.max_position_size))
            ),
            max_positions=int(
                os.getenv("MAX_POSITIONS", str(cls.max_positions))
            ),
            db_path=os.getenv("DB_PATH", cls.db_path),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL"),
            scanner_config=ScannerConfig(),
        )

        logger.info("Configuration loaded:")
        logger.info(f"  Client ID: {config.ib_client_id}")
        logger.info(f"  Paper Trading: {config.paper_trading}")
        logger.info(f"  Gap Threshold: {config.gap_threshold}%")
        logger.info(f"  Max Position Size: {config.max_position_size} shares")
        logger.info(f"  Max Positions: {config.max_positions}")
        logger.info(f"  Database: {config.db_path}")
        logger.info(
            f"  Discord Webhook: {'Configured' if config.discord_webhook_url else 'Not configured'}"
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
