"""Configuration management for Skim trading bot"""

import os
from dataclasses import dataclass

from loguru import logger


@dataclass
class Config:
    """Configuration for Skim trading bot loaded from environment variables"""

    # IB Gateway connection settings
    ib_host: str
    ib_port: int
    ib_client_id: int

    # Trading settings
    paper_trading: bool
    gap_threshold: float
    max_position_size: int
    max_positions: int

    # Database settings
    db_path: str

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables

        Returns:
            Config instance with values from environment

        Raises:
            ValueError: If required environment variables are missing or invalid
        """
        paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"

        # Validate paper trading requirement
        if not paper_trading:
            raise ValueError(
                "PAPER_TRADING must be set to 'true'. "
                "This bot is designed for paper trading only."
            )

        config = cls(
            ib_host=os.getenv("IB_HOST", "ibgateway"),
            ib_port=int(os.getenv("IB_PORT", "4004")),
            ib_client_id=int(os.getenv("IB_CLIENT_ID", "1")),
            paper_trading=paper_trading,
            gap_threshold=float(os.getenv("GAP_THRESHOLD", "3.0")),
            max_position_size=int(os.getenv("MAX_POSITION_SIZE", "1000")),
            max_positions=int(os.getenv("MAX_POSITIONS", "5")),
            db_path=os.getenv("DB_PATH", "data/skim.db"),
        )

        logger.info("Configuration loaded:")
        logger.info(f"  IB Host: {config.ib_host}:{config.ib_port}")
        logger.info(f"  Client ID: {config.ib_client_id}")
        logger.info(f"  Paper Trading: {config.paper_trading}")
        logger.info(f"  Gap Threshold: {config.gap_threshold}%")
        logger.info(f"  Max Position Size: {config.max_position_size} shares")
        logger.info(f"  Max Positions: {config.max_positions}")
        logger.info(f"  Database: {config.db_path}")

        return config
