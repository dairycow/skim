"""Event handlers for the trading system.

These handlers process events published by the TradingService and other
components. Each handler is responsible for a specific event type and
performs domain actions like persisting data, sending notifications, etc.
"""

from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from .event_bus import Event, EventType

if TYPE_CHECKING:
    from skim.trading.data.database import Database
    from skim.trading.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )
    from skim.trading.notifications.discord import DiscordNotifier


HandlerFunc = Callable[[Event], Awaitable[None]]


class EventHandlers:
    """Container for event handlers with their dependencies.

    Provides a single place to configure all event handlers with their
    required services (database, notifier, repository).
    """

    def __init__(
        self,
        db: "Database",
        repository: "ORHCandidateRepository",
        notifier: "DiscordNotifier",
    ) -> None:
        """Initialise handlers with dependencies.

        Args:
            db: Database for persistence operations
            repository: Candidate repository for ORM operations
            notifier: Discord webhook for notifications
        """
        self._db = db
        self._repository = repository
        self._notifier = notifier

    async def handle_gap_scan_result(self, event: Event) -> None:
        """Handle gap scan results - persist candidates and notify.

        Args:
            event: Event containing gap scan results with 'candidates' list
        """
        logger.info("Handling gap scan result event")
        candidates = event.data.get("candidates", [])
        count = event.data.get("count", len(candidates))

        if not candidates:
            logger.info("No gap candidates to process")
            return

        for candidate_data in candidates:
            try:
                ticker = candidate_data.get("ticker")
                gap_percent = candidate_data.get("gap_percent", 0.0)
                conid = candidate_data.get("conid")

                if ticker:
                    from skim.trading.data.models import GapStockInPlay

                    candidate = GapStockInPlay(
                        ticker=ticker,
                        scan_date=event.data.get("scan_date", ""),
                        status="watching",
                        gap_percent=gap_percent,
                        conid=conid,
                    )
                    self._repository.save_gap_candidate(candidate)
                    logger.debug(
                        f"Saved gap candidate: {ticker} ({gap_percent:.1f}%)"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to save gap candidate: {e}", exc_info=True
                )

        logger.info(f"Processed {count} gap candidates")
        self._send_scan_summary("Gap Scan", count, candidates)

    async def handle_news_scan_result(self, event: Event) -> None:
        """Handle news scan results - persist candidates and notify.

        Args:
            event: Event containing news scan results with 'candidates' list
        """
        logger.info("Handling news scan result event")
        candidates = event.data.get("candidates", [])
        count = event.data.get("count", len(candidates))

        if not candidates:
            logger.info("No news candidates to process")
            return

        for candidate_data in candidates:
            try:
                ticker = candidate_data.get("ticker")
                headline = candidate_data.get("headline", "")
                announcement_type = candidate_data.get(
                    "announcement_type", "pricesens"
                )

                if ticker:
                    from skim.trading.data.models import NewsStockInPlay

                    candidate = NewsStockInPlay(
                        ticker=ticker,
                        scan_date=event.data.get("scan_date", ""),
                        status="watching",
                        headline=headline,
                        announcement_type=announcement_type,
                    )
                    self._repository.save_news_candidate(candidate)
                    logger.debug(f"Saved news candidate: {ticker}")
            except Exception as e:
                logger.error(
                    f"Failed to save news candidate: {e}", exc_info=True
                )

        logger.info(f"Processed {count} news candidates")
        self._send_scan_summary("News Scan", count, candidates)

    async def handle_opening_range_tracked(self, event: Event) -> None:
        """Handle opening range tracking completion.

        Args:
            event: Event containing opening range data with 'ranges' list
        """
        logger.info("Handling opening range tracked event")
        ranges = event.data.get("ranges", [])

        if not ranges:
            logger.info("No opening ranges to process")
            return

        for range_data in ranges:
            try:
                ticker = range_data.get("ticker")
                or_high = range_data.get("or_high")
                or_low = range_data.get("or_low")

                if ticker and or_high is not None and or_low is not None:
                    self._repository.save_opening_range(ticker, or_high, or_low)
                    logger.debug(
                        f"Saved opening range for {ticker}: ORH={or_high}, ORL={or_low}"
                    )
            except Exception as e:
                logger.error(
                    f"Failed to save opening range: {e}", exc_info=True
                )

        logger.info(f"Processed {len(ranges)} opening ranges")

    async def handle_stop_hit(self, event: Event) -> None:
        """Handle stop loss triggers - close positions and notify.

        Args:
            event: Event containing stop hit information with 'position'
        """
        logger.info("Handling stop hit event")
        position_data = event.data.get("position")

        if not position_data:
            logger.warning("Stop hit event with no position data")
            return

        ticker = position_data.get("ticker", "UNKNOWN")
        exit_price = position_data.get("exit_price", 0.0)
        exit_date = datetime.now().isoformat()

        try:
            positions = self._db.get_open_positions()
            for pos in positions:
                if pos.ticker == ticker and pos.is_open and pos.id is not None:
                    self._db.close_position(pos.id, exit_price, exit_date)
                    logger.info(
                        f"Closed position for {ticker} at ${exit_price:.2f}"
                    )

                    self._notifier.send_trade_notification(
                        action="SELL",
                        ticker=ticker,
                        quantity=pos.quantity,
                        price=exit_price,
                        pnl=position_data.get("pnl"),
                    )
                    break
        except Exception as e:
            logger.error(f"Failed to process stop hit: {e}", exc_info=True)

    async def handle_trade_executed(self, event: Event) -> None:
        """Handle trade execution confirmation - persist and notify.

        Args:
            event: Event containing trade execution details with 'trade' and 'signal'
        """
        logger.info("Handling trade executed event")
        trade = event.data.get("trade")

        if not trade:
            logger.warning("Trade executed event with no trade data")
            return

        ticker = trade.get("ticker", "UNKNOWN")
        action = trade.get("action", "BUY")
        quantity = trade.get("quantity", 0)
        filled_price = trade.get("filled_price", trade.get("price", 0.0))

        if filled_price is None:
            filled_price = 0.0

        try:
            entry_date = datetime.now().isoformat()
            position_id = self._db.create_position(
                ticker=ticker,
                quantity=quantity,
                entry_price=filled_price,
                stop_loss=filled_price * 0.95,
                entry_date=entry_date,
            )
            logger.info(
                f"Saved position {position_id}: {ticker} x {quantity} @ ${filled_price:.2f}"
            )

            self._notifier.send_trade_notification(
                action=action,
                ticker=ticker,
                quantity=quantity,
                price=filled_price,
            )
        except Exception as e:
            logger.error(
                f"Failed to process trade execution: {e}", exc_info=True
            )

    async def handle_candidate_created(self, event: Event) -> None:
        """Handle new candidate creation.

        Args:
            event: Event containing new candidate information with 'candidate'
        """
        logger.info("Handling candidate created event")
        candidate = event.data.get("candidate")

        if candidate:
            ticker = getattr(candidate, "ticker", "UNKNOWN")
            logger.info(f"New candidate created: {ticker}")

    def _send_scan_summary(
        self, scan_type: str, count: int, candidates: list[dict]
    ) -> None:
        """Send scan result summary to Discord.

        Args:
            scan_type: Type of scan (Gap, News, etc.)
            count: Number of candidates found
            candidates: List of candidate data dictionaries
        """
        try:
            self._notifier.send_tradeable_candidates(count, candidates)
        except Exception as e:
            logger.error(f"Failed to send {scan_type} scan notification: {e}")


def create_handler_factory(
    db: "Database",
    repository: "ORHCandidateRepository",
    notifier: "DiscordNotifier",
) -> EventHandlers:
    """Create an EventHandlers instance with dependencies.

    This is the recommended way to create handlers that need access
    to database, repository, and notification services.

    Args:
        db: Database instance
        repository: Candidate repository
        notifier: Discord notifier

    Returns:
        EventHandlers instance with all handlers configured
    """
    return EventHandlers(db, repository, notifier)


def get_default_handlers(
    handlers: EventHandlers,
) -> dict[EventType, HandlerFunc]:
    """Get default handler mapping with handlers bound to their dependencies.

    Args:
        handlers: EventHandlers instance with configured dependencies

    Returns:
        Dictionary mapping event types to handler functions
    """
    return {
        EventType.GAP_SCAN_RESULT: handlers.handle_gap_scan_result,
        EventType.NEWS_SCAN_RESULT: handlers.handle_news_scan_result,
        EventType.STOP_HIT: handlers.handle_stop_hit,
        EventType.TRADE_EXECUTED: handlers.handle_trade_executed,
        EventType.CANDIDATE_CREATED: handlers.handle_candidate_created,
        EventType.OPENING_RANGE_TRACKED: handlers.handle_opening_range_tracked,
    }


async def handle_gap_scan_result(event: Event) -> None:
    """Handle gap scan results (standalone fallback).

    Args:
        event: Event containing gap scan results
    """
    logger.info("Handling gap scan result event (standalone)")
    candidates = event.data.get("candidates", [])
    logger.info(f"Received {len(candidates)} gap candidates from scan")


async def handle_news_scan_result(event: Event) -> None:
    """Handle news scan results (standalone fallback).

    Args:
        event: Event containing news scan results
    """
    logger.info("Handling news scan result event (standalone)")
    candidates = event.data.get("candidates", [])
    logger.info(f"Received {len(candidates)} news candidates from scan")


async def handle_stop_hit(event: Event) -> None:
    """Handle stop loss triggers (standalone fallback).

    Args:
        event: Event containing stop hit information
    """
    logger.info("Handling stop hit event (standalone)")
    position = event.data.get("position")
    if position:
        logger.info(f"Stop hit for position: {position}")


async def handle_trade_executed(event: Event) -> None:
    """Handle trade execution confirmation (standalone fallback).

    Args:
        event: Event containing trade execution details
    """
    logger.info("Handling trade executed event (standalone)")
    trade = event.data.get("trade")
    if trade:
        logger.info(f"Trade executed: {trade}")


async def handle_candidate_created(event: Event) -> None:
    """Handle new candidate creation (standalone fallback).

    Args:
        event: Event containing new candidate information
    """
    logger.info("Handling candidate created event (standalone)")
    candidate = event.data.get("candidate")
    if candidate:
        ticker = getattr(candidate, "ticker", "UNKNOWN")
        logger.info(f"New candidate created: {ticker}")


async def handle_opening_range_tracked(event: Event) -> None:
    """Handle opening range tracking completion (standalone fallback).

    Args:
        event: Event containing opening range data
    """
    logger.info("Handling opening range tracked event (standalone)")
    ranges = event.data.get("ranges", [])
    logger.info(f"Opening ranges tracked for {len(ranges)} candidates")


DEFAULT_HANDLERS = {
    EventType.GAP_SCAN_RESULT: handle_gap_scan_result,
    EventType.NEWS_SCAN_RESULT: handle_news_scan_result,
    EventType.STOP_HIT: handle_stop_hit,
    EventType.TRADE_EXECUTED: handle_trade_executed,
    EventType.CANDIDATE_CREATED: handle_candidate_created,
    EventType.OPENING_RANGE_TRACKED: handle_opening_range_tracked,
}
