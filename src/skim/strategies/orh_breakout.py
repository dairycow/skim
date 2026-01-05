"""ORH Breakout Strategy - Gap and News scanning with Opening Range breakout"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from loguru import logger

from skim.strategies.base import Strategy

if TYPE_CHECKING:
    from skim.brokers.ibkr_client import IBKRClient
    from skim.brokers.ibkr_gap_scanner import IBKRGapScanner
    from skim.brokers.ibkr_market_data import IBKRMarketData
    from skim.brokers.ibkr_orders import IBKROrders
    from skim.core.config import Config
    from skim.data.database import Database
    from skim.notifications.discord import DiscordNotifier


class ORHBreakoutStrategy(Strategy):
    """Opening Range High breakout strategy using gap and news scanning

    Strategy phases:
    1. Scan for gap candidates (pre-market)
    2. Scan for news candidates (pre-market)
    3. Track opening ranges (first 10 minutes)
    4. Execute breakouts when price > ORH
    5. Manage positions with stop losses at ORL
    """

    def __init__(
        self,
        ib_client: IBKRClient,
        scanner_service: IBKRGapScanner,
        market_data_service: IBKRMarketData,
        order_service: IBKROrders,
        db: Database,
        discord: DiscordNotifier,
        config: Config,
    ):
        """Initialise ORH breakout strategy

        Args:
            ib_client: IBKR API client
            scanner_service: Gap scanner service
            market_data_service: Market data service
            order_service: Order placement service
            db: Database for persistence
            discord: Discord notification service
            config: Strategy configuration
        """
        self.ib_client = ib_client
        self.db = db
        self.discord = discord
        self.config = config

        # Import here to avoid circular imports
        from skim.monitor import Monitor
        from skim.range_tracker import RangeTracker
        from skim.scanners import GapScanner, NewsScanner
        from skim.trader import Trader

        # Business logic modules
        self.gap_scanner = GapScanner(
            scanner_service=scanner_service,
            gap_threshold=config.scanner_config.gap_threshold,
        )
        self.news_scanner = NewsScanner()
        self.range_tracker = RangeTracker(
            market_data_service=market_data_service, db=self.db
        )
        self.trader = Trader(market_data_service, order_service, self.db)
        self.monitor = Monitor(market_data_service)

        logger.info("ORH Breakout Strategy initialised")

    @property
    def name(self) -> str:
        """Strategy identifier"""
        return "orh_breakout"

    async def _ensure_connection(self) -> None:
        """Ensure IB connection is active"""
        if not self.ib_client.is_connected():
            logger.info("Connecting to IBKR...")
            await self.ib_client.connect(timeout=20)

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
            deleted = self.db.purge_candidates(only_before_utc_date)
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
                    self.db.save_stock_in_play(candidate)

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
                    self.db.save_stock_in_play(candidate)

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

    async def trade(self) -> int:
        """Execute breakout entries for tradeable candidates

        Returns:
            Number of trades executed
        """
        logger.info("Executing breakouts...")
        try:
            await self._ensure_connection()
            candidates = self.db.get_tradeable_candidates()
            if not candidates:
                logger.info("No tradeable candidates found.")
                return 0

            logger.info(f"Found {len(candidates)} tradeable candidates")
            events = await self.trader.execute_breakouts(candidates)

            for event in events:
                self.discord.send_trade_notification(
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
            positions = self.db.get_open_positions()
            if not positions:
                logger.info("No open positions to manage.")
                return 0

            stops_hit = await self.monitor.check_stops(positions)
            if not stops_hit:
                logger.info("No stop losses hit.")
                return 0

            events = await self.trader.execute_stops(stops_hit)

            for event in events:
                self.discord.send_trade_notification(
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
        """Send Discord notification for tradeable candidates

        Returns:
            Number of candidates alerted
        """
        logger.info("Sending alert for tradeable candidates...")
        try:
            candidates = self.db.get_tradeable_candidates()
            count = len(candidates)

            if not candidates:
                logger.info("No tradeable candidates to alert")
                return 0

            payload = [
                {
                    "ticker": c.ticker,
                    "gap_percent": c.gap_percent,
                    "headline": c.headline,
                    "or_high": c.or_high,
                    "or_low": c.or_low,
                }
                for c in candidates
            ]

            self.discord.send_tradeable_candidates(count, payload)
            logger.info(f"Alert sent for {count} tradeable candidates")
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
            account = self.ib_client.get_account()
            logger.info(f"Health check OK. Connected account: {account}")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return False
