"""Candidate domain model"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .ticker import Ticker

_UNSET: Any = object()


@dataclass
class Candidate:
    """Trading candidate (domain model)"""

    ticker: Ticker
    scan_date: datetime
    status: str = field(default="watching")
    strategy_name: str = field(default="")
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class GapCandidate(Candidate):
    """Gap scanner candidate"""

    gap_percent: float = field(default=_UNSET)
    conid: int | None = field(default=None)

    def __post_init__(self):
        if self.gap_percent is _UNSET:
            raise ValueError("gap_percent is required")


@dataclass
class NewsCandidate(Candidate):
    """News scanner candidate"""

    headline: str = field(default=_UNSET)
    announcement_type: str = field(default="pricesens")
    announcement_timestamp: datetime | None = field(default=None)

    def __post_init__(self):
        if self.headline is _UNSET:
            raise ValueError("headline is required")
