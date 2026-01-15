"""Database loader for loading and managing ASX stock data from SQLite."""

from pathlib import Path

from loguru import logger
from tqdm import tqdm

from skim.infrastructure.database.historical import (
    HistoricalDataRepository,
    HistoricalDataService,
)
from skim.infrastructure.database.historical.repository import (
    HistoricalDatabase,
)
from skim.shared.database import get_historical_db_path


class DatabaseLoader:
    """Loads and manages ASX stock data from the shared historical database."""

    def __init__(
        self,
        db_path: str | Path | None = None,
        min_price: float = 0.20,
        min_volume: int = 50000,
    ):
        """Initialise database loader.

        Args:
            db_path: Path to historical database (auto-detected if not provided)
            min_price: Minimum price filter (default $0.20)
            min_volume: Minimum average volume filter (default 50k)
        """
        if db_path is None:
            db_path = get_historical_db_path()

        self.db = HistoricalDatabase(str(db_path))
        self.repo = HistoricalDataRepository(self.db)
        self.service = HistoricalDataService(self.repo)
        self.min_price = min_price
        self.min_volume = min_volume

    def load_all(self, quiet: bool = False) -> dict[str, dict]:
        """Load all stocks from database that meet criteria.

        Args:
            quiet: Suppress progress output

        Returns:
            Dictionary mapping ticker -> stock data dictionary
        """
        tickers = self.repo.get_tickers_with_data()

        if not quiet:
            logger.info(f"Found {len(tickers)} tickers in database")

        stocks = {}

        for ticker in tqdm(tickers, desc="Loading stocks", disable=quiet):
            latest = self.repo.get_latest_date()
            if latest is None:
                continue

            perf_3m = self.repo.get_3month_performance(ticker)
            if perf_3m is None:
                continue

            if perf_3m.avg_daily_volume < self.min_volume:
                continue

            stock = {
                "ticker": ticker,
                "latest_date": latest.isoformat(),
                "3m_return": perf_3m.return_percent,
                "3m_avg_volume": perf_3m.avg_daily_volume,
                "3m_trading_days": perf_3m.trading_days,
            }

            perf_6m = self.repo.get_6month_performance(ticker)
            if perf_6m:
                stock["6m_return"] = perf_6m.return_percent
                stock["6m_avg_volume"] = perf_6m.avg_daily_volume
                stock["6m_trading_days"] = perf_6m.trading_days

            stocks[ticker] = stock

        if not quiet:
            logger.info(f"Loaded {len(stocks)} stocks meeting criteria")

        return stocks

    def get_stock(self, ticker: str) -> dict | None:
        """Get stock data by ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Stock data dictionary or None if not found
        """
        latest = self.repo.get_latest_date()
        if latest is None:
            return None

        perf_3m = self.repo.get_3month_performance(ticker)
        if perf_3m is None:
            return None

        stock = {
            "ticker": ticker,
            "latest_date": latest.isoformat(),
            "3m_return": perf_3m.return_percent,
            "3m_avg_volume": perf_3m.avg_daily_volume,
            "3m_trading_days": perf_3m.trading_days,
        }

        perf_6m = self.repo.get_6month_performance(ticker)
        if perf_6m:
            stock["6m_return"] = perf_6m.return_percent
            stock["6m_avg_volume"] = perf_6m.avg_daily_volume
            stock["6m_trading_days"] = perf_6m.trading_days

        return stock

    def get_all_tickers(self) -> list[str]:
        """Get list of all tickers in database.

        Returns:
            Sorted list of ticker symbols
        """
        return sorted(self.repo.get_tickers_with_data())

    def get_top_performers(
        self, period_days: int = 90, limit: int = 20
    ) -> list[tuple[str, float]]:
        """Get top performing tickers by return.

        Args:
            period_days: Number of days to look back (90=3m, 180=6m)
            limit: Maximum number of results

        Returns:
            List of (ticker, return_percent) tuples sorted descending
        """
        tickers = self.get_all_tickers()
        return self.service.get_top_performers(tickers, period_days, limit)

    def get_database_stats(self) -> dict:
        """Get database statistics.

        Returns:
            Dictionary with database stats
        """
        return self.service.get_database_stats()

    def close(self) -> None:
        """Close database connection."""
        self.db.close()
