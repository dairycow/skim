"""Event domain model"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventType(Enum):
    MARKET_DATA = "market_data"
    GAP_SCAN_RESULT = "gap_scan"
    NEWS_SCAN_RESULT = "news_scan"
    OPENING_RANGE_TRACKED = "or_tracked"
    STOP_HIT = "stop_hit"


@dataclass
class Event:
    """Domain event"""

    type: EventType
    data: dict | object
    timestamp: datetime = datetime.now()
