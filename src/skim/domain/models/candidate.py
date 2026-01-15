"""Candidate domain model"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .orh_candidate import ORHCandidateData
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
    orh_data: ORHCandidateData | None = field(default=None)


@dataclass
class GapCandidate(Candidate):
    """Gap scanner candidate"""

    STRATEGY_NAME: str = "orh_breakout"
    gap_percent: float = field(default=_UNSET)
    conid: int | None = field(default=None)

    def __post_init__(self):
        if self.strategy_name == "":
            self.strategy_name = self.STRATEGY_NAME
        if self.gap_percent is _UNSET:
            raise ValueError("gap_percent is required")
        if self.orh_data is None:
            self.orh_data = ORHCandidateData(
                gap_percent=self.gap_percent, conid=self.conid
            )
        else:
            self.orh_data.gap_percent = self.gap_percent
            self.orh_data.conid = self.conid


@dataclass
class NewsCandidate(Candidate):
    """News scanner candidate"""

    STRATEGY_NAME: str = "orh_breakout"
    headline: str = field(default=_UNSET)
    announcement_type: str = field(default="pricesens")
    announcement_timestamp: datetime | None = field(default=None)

    def __post_init__(self):
        if self.strategy_name == "":
            self.strategy_name = self.STRATEGY_NAME
        if self.headline is _UNSET:
            raise ValueError("headline is required")
        if self.orh_data is None:
            self.orh_data = ORHCandidateData(
                headline=self.headline,
                announcement_type=self.announcement_type,
                announcement_timestamp=self.announcement_timestamp,
            )
        else:
            self.orh_data.headline = self.headline
            self.orh_data.announcement_type = self.announcement_type
            self.orh_data.announcement_timestamp = self.announcement_timestamp
