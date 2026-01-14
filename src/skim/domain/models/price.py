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
