"""Price value object"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Price:
    """Value object for price data"""

    value: float
    timestamp: datetime

    @property
    def is_valid(self) -> bool:
        return self.value > 0

    @classmethod
    def from_persistence(cls, value: float) -> "Price":
        return cls(value=value, timestamp=datetime.now())

    def to_persistence(self) -> float:
        return self.value
