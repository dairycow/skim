"""Order result domain model"""

from dataclasses import dataclass


@dataclass
class OrderResult:
    """Result of placing an order (domain model)"""

    order_id: str
    ticker: str
    action: str
    quantity: int
    filled_price: float | None = None
    status: str = "submitted"
