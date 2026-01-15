"""Historical performance filter for candidates"""

from loguru import logger

from skim.domain.models import Candidate
from skim.infrastructure.database.historical import (
    HistoricalDataService,
    PerformanceFilter,
)


class HistoricalPerformanceFilter:
    """Filters candidates by historical performance criteria"""

    def __init__(self, historical_service: HistoricalDataService | None):
        """Initialize historical performance filter

        Args:
            historical_service: Service for historical data queries
        """
        self.historical_service = historical_service
        self._enable_filtering = False
        self._filter_criteria = None

    def configure(
        self, enable_filtering: bool, filter_criteria: PerformanceFilter
    ) -> None:
        """Configure filter settings

        Args:
            enable_filtering: Whether to apply filtering
            filter_criteria: Criteria for filtering candidates
        """
        self._enable_filtering = enable_filtering
        self._filter_criteria = filter_criteria

    @property
    def name(self) -> str:
        """Filter identifier"""
        return "historical_performance"

    def filter(self, candidates: list[Candidate]) -> list[Candidate]:
        """Filter candidates by historical performance

        Args:
            candidates: List of candidates to filter

        Returns:
            Filtered list of candidates
        """
        if not self.historical_service:
            logger.debug(
                "Historical data service not available, skipping filter"
            )
            return candidates

        if not self._enable_filtering or not self._filter_criteria:
            logger.debug("Historical filtering disabled in config")
            return candidates

        tickers = [
            c.ticker.symbol if hasattr(c.ticker, "symbol") else str(c.ticker)
            for c in candidates
        ]

        qualified = self.historical_service.filter_by_performance(
            tickers, self._filter_criteria
        )

        qualified_set = set(qualified)

        filtered_candidates = [
            c
            for c in candidates
            if (
                c.ticker.symbol
                if hasattr(c.ticker, "symbol")
                else str(c.ticker)
            )
            in qualified_set
        ]

        rejected = set(tickers) - qualified_set
        if rejected:
            logger.info(
                f"Historical filter: {len(tickers)} -> {len(qualified)} candidates"
            )
            logger.debug(f"Rejected tickers: {rejected}")

        return filtered_candidates
