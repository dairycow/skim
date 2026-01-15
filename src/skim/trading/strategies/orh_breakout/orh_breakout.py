"""ORH Breakout Strategy - Event-driven architecture"""

from datetime import date
from typing import cast

from loguru import logger

from skim.application.notifications import NotificationHandler
from skim.application.persistence import StrategyPersistenceHandler
from skim.domain.models.event import EventType
from skim.domain.strategies.base import Strategy
from skim.domain.strategies.context import StrategyContext
from skim.domain.strategies.registry import register_strategy
from skim.infrastructure.database.historical import PerformanceFilter
from skim.trading.alerts import CandidateAlerter
from skim.trading.core.config import Config
from skim.trading.data.database import Database
from skim.trading.data.repositories.orh_repository import ORHCandidateRepository
from skim.trading.filters import FilterChain, HistoricalPerformanceFilter
from skim.trading.monitor import Monitor
from skim.trading.scanners import GapScanner, NewsScanner, ScannerOrchestrator
from skim.trading.strategies.orh_breakout.range_tracker import RangeTracker
from skim.trading.strategies.orh_breakout.trader import Trader


@register_strategy("orh_breakout")
class ORHBreakoutStrategy(Strategy):
    """Opening Range High breakout strategy using event-driven architecture

    Strategy phases:
        1. Scan for gap and news candidates (via ScannerOrchestrator)
        2. Track opening ranges (via RangeTracker)
        3. Execute breakouts when price > ORH (via Trader)
        4. Manage positions with stop losses (via Trader + Monitor)
    """

    db: Database
    repo: ORHCandidateRepository

    def __init__(self, context: StrategyContext):
        """Initialise ORH breakout strategy

        Args:
            context: Strategy context with all dependencies
        """
        self.ctx = context

        self.event_bus = context.event_bus

        self.db = cast(Database, context.database)
        self.repo = cast(ORHCandidateRepository, context.repository)
        config = cast(Config, context.config)

        self.scanner_orchestrator = ScannerOrchestrator(
            self.event_bus, self.repo
        )
        self.scanner_orchestrator.register_scanner(
            GapScanner(
                scanner_service=context.scanner_service,
                gap_threshold=config.scanner_config.gap_threshold,
            )
        )
        self.scanner_orchestrator.register_scanner(NewsScanner())

        self.range_tracker = RangeTracker(
            market_data_service=context.market_data,
            orh_repo=self.repo,
        )

        self.trader = Trader(
            market_data_provider=context.market_data,
            order_manager=context.order_service,
            event_bus=self.event_bus,
        )

        self.monitor = Monitor(context.market_data)

        self.alerter = CandidateAlerter(
            repository=self.repo,  # type: ignore[assignment]
            event_bus=self.event_bus,
        )

        hist_config = config.historical_config
        historical_filter = HistoricalPerformanceFilter(
            context.historical_service
        )
        historical_filter.configure(
            enable_filtering=hist_config.enable_filtering,
            filter_criteria=PerformanceFilter(
                min_3month_return=hist_config.min_3month_return,
                max_3month_return=hist_config.max_3month_return,
                min_6month_return=hist_config.min_6month_return,
                min_avg_volume=hist_config.min_avg_volume,
                require_3month_data=hist_config.require_data,
                require_6month_data=False,
            ),
        )
        self.filter_chain = FilterChain([historical_filter])

        self.notification_handler = NotificationHandler(context.notifier)

        self.persistence_handler = StrategyPersistenceHandler(
            self.db, self.repo
        )

        self._setup_event_handlers()

        logger.info("ORH Breakout Strategy initialised (event-driven)")

    def _setup_event_handlers(self) -> None:
        """Subscribe to relevant events"""
        self.event_bus.subscribe(
            EventType.TRADE_EXECUTED,
            self.notification_handler.handle_trade_executed,
        )
        self.event_bus.subscribe(
            EventType.STOP_HIT,
            self.notification_handler.handle_stop_hit,
        )
        self.event_bus.subscribe(
            EventType.CANDIDATES_ALERTED,
            self.notification_handler.handle_candidates_alerted,
        )
        self.event_bus.subscribe(
            EventType.CANDIDATES_SCANNED,
            self.persistence_handler.handle_candidates_scanned,
        )
        self.event_bus.subscribe(
            EventType.TRADE_EXECUTED,
            self.persistence_handler.handle_trade_executed,
        )
        self.event_bus.subscribe(
            EventType.STOP_HIT,
            self.persistence_handler.handle_stop_hit,
        )

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
            deleted = self.db.purge_candidates(
                only_before_utc_date,
                strategy_name=self.repo.STRATEGY_NAME,
            )
            logger.info(f"Deleted {deleted} candidate rows")
            return deleted
        except Exception as e:
            logger.error(f"Candidate purge failed: {e}", exc_info=True)
            return 0

    async def scan(self) -> int:
        """Full scan phase - gaps and news

        Returns:
            Total number of candidates found
        """
        logger.info("Running full scan...")
        try:
            await self._ensure_connection()
            results = await self.scanner_orchestrator.run_all()
            return sum(results.values())
        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            return 0

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
            candidates = self.repo.get_tradeable_candidates()
            if not candidates:
                logger.info("No tradeable candidates found.")
                return 0

            logger.info(f"Found {len(candidates)} tradeable candidates")

            filtered = self.filter_chain.apply(candidates)

            if not filtered:
                logger.info("No candidates passed filters")
                return 0

            logger.info(f"Trading {len(filtered)} candidates")
            events = await self.trader.execute_breakouts(filtered)

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

            return len(events)
        except Exception as e:
            logger.error(f"Position management failed: {e}", exc_info=True)
            return 0

    async def alert(self) -> int:
        """Send Discord notification for alertable candidates

        Returns:
            Number of candidates alerted
        """
        return await self.alerter.send_alerts()

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
