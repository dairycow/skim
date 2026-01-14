"""Event handling module for event-driven architecture"""

from .event_bus import Event, EventBus, EventType
from .handlers import (
    DEFAULT_HANDLERS,
    handle_candidate_created,
    handle_gap_scan_result,
    handle_news_scan_result,
    handle_opening_range_tracked,
    handle_stop_hit,
    handle_trade_executed,
)

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
]
