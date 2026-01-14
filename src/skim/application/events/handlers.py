"""Event handlers for the trading system"""

from typing import TYPE_CHECKING

from loguru import logger

from .event_bus import Event, EventType

if TYPE_CHECKING:
    pass


async def handle_gap_scan_result(event: Event) -> None:
    """Handle gap scan results

    Args:
        event: Event containing gap scan results
    """
    logger.info("Handling gap scan result event")
    candidates = event.data.get("candidates", [])
    logger.info(f"Received {len(candidates)} gap candidates from scan")


async def handle_news_scan_result(event: Event) -> None:
    """Handle news scan results

    Args:
        event: Event containing news scan results
    """
    logger.info("Handling news scan result event")
    candidates = event.data.get("candidates", [])
    logger.info(f"Received {len(candidates)} news candidates from scan")


async def handle_stop_hit(event: Event) -> None:
    """Handle stop loss triggers

    Args:
        event: Event containing stop hit information
    """
    logger.info("Handling stop hit event")
    position = event.data.get("position")
    if position:
        logger.info(f"Stop hit for position: {position}")


async def handle_trade_executed(event: Event) -> None:
    """Handle trade execution confirmation

    Args:
        event: Event containing trade execution details
    """
    logger.info("Handling trade executed event")
    trade = event.data.get("trade")
    if trade:
        logger.info(f"Trade executed: {trade}")


async def handle_candidate_created(event: Event) -> None:
    """Handle new candidate creation

    Args:
        event: Event containing new candidate information
    """
    logger.info("Handling candidate created event")
    candidate = event.data.get("candidate")
    if candidate:
        logger.info(f"New candidate created: {candidate.ticker}")


async def handle_opening_range_tracked(event: Event) -> None:
    """Handle opening range tracking completion

    Args:
        event: Event containing opening range data
    """
    logger.info("Handling opening range tracked event")
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
