"""Broker protocols defining interfaces for broker integrations.

These protocols enable broker swapping by defining abstract interfaces
that concrete implementations must satisfy.
"""

from typing import Protocol, runtime_checkable

from skim.trading.data.models import MarketData, OrderResult, Position
from skim.trading.validation.scanners import GapStock


@runtime_checkable
class BrokerConnectionManager(Protocol):
    """Protocol for broker connection lifecycle management."""

    async def connect(self, timeout: int = 20) -> None:
        """Establish an authenticated session with the broker."""
        ...

    async def disconnect(self) -> None:
        """Disconnect from the broker and clean up resources."""
        ...

    def is_connected(self) -> bool:
        """Check if the session is still valid."""
        ...

    def get_account(self) -> str:
        """Get the connected account ID."""
        ...


@runtime_checkable
class MarketDataProvider(Protocol):
    """Protocol for market data retrieval."""

    async def get_market_data(
        self,
        tickers: str | list[str],
    ) -> MarketData | dict[str, MarketData | None] | None:
        """Get market data for one or more tickers."""
        ...

    async def get_contract_id(self, ticker: str) -> str:
        """Look up the contract ID for a given ticker."""
        ...

    def clear_cache(self) -> None:
        """Clear any internal caches."""
        ...


@runtime_checkable
class OrderManager(Protocol):
    """Protocol for order management operations."""

    async def place_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str = "MKT",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult | None:
        """Place an order."""
        ...

    async def get_open_orders(self) -> list[dict]:
        """Query all open orders."""
        ...

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel a specific order."""
        ...

    async def get_positions(self) -> list[Position]:
        """Get all current positions."""
        ...

    async def get_account_balance(self) -> dict:
        """Get the account balance summary."""
        ...


@runtime_checkable
class GapScannerService(Protocol):
    """Protocol for market scanner services."""

    async def run_scanner(self, scan_params: dict) -> list[dict]:
        """Run a market scanner with specified parameters."""
        ...

    async def scan_for_gaps(self, min_gap: float) -> list[GapStock]:
        """Scan for stocks with gaps."""
        ...

    async def get_scanner_params(self) -> dict:
        """Get available scanner parameters."""
        ...
