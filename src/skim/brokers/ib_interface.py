"""Interactive Brokers interface protocol definition"""

from dataclasses import dataclass
from typing import Protocol


@dataclass
class MarketData:
    """Market data for a security"""

    ticker: str
    last_price: float
    bid: float
    ask: float
    volume: int
    low: float


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

    def connect(
        self, host: str, port: int, client_id: int, timeout: int = 20
    ) -> None:
        """Connect to IB Gateway/Client Portal API

        Args:
            host: IB Gateway hostname or IP
            port: IB Gateway port (5000 for Client Portal API)
            client_id: Unique client ID
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

    def get_market_data(self, ticker: str) -> MarketData | None:
        """Get current market data for a ticker

        Args:
            ticker: Stock ticker symbol (e.g., "BHP")

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
