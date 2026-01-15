"""IBKRClientFacade - Lightweight facade for IBKR Client Portal API"""

from typing import TYPE_CHECKING

from .auth import IBKRAuthManager
from .connection import IBKRConnectionManager
from .requests import IBKRRequestClient

if TYPE_CHECKING:
    pass


class IBKRClientFacade:
    """IBKR Client Portal API connection manager (facade pattern)

    A lightweight facade that delegates to IBKRAuthManager, IBKRConnectionManager,
    and IBKRRequestClient. Provides backward-compatible interface.

    This is a connection manager. Market data, orders, and scanning are handled
    by specialized classes that use this client internally.

    Satisfies the BrokerConnectionManager protocol at the type level.
    """

    BASE_URL = "https://api.ibkr.com/v1/api"
    REALM = "limited_poa"

    def __init__(self, paper_trading: bool = True) -> None:
        """Initialize IBKR connection manager

        Args:
            paper_trading: If True, verify connected to paper account (DU prefix)

        Raises:
            ValueError: If required OAuth environment variables are missing
        """
        self._auth_manager = IBKRAuthManager()
        self._request_client = IBKRRequestClient(self._auth_manager)
        self._connection_manager = IBKRConnectionManager(
            self._auth_manager, self._request_client, paper_trading
        )

    def is_connected(self) -> bool:
        """Check if session is still valid"""
        return self._connection_manager.is_connected

    @property
    def account_id(self) -> str:
        """Get connected account ID"""
        return self._connection_manager.account_id  # type: ignore

    async def connect(self, timeout: int = 20) -> None:
        """Establish authenticated session with IBKR"""
        await self._connection_manager.connect(timeout)

    async def disconnect(self) -> None:
        """Disconnect from IBKR and cleanup resources"""
        await self._connection_manager.disconnect()

    def get_account(self) -> str:
        """Get connected account ID

        Returns:
            Account ID string (e.g., "DUN090463" for paper account)

        Raises:
            IBKRConnectionError: If not connected
        """
        return self._connection_manager.get_account()

    async def get(
        self,
        endpoint: str,
        params: dict | None = None,
    ) -> dict:
        """Make GET request

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            Response JSON as dict
        """
        return await self._request_client.request(
            "GET", endpoint, params=params
        )

    async def post(
        self,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make POST request

        Args:
            endpoint: API endpoint path
            data: JSON payload
            params: Query parameters

        Returns:
            Response JSON as dict
        """
        return await self._request_client.request(
            "POST", endpoint, data=data, params=params
        )

    @property
    def auth_manager(self) -> IBKRAuthManager:
        """Access auth manager for testing"""
        return self._auth_manager

    @property
    def request_client(self) -> IBKRRequestClient:
        """Access request client for testing"""
        return self._request_client

    @classmethod
    def install_logging_bridge(cls) -> None:
        """Bridge stdlib logging used by httpx/ibkr modules into loguru once."""
        IBKRRequestClient.install_logging_bridge()


IBKRClient = IBKRClientFacade


def install_logging_bridge() -> None:
    """Bridge stdlib logging used by httpx/ibkr modules into loguru once."""
    IBKRRequestClient.install_logging_bridge()


def is_connection_manager(obj: object) -> bool:
    """Check if object satisfies BrokerConnectionManager protocol.

    Args:
        obj: Object to check

    Returns:
        True if object has all required connection manager methods
    """
    required_methods = [
        "connect",
        "disconnect",
        "is_connected",
        "get_account",
    ]
    return all(
        hasattr(obj, method) and callable(getattr(obj, method))
        for method in required_methods
    )
