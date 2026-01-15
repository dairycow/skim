"""Event domain model"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class EventType(Enum):
    """Event types for the trading system

    Domain Events:
        - MARKET_DATA: Market data updates
        - GAP_SCAN_RESULT: Gap scan completed
        - NEWS_SCAN_RESULT: News scan completed
        - OPENING_RANGE_TRACKED: Opening range data collected
        - STOP_HIT: Stop loss triggered
        - SIGNAL_EMITTED: Trading signal generated
        - TRADE_EXECUTED: Trade order filled
        - CANDIDATE_CREATED: New candidate identified

    Strategy Events (for event-driven strategies):
        - SCAN: Scan phase triggered
        - TRADE: Trade phase triggered
        - MANAGE: Manage phase triggered
        - ALERT: Alert phase triggered
        - TRACK_RANGES: Track ranges phase triggered
        - HEALTH_CHECK: Health check triggered
        - SETUP: Setup phase triggered
        - CUSTOM: Custom event type
    """

    MARKET_DATA = "market_data"
    GAP_SCAN_RESULT = "gap_scan"
    NEWS_SCAN_RESULT = "news_scan"
    OPENING_RANGE_TRACKED = "or_tracked"
    STOP_HIT = "stop_hit"
    SIGNAL_EMITTED = "signal"
    TRADE_EXECUTED = "trade_executed"
    CANDIDATE_CREATED = "candidate_created"

    SCAN = "scan"
    TRADE = "trade"
    MANAGE = "manage"
    ALERT = "alert"
    TRACK_RANGES = "track_ranges"
    HEALTH_CHECK = "health_check"
    SETUP = "setup"
    CUSTOM = "custom"


@dataclass
class Event:
    """Domain event

    Attributes:
        type: Type of event
        data: Event-specific data payload
        timestamp: When the event was created
    """

    type: EventType
    data: dict[str, Any] | None = None
    timestamp: datetime | None = None

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now()

    def __repr__(self) -> str:
        ts = self.timestamp.isoformat() if self.timestamp else "none"
        return f"Event(type={self.type.value}, timestamp={ts})"


@dataclass
class EventSignal:
    """Lightweight signal for event bus communication

    Used by strategies to emit signals through the event bus.
    Can be converted to domain Signal by event handlers.

    Attributes:
        ticker: Target ticker symbol
        action: Recommended action (BUY, SELL, etc.)
        price: Target price
        quantity: Position quantity
        metadata: Additional signal data
    """

    ticker: str
    action: str
    price: float | None = None
    quantity: int | None = None
    metadata: dict[str, Any] | None = None

    def __repr__(self) -> str:
        return f"EventSignal(ticker={self.ticker}, action={self.action}, price={self.price})"
