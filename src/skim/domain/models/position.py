"""Position domain model"""

from dataclasses import dataclass, field
from datetime import datetime

from .price import Price
from .ticker import Ticker


@dataclass
class Position:
    """Trading position (domain model)"""

    ticker: Ticker
    quantity: int
    entry_price: Price
    stop_loss: Price
    entry_date: datetime
    id: int | None = None
    exit_price: Price | None = None
    exit_date: datetime | None = None
    status: str = field(default="open")

    @property
    def is_open(self) -> bool:
        return self.status == "open"

    @property
    def pnl(self) -> float | None:
        if not self.exit_price:
            return None
        return (self.exit_price.value - self.entry_price.value) * self.quantity
