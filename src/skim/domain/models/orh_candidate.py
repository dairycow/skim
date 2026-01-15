"""ORH-specific candidate data domain model"""

from dataclasses import dataclass, field
from datetime import datetime

_UNSET: object = object()


@dataclass
class ORHCandidateData:
    """ORH-specific candidate data"""

    gap_percent: float | None = field(default=None)
    conid: int | None = field(default=None)
    headline: str | None = field(default=None)
    announcement_type: str = field(default="pricesens")
    announcement_timestamp: datetime | None = field(default=None)
    or_high: float | None = field(default=None)
    or_low: float | None = field(default=None)
    sample_date: str | None = field(default=None)
