"""Interactive Brokers interface protocol definition"""

from typing import Protocol

from ib_insync import Contract, Ticker, Trade


class MarketData:
    """Market data for a security"""

    def __init__(self, ticker: str, last_price: float, contract: Contract):
        self.ticker = ticker
        self.last_price = last_price
        self.contract = contract


class IBInterface(Protocol):
    """Protocol defining the Interactive Brokers client interface"""

    def connect(
        self, host: str, port: int, client_id: int, timeout: int = 20
    ) -> None:
        """Connect to IB Gateway/TWS

        Args:
            host: IB Gateway hostname or IP
            port: IB Gateway port (4001 for TWS live, 4002 for paper, 4004 for Gateway)
            client_id: Unique client ID
            timeout: Connection timeout in seconds

        Raises:
            ValueError: If connecting to wrong account type
            RuntimeError: If connection fails after retries
        """
        ...

    def is_connected(self) -> bool:
        """Check if connected to IB Gateway

        Returns:
            True if connected, False otherwise
        """
        ...

    def place_order(
        self, ticker: str, action: str, quantity: int
    ) -> Trade | None:
        """Place a market order

        Args:
            ticker: Stock ticker symbol (e.g., "BHP")
            action: Order action ("BUY" or "SELL")
            quantity: Number of shares

        Returns:
            Trade object if order placed successfully, None otherwise
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
        """Disconnect from IB Gateway"""
        ...

    def get_account(self) -> str:
        """Get the connected account ID

        Returns:
            Account ID string
        """
        ...
