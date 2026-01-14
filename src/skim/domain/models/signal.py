"""Signal domain model"""

from dataclasses import dataclass

from .price import Price
from .ticker import Ticker


@dataclass
class Signal:
    """Trading signal"""

    ticker: Ticker
    action: str
    quantity: int
    price: Price | None = None
    reason: str = ""
