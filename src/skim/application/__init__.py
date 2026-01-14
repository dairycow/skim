"""Application layer for event-driven trading architecture"""

from skim.application.events import (
    DEFAULT_HANDLERS,
    Event,
    EventBus,
    EventType,
    handle_candidate_created,
    handle_gap_scan_result,
    handle_news_scan_result,
    handle_opening_range_tracked,
    handle_stop_hit,
    handle_trade_executed,
)
from skim.application.services import TradingService

__all__ = [
    "Event",
    "EventBus",
    "EventType",
    "DEFAULT_HANDLERS",
    "handle_gap_scan_result",
    "handle_news_scan_result",
    "handle_stop_hit",
    "handle_trade_executed",
    "handle_candidate_created",
    "handle_opening_range_tracked",
    "TradingService",
]
