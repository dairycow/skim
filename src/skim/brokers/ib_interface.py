"""Interactive Brokers interface protocol definition"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class MarketData:
    """Market data for a security"""

    ticker: str
    conid: str
    last_price: float
    high: float
    low: float
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    volume: int
    open: float
    prior_close: float
    change_percent: float


@dataclass
class OrderResult:
    """Result of placing an order"""

    order_id: str
    ticker: str
    action: str
    quantity: int
    filled_price: float | None = None
    status: str = "submitted"


class IBInterface(Protocol):
    """Protocol defining the Interactive Brokers client interface"""

    def connect(self, timeout: int = 20) -> None:
        """Connect to IB Gateway/Client Portal API

        Args:
            timeout: Connection timeout in seconds

        Raises:
            ValueError: If connecting to wrong account type
            RuntimeError: If connection fails after retries
        """
        ...

    def is_connected(self) -> bool:
        """Check if connected to IB

        Returns:
            True if connected, False otherwise
        """
        ...

    def place_order(
        self, ticker: str, action: str, quantity: int
    ) -> OrderResult | None:
        """Place a market order

        Args:
            ticker: Stock ticker symbol (e.g., "BHP")
            action: Order action ("BUY" or "SELL")
            quantity: Number of shares

        Returns:
            OrderResult object if order placed successfully, None otherwise
        """
        ...

    def get_market_data(self, conid: str) -> MarketData | None:
        """Get current market data for a contract

        Args:
            conid: IBKR contract ID

        Returns:
            MarketData object if data available, None otherwise
        """
        ...

    def disconnect(self) -> None:
        """Disconnect from IB"""
        ...

    def get_account(self) -> str:
        """Get the connected account ID

        Returns:
            Account ID string
        """
        ...
