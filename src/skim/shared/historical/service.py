"""Historical data service for querying stock performance metrics."""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

from loguru import logger

from skim.shared.historical.repository import HistoricalDataRepository

if TYPE_CHECKING:
    from skim.shared.historical.repository import HistoricalDatabase


@dataclass
class PerformanceFilter:
    """Criteria for filtering stocks by historical performance."""

    min_3month_return: float | None = None
    max_3month_return: float | None = None
    min_6month_return: float | None = None
    max_6month_return: float | None = None
    min_avg_volume: int | None = None
    require_3month_data: bool = True
    require_6month_data: bool = True


class HistoricalDataService:
    """Service for querying historical stock performance data."""

    def __init__(self, repo: HistoricalDataRepository):
        """Initialise historical data service.

        Args:
            repo: HistoricalDataRepository instance
        """
        self.repo = repo

    @classmethod
    def from_database(cls, db: "HistoricalDatabase") -> "HistoricalDataService":
        """Create service from database connection.

        Args:
            db: HistoricalDatabase instance

        Returns:
            HistoricalDataService instance
        """
        repo = HistoricalDataRepository(db)
        return cls(repo)

    def get_3month_return(self, ticker: str) -> float | None:
        """Get 3-month return percentage for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Return percentage or None if unavailable
        """
        perf = self.repo.get_3month_performance(ticker)
        return perf.return_percent if perf else None

    def get_6month_return(self, ticker: str) -> float | None:
        """Get 6-month return percentage for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Return percentage or None if unavailable
        """
        perf = self.repo.get_6month_performance(ticker)
        return perf.return_percent if perf else None

    def get_performance_summary(
        self, ticker: str
    ) -> dict[str, float | int | str | None]:
        """Get complete performance summary for a ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Dictionary with 3-month and 6-month performance metrics
        """
        perf_3m = self.repo.get_3month_performance(ticker)
        perf_6m = self.repo.get_6month_performance(ticker)

        return {
            "ticker": ticker.upper(),
            "3m_return": perf_3m.return_percent if perf_3m else None,
            "3m_start_date": perf_3m.start_date.isoformat()
            if perf_3m
            else None,
            "3m_end_date": perf_3m.end_date.isoformat() if perf_3m else None,
            "3m_avg_volume": perf_3m.avg_daily_volume if perf_3m else None,
            "6m_return": perf_6m.return_percent if perf_6m else None,
            "6m_start_date": perf_6m.start_date.isoformat()
            if perf_6m
            else None,
            "6m_end_date": perf_6m.end_date.isoformat() if perf_6m else None,
            "6m_avg_volume": perf_6m.avg_daily_volume if perf_6m else None,
        }

    def filter_by_performance(
        self,
        tickers: list[str],
        filter_criteria: PerformanceFilter,
    ) -> list[str]:
        """Filter a list of tickers by historical performance criteria.

        Args:
            tickers: List of stock ticker symbols to filter
            filter_criteria: PerformanceFilter with filtering criteria

        Returns:
            List of tickers that meet all criteria
        """
        qualified = []

        for ticker in tickers:
            perf_3m = self.repo.get_3month_performance(ticker)
            perf_6m = self.repo.get_6month_performance(ticker)

            if filter_criteria.require_3month_data and perf_3m is None:
                logger.debug(f"{ticker}: no 3-month data")
                continue

            if filter_criteria.require_6month_data and perf_6m is None:
                logger.debug(f"{ticker}: no 6-month data")
                continue

            if (
                filter_criteria.min_3month_return is not None
                and perf_3m is not None
                and perf_3m.return_percent < filter_criteria.min_3month_return
            ):
                logger.debug(
                    f"{ticker}: 3m return {perf_3m.return_percent:.2f}% < {filter_criteria.min_3month_return}%"
                )
                continue

            if (
                filter_criteria.max_3month_return is not None
                and perf_3m is not None
                and perf_3m.return_percent > filter_criteria.max_3month_return
            ):
                logger.debug(
                    f"{ticker}: 3m return {perf_3m.return_percent:.2f}% > {filter_criteria.max_3month_return}%"
                )
                continue

            if (
                filter_criteria.min_6month_return is not None
                and perf_6m is not None
                and perf_6m.return_percent < filter_criteria.min_6month_return
            ):
                logger.debug(
                    f"{ticker}: 6m return {perf_6m.return_percent:.2f}% < {filter_criteria.min_6month_return}%"
                )
                continue

            if (
                filter_criteria.max_6month_return is not None
                and perf_6m is not None
                and perf_6m.return_percent > filter_criteria.max_6month_return
            ):
                logger.debug(
                    f"{ticker}: 6m return {perf_6m.return_percent:.2f}% > {filter_criteria.max_6month_return}%"
                )
                continue

            if filter_criteria.min_avg_volume is not None:
                avg_vol = perf_3m.avg_daily_volume if perf_3m else 0
                if avg_vol < filter_criteria.min_avg_volume:
                    logger.debug(
                        f"{ticker}: avg volume {avg_vol:,} < {filter_criteria.min_avg_volume:,}"
                    )
                    continue

            qualified.append(ticker)

        logger.info(
            f"Filtered {len(tickers)} tickers -> {len(qualified)} qualified "
            f"(criteria: 3m>{filter_criteria.min_3month_return}%, "
            f"6m>{filter_criteria.min_6month_return}%, "
            f"vol>{filter_criteria.min_avg_volume})"
        )
        return qualified

    def get_top_performers(
        self, tickers: list[str], period_days: int = 90, limit: int = 20
    ) -> list[tuple[str, float]]:
        """Get top performing tickers by return.

        Args:
            tickers: List of stock ticker symbols
            period_days: Number of days to look back (90=3m, 180=6m)
            limit: Maximum number of results to return

        Returns:
            List of (ticker, return_percent) tuples, sorted by return descending
        """
        performances = []

        for ticker in tickers:
            perf = self.repo.get_performance(ticker, period_days)
            if perf:
                performances.append((ticker, perf.return_percent))

        performances.sort(key=lambda x: x[1], reverse=True)
        return performances[:limit]

    def get_database_stats(self) -> dict[str, int | date | None]:
        """Get statistics about the historical data database.

        Returns:
            Dictionary with database statistics
        """
        return {
            "tickers": self.repo.get_tickers_count(),
            "total_records": self.repo.get_total_records(),
            "latest_date": self.repo.get_latest_date(),
            "earliest_date": self.repo.get_earliest_date(),
        }
