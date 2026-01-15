"""Database path utilities for historical data."""

from pathlib import Path


def get_historical_db_path() -> Path:
    """Get historical database path that works both locally and in production.

    This database is used for storing historical price data that is shared
    between the trading and analysis modules.

    Priority order:
    1. Production path: /opt/skim/data/skim_historical.db (production deployment)
    2. Local development path: project_root/data/skim_historical.db (development)

    Returns:
        Path object for the historical database file

    Raises:
        FileNotFoundError: If data directory cannot be created/accessed
    """
    production_path = Path("/opt/skim/data/skim_historical.db")
    if production_path.parent.exists():
        return production_path

    project_root = Path(__file__).parent.parent.parent.parent
    local_path = project_root / "data" / "skim_historical.db"

    local_path.parent.mkdir(parents=True, exist_ok=True)

    return local_path
