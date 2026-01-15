"""ORH Breakout Strategy - Gap and News scanning with Opening Range breakout"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from loguru import logger

from skim.domain.strategies.base import Strategy
from skim.domain.strategies.context import StrategyContext
from skim.domain.strategies.registry import register_strategy
from skim.infrastructure.database.historical import PerformanceFilter

if TYPE_CHECKING:
    pass


@register_strategy("orh_breakout")
class ORHBreakoutStrategy(Strategy):
    """Opening Range High breakout strategy using gap and news scanning

    Strategy phases:
    1. Scan for gap candidates (pre-market)
    2. Scan for news candidates (pre-market)
    3. Track opening ranges (first 5 minutes)
    4. Execute breakouts when price > ORH
    5. Manage positions with stop losses at ORL
    """

    def __init__(self, context: StrategyContext):
        """Initialise ORH breakout strategy

        Args:
            context: Strategy context with all dependencies
        """
        self.ctx = context

        from skim.trading.monitor import Monitor
        from skim.trading.scanners import GapScanner, NewsScanner

        from .range_tracker import RangeTracker
        from .trader import Trader

        self.gap_scanner = GapScanner(
            scanner_service=self.ctx.scanner_service,
            gap_threshold=self.ctx.config.scanner_config.gap_threshold,
        )
        self.news_scanner = NewsScanner()
        self.range_tracker = RangeTracker(
            market_data_service=self.ctx.market_data,
            orh_repo=self.ctx.repository,
        )
        self.trader = Trader(
            self.ctx.market_data, self.ctx.order_service, self.ctx.database
        )
        self.monitor = Monitor(self.ctx.market_data)

        logger.info("ORH Breakout Strategy initialised")

    @property
    def name(self) -> str:
        """Strategy identifier"""
        return "orh_breakout"

    async def _ensure_connection(self) -> None:
        """Ensure IB connection is active"""
        if not self.ctx.connection_manager.is_connected():
            logger.info("Connecting to IBKR...")
            await self.ctx.connection_manager.connect(timeout=20)

    async def setup(self) -> None:
        """Purge candidates before scanning"""
        await self.purge_candidates()

    async def purge_candidates(
        self, only_before_utc_date: date | None = None
    ) -> int:
        """Clear candidate rows before a scan

        Args:
            only_before_utc_date: Optional UTC date to limit deletions

        Returns:
            Number of candidates deleted
        """
        logger.info("Purging candidates...")
        try:
            deleted = self.ctx.database.purge_candidates(
                only_before_utc_date,
                strategy_name=self.ctx.repository.STRATEGY_NAME,
            )
            logger.info(f"Deleted {deleted} candidate rows")
            return deleted
        except Exception as e:
            logger.error(f"Candidate purge failed: {e}", exc_info=True)
            return 0

    async def scan_gaps(self) -> int:
        """Scan for gap-only candidates

        Returns:
            Number of gap candidates found
        """
        logger.info("Scanning for gap-only candidates...")
        try:
            await self._ensure_connection()
            candidates = await self.gap_scanner.find_gap_candidates()

            count = len(candidates)
            if not candidates:
                logger.warning("No gap candidates found")
            else:
                for candidate in candidates:
                    self.ctx.repository.save_gap_candidate(candidate)

            logger.info(f"Gap scan complete. Found {count} candidates")
            return count
        except Exception as e:
            logger.error(f"Gap scan failed: {e}", exc_info=True)
            return 0

    async def scan_news(self) -> int:
        """Scan for news-only candidates

        Returns:
            Number of news candidates found
        """
        logger.info("Scanning for news-only candidates...")
        try:
            candidates = await self.news_scanner.find_news_candidates()

            count = len(candidates)
            if not candidates:
                logger.warning("No news candidates found")
            else:
                for candidate in candidates:
                    self.ctx.repository.save_news_candidate(candidate)

            logger.info(f"News scan complete. Found {count} candidates")
            return count
        except Exception as e:
            logger.error(f"News scan failed: {e}", exc_info=True)
            return 0

    async def scan(self) -> int:
        """Full scan phase - gaps and news

        Returns:
            Total number of candidates found
        """
        gap_count = await self.scan_gaps()
        news_count = await self.scan_news()
        return gap_count + news_count

    async def track_ranges(self) -> int:
        """Track opening ranges for candidates without ORH/ORL values

        Returns:
            Number of candidates updated with opening ranges
        """
        logger.info("Tracking opening ranges...")
        try:
            await self._ensure_connection()
            updated = await self.range_tracker.track_opening_ranges()
            logger.info(
                f"Opening range tracking complete. Updated {updated} candidates"
            )
            return updated
        except Exception as e:
            logger.error(f"Opening range tracking failed: {e}", exc_info=True)
            return 0

    def filter_by_historical_performance(self, tickers: list[str]) -> list[str]:
        """Filter tickers by historical performance criteria.

        Args:
            tickers: List of ticker symbols to filter

        Returns:
            List of tickers that meet historical performance criteria
        """
        if not self.ctx.historical_service:
            logger.debug(
                "Historical data service not available, skipping filter"
            )
            return tickers

        hist_config = self.ctx.config.historical_config
        if not hist_config.enable_filtering:
            logger.debug("Historical filtering disabled in config")
            return tickers

        filter_criteria = PerformanceFilter(
            min_3month_return=hist_config.min_3month_return,
            max_3month_return=hist_config.max_3month_return,
            min_6month_return=hist_config.min_6month_return,
            min_avg_volume=hist_config.min_avg_volume,
            require_3month_data=hist_config.require_data,
            require_6month_data=False,
        )

        qualified = self.ctx.historical_service.filter_by_performance(
            tickers, filter_criteria
        )

        logger.info(
            f"Historical filter: {len(tickers)} -> {len(qualified)} candidates"
        )
        return qualified

    async def trade(self) -> int:
        """Execute breakout entries for tradeable candidates

        Returns:
            Number of trades executed
        """
        logger.info("Executing breakouts...")
        try:
            await self._ensure_connection()
            candidates = self.ctx.repository.get_tradeable_candidates()
            if not candidates:
                logger.info("No tradeable candidates found.")
                return 0

            logger.info(f"Found {len(candidates)} tradeable candidates")

            tickers = [c.ticker for c in candidates]
            qualified_tickers = self.filter_by_historical_performance(tickers)

            if len(qualified_tickers) < len(tickers):
                filtered = set(tickers) - set(qualified_tickers)
                logger.info(
                    f"Filtered out {len(filtered)} candidates: {filtered}"
                )

            tradeable = [c for c in candidates if c.ticker in qualified_tickers]

            if not tradeable:
                logger.info("No candidates passed historical filter")
                return 0

            logger.info(f"Trading {len(tradeable)} candidates")
            events = await self.trader.execute_breakouts(tradeable)

            for event in events:
                self.ctx.notifier.send_trade_notification(
                    action=event.action,
                    ticker=event.ticker,
                    quantity=event.quantity,
                    price=event.price,
                    pnl=event.pnl,
                )

            return len(events)
        except Exception as e:
            logger.error(f"Trade execution failed: {e}", exc_info=True)
            return 0

    async def manage(self) -> int:
        """Monitor positions and execute stops

        Returns:
            Number of positions managed/exited
        """
        logger.info("Managing positions...")
        try:
            await self._ensure_connection()
            positions = self.ctx.database.get_open_positions()
            if not positions:
                logger.info("No open positions to manage.")
                return 0

            stops_hit = await self.monitor.check_stops(positions)
            if not stops_hit:
                logger.info("No stop losses hit.")
                return 0

            events = await self.trader.execute_stops(stops_hit)

            for event in events:
                self.ctx.notifier.send_trade_notification(
                    action=event.action,
                    ticker=event.ticker,
                    quantity=event.quantity,
                    price=event.price,
                    pnl=event.pnl,
                )

            return len(events)
        except Exception as e:
            logger.error(f"Position management failed: {e}", exc_info=True)
            return 0

    async def alert(self) -> int:
        """Send Discord notification for alertable candidates

        Returns:
            Number of candidates alerted
        """
        logger.info("Sending alert for alertable candidates...")
        try:
            candidates = self.ctx.repository.get_alertable_candidates()
            count = len(candidates)

            if not candidates:
                logger.info("No alertable candidates to alert")
                return 0

            payload = [
                {
                    "ticker": c.ticker,
                    "gap_percent": c.gap_percent,
                    "headline": c.headline,
                }
                for c in candidates
            ]

            self.ctx.notifier.send_tradeable_candidates(count, payload)
            logger.info(f"Alert sent for {count} alertable candidates")
            return count
        except Exception as e:
            logger.error(f"Alert failed: {e}", exc_info=True)
            return 0

    async def health_check(self) -> bool:
        """Check IBKR connection and strategy health

        Returns:
            True if strategy is healthy
        """
        logger.info("Performing health check...")
        try:
            await self._ensure_connection()
            account = self.ctx.connection_manager.get_account()
            logger.info(f"Health check OK. Connected account: {account}")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return False
