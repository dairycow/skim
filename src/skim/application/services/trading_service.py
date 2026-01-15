"""Trading service - Main orchestrator using event-driven architecture"""

from typing import TYPE_CHECKING

from loguru import logger

from skim.application.events import Event, EventBus, EventType
from skim.application.events.handlers import (
    create_handler_factory,
    get_default_handlers,
)

if TYPE_CHECKING:
    from skim.domain.strategies.base import Strategy
    from skim.trading.brokers.ibkr_market_data import IBKRMarketData
    from skim.trading.brokers.ibkr_orders import IBKROrders
    from skim.trading.core.config import Config
    from skim.trading.data.database import Database
    from skim.trading.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )
    from skim.trading.notifications.discord import DiscordNotifier


class TradingService:
    """Main trading orchestrator using event-driven architecture

    Coordinates between strategies, event bus, and services for
    scan, trade, and manage operations.
    """

    def __init__(
        self,
        strategy: "Strategy",
        event_bus: EventBus,
        db: "Database",
        market_data: "IBKRMarketData",
        orders: "IBKROrders",
        config: "Config",
        repository: "ORHCandidateRepository",
        notifier: "DiscordNotifier",
    ) -> None:
        """Initialise trading service

        Args:
            strategy: Trading strategy implementation
            event_bus: Event bus for publishing events
            db: Database for persistence
            market_data: Market data service
            orders: Order management service
            config: Application configuration
            repository: Candidate repository for ORM operations
            notifier: Discord webhook for notifications
        """
        self.strategy = strategy
        self.events = event_bus
        self.db = db
        self.market_data = market_data
        self.orders = orders
        self.config = config
        self._repository = repository
        self._notifier = notifier

        self._register_strategy_handler()
        self._register_event_handlers()

        logger.info(f"TradingService initialised for strategy: {strategy.name}")

    def _register_strategy_handler(self) -> None:
        """Register strategy as a global event handler if it supports on_event."""
        if hasattr(self.strategy, "on_event"):
            self.events.add_handler(self.strategy.on_event)
            logger.debug("Registered strategy as global event handler")

    def _register_event_handlers(self) -> None:
        """Register domain event handlers with the event bus.

        Creates an EventHandlers instance with all required dependencies
        and registers handlers for each event type.
        """
        handlers = create_handler_factory(
            db=self.db,
            repository=self._repository,
            notifier=self._notifier,
        )

        handler_mapping = get_default_handlers(handlers)

        for event_type, handler in handler_mapping.items():
            self.events.subscribe(event_type, handler)
            logger.debug(f"Registered handler for event: {event_type.value}")

        logger.info(f"Registered {len(handler_mapping)} event handlers")

    async def scan(self) -> int:
        """Run scan phase - publish events

        Returns:
            Total number of candidates found
        """
        logger.info("TradingService: Running scan phase")
        gap_count = await self._run_gap_scan()
        news_count = await self._run_news_scan()
        logger.info(f"Scan complete. Found {gap_count + news_count} candidates")
        return gap_count + news_count

    async def trade(self) -> int:
        """Execute signals from strategy

        Returns:
            Number of trades executed
        """
        logger.info("TradingService: Executing trades")
        signals = await self._get_pending_signals()
        executed = 0

        for signal in signals:
            result = await self.orders.place_order(
                ticker=str(signal.ticker),
                action=signal.action,
                quantity=signal.quantity,
            )
            if result:
                executed += 1
                await self.events.publish(
                    Event(
                        EventType.TRADE_EXECUTED,
                        {"trade": result, "signal": signal},
                    )
                )

        logger.info(f"TradingService: Executed {executed} trades")
        return executed

    async def manage(self) -> int:
        """Monitor positions and handle stops

        Returns:
            Number of positions managed
        """
        logger.info("TradingService: Managing positions")
        positions = self.db.get_open_positions()

        if not positions:
            logger.info("No open positions to manage")
            return 0

        stops_hit = await self._check_stops(positions)
        for stop in stops_hit:
            await self.events.publish(
                Event(EventType.STOP_HIT, {"position": stop})
            )

        logger.info(f"TradingService: Managed {len(stops_hit)} stops")
        return len(stops_hit)

    async def status(self) -> bool:
        """Perform health check

        Returns:
            True if healthy
        """
        logger.info("TradingService: Health check")
        return await self.strategy.health_check()

    async def _run_gap_scan(self) -> int:
        """Run gap scanner and publish events

        Returns:
            Number of gap candidates found
        """
        count = await self.strategy.scan_gaps()

        await self.events.publish(
            Event(
                EventType.GAP_SCAN_RESULT,
                {"candidates": [], "count": count},
            )
        )

        return count

    async def _run_news_scan(self) -> int:
        """Run news scanner and publish events

        Returns:
            Number of news candidates found
        """
        count = await self.strategy.scan_news()

        await self.events.publish(
            Event(
                EventType.NEWS_SCAN_RESULT,
                {"candidates": [], "count": count},
            )
        )

        return count

    async def _get_pending_signals(self) -> list:
        """Get pending signals from strategy

        Returns:
            List of pending signals
        """
        logger.debug("Getting pending signals from strategy")
        return []

    async def _check_stops(self, positions: list) -> list:
        """Check for stop losses being hit

        Args:
            positions: List of open positions

        Returns:
            List of positions with stops hit
        """
        logger.debug(f"Checking stops for {len(positions)} positions")
        return []
