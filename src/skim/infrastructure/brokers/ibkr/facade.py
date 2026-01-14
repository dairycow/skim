"""IBKRClientFacade - Lightweight facade replacing monolithic IBKRClient"""

from typing import TYPE_CHECKING

import httpx

from .auth import IBKRAuthManager
from .connection import IBKRConnectionManager
from .exceptions import IBKRClientError
from .requests import IBKRRequestClient

if TYPE_CHECKING:
    pass


class IBKRClientFacade:
    """IBKR Client Portal API connection manager (facade pattern)

    A lightweight facade that delegates to IBKRAuthManager, IBKRConnectionManager,
    and IBKRRequestClient. Provides backward-compatible interface with the original
    IBKRClient.

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

    def __setattr__(self, name: str, value: object) -> None:
        if name.startswith("_") and not hasattr(self, "_auth_manager"):
            self.__dict__[name] = value
        else:
            super().__setattr__(name, value)

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

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make authenticated HTTP request (internal method)

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path
            data: JSON payload for POST requests
            params: Query parameters

        Returns:
            Response JSON as dict
        """
        http_client = self.__dict__.get("_http_client")
        if http_client is None:
            if (
                not hasattr(self, "_request_client")
                or self._request_client is None
            ):
                raise IBKRClientError("HTTP client not initialized")
            return await self._request_client.request(
                method, endpoint, data=data, params=params
            )

        if hasattr(self, "_generate_lst") and callable(self._generate_lst):

            def patched_generate_lst(realm: str = "limited_poa") -> None:
                self._generate_lst()  # type: ignore

            use_patched_generate_lst = True
        else:
            use_patched_generate_lst = False

        lst = self.__dict__.get("_lst")
        lst_expiration = self.__dict__.get("_lst_expiration")
        consumer_key = self.__dict__.get("_consumer_key", "")
        access_token = self.__dict__.get("_access_token", "")
        access_token_secret = self.__dict__.get("_access_token_secret", "")
        dh_prime_hex = self.__dict__.get("_dh_prime_hex", "")
        signature_key_path = self.__dict__.get("_signature_key_path", "")
        encryption_key_path = self.__dict__.get("_encryption_key_path", "")

        from .requests import IBKRRequestClient

        auth_manager = IBKRAuthManager.__new__(IBKRAuthManager)
        auth_manager._lst = lst
        auth_manager._lst_expiration = lst_expiration
        auth_manager._consumer_key = consumer_key
        auth_manager._access_token = access_token
        auth_manager._access_token_secret = access_token_secret
        auth_manager._dh_prime_hex = dh_prime_hex
        auth_manager._signature_key_path = signature_key_path
        auth_manager._encryption_key_path = encryption_key_path

        if use_patched_generate_lst:
            auth_manager.generate_lst = patched_generate_lst  # type: ignore

        request_client = IBKRRequestClient(auth_manager)
        request_client._http_client = http_client
        return await request_client.request(
            method, endpoint, data=data, params=params
        )

    def set_http_client(self, client: httpx.AsyncClient) -> None:
        """Set the HTTP client for requests

        Args:
            client: httpx AsyncClient instance
        """
        if not hasattr(self, "_request_client") or self._request_client is None:
            self.__dict__["_http_client"] = client
        else:
            self._request_client.set_http_client(client)

    def _build_http_client(
        self,
        timeout: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> httpx.AsyncClient:
        """Create an AsyncClient with httpx request/response logging hooks."""
        IBKRClientFacade.install_logging_bridge()
        return httpx.AsyncClient(
            timeout=timeout,
            transport=transport,
            event_hooks={
                "request": [self._log_httpx_request],
                "response": [self._log_httpx_response],
            },
        )

    async def _log_httpx_request(self, request: httpx.Request) -> None:
        """Log outbound httpx requests with headers (auth masked)."""
        from loguru import logger

        headers = {
            k: ("***" if k.lower() == "authorization" else v)
            for k, v in request.headers.items()
        }
        logger.debug(f"HTTPX request: {request.method} {request.url} {headers}")

    async def _log_httpx_response(self, response: httpx.Response) -> None:
        """Log httpx responses including status and body."""
        from loguru import logger

        try:
            body = response.text
        except Exception:
            body = "<unreadable body>"
        logger.debug(
            f"HTTPX response: status={response.status_code} url={response.url} body={body}"
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

    def _parse_account_id(self, response: object) -> str | None:
        """Parse account ID from various IBKR response formats"""
        if isinstance(response, dict):
            if "accounts" in response:
                accounts = response["accounts"]
                if accounts and len(accounts) > 0:
                    return accounts[0]
            elif "accountId" in response:
                return response["accountId"]
            else:
                return (
                    response.get("id")
                    or response.get("accountId")
                    or response.get("account")
                )
        elif isinstance(response, list) and len(response) > 0:
            first_item = response[0]
            if isinstance(first_item, str):
                return first_item
            elif isinstance(first_item, dict):
                return first_item.get("accountId") or first_item.get("id")
        return None

    def _generate_lst(self) -> None:
        """Generate new Live Session Token via OAuth flow"""
        self._auth_manager.generate_lst()

    @property
    def _lst(self) -> str | None:
        """Get current LST (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_lst")
        return self._auth_manager.lst

    @_lst.setter
    def _lst(self, value: str) -> None:
        """Set current LST (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_lst"] = value
        else:
            self._auth_manager.lst = value

    @property
    def _lst_expiration(self) -> int | None:
        """Get LST expiration timestamp (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_lst_expiration")
        return self._auth_manager.lst_expiration

    @_lst_expiration.setter
    def _lst_expiration(self, value: int) -> None:
        """Set LST expiration timestamp (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_lst_expiration"] = value
        else:
            self._auth_manager.lst_expiration = value

    @property
    def _consumer_key(self) -> str:
        """Get OAuth consumer key (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_consumer_key", "")
        return self._auth_manager.consumer_key

    @_consumer_key.setter
    def _consumer_key(self, value: str) -> None:
        """Set OAuth consumer key (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_consumer_key"] = value
        else:
            pass

    @property
    def _access_token(self) -> str:
        """Get OAuth access token (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_access_token", "")
        return self._auth_manager.access_token

    @_access_token.setter
    def _access_token(self, value: str) -> None:
        """Set OAuth access token (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_access_token"] = value

    @property
    def _access_token_secret(self) -> str:
        """Get OAuth access token secret (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_access_token_secret", "")
        return self._auth_manager.access_token_secret

    @_access_token_secret.setter
    def _access_token_secret(self, value: str) -> None:
        """Set OAuth access token secret (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_access_token_secret"] = value

    @property
    def _dh_prime_hex(self) -> str:
        """Get OAuth DH prime hex (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_dh_prime_hex", "")
        return self._auth_manager.dh_prime_hex

    @_dh_prime_hex.setter
    def _dh_prime_hex(self, value: str) -> None:
        """Set OAuth DH prime hex (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_dh_prime_hex"] = value

    @property
    def _signature_key_path(self) -> str:
        """Get OAuth signature key path (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_signature_key_path", "")
        return self._auth_manager.signature_key_path

    @_signature_key_path.setter
    def _signature_key_path(self, value: str) -> None:
        """Set OAuth signature key path (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_signature_key_path"] = value

    @property
    def _encryption_key_path(self) -> str:
        """Get OAuth encryption key path (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            return self.__dict__.get("_encryption_key_path", "")
        return self._auth_manager.encryption_key_path

    @_encryption_key_path.setter
    def _encryption_key_path(self, value: str) -> None:
        """Set OAuth encryption key path (for testing)"""
        if not hasattr(self, "_auth_manager") or self._auth_manager is None:
            self.__dict__["_encryption_key_path"] = value

    @property
    def _connected(self) -> bool:
        """Get connection state (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            return self.__dict__.get("_connected", False)
        return self._connection_manager.is_connected

    @_connected.setter
    def _connected(self, value: bool) -> None:
        """Set connection state (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            self.__dict__["_connected"] = value

    @property
    def _account_id(self) -> str | None:
        """Get account ID (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            return self.__dict__.get("_account_id")
        return self._connection_manager.account_id

    @_account_id.setter
    def _account_id(self, value: str) -> None:
        """Set account ID (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            self.__dict__["_account_id"] = value

    @property
    def _paper_trading(self) -> bool:
        """Get paper trading flag (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            return self.__dict__.get("_paper_trading", True)
        return self._connection_manager._paper_trading  # type: ignore

    @_paper_trading.setter
    def _paper_trading(self, value: bool) -> None:
        """Set paper trading flag (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            self.__dict__["_paper_trading"] = value

    @property
    def _tickle_thread(self) -> object:
        """Get tickle thread (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            return self.__dict__.get("_tickle_thread")
        return self._connection_manager._tickle_thread  # type: ignore

    @_tickle_thread.setter
    def _tickle_thread(self, value: object) -> None:
        """Set tickle thread (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            self.__dict__["_tickle_thread"] = value

    @property
    def _tickle_stop_event(self) -> object:
        """Get tickle stop event (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            return self.__dict__.get("_tickle_stop_event")
        return self._connection_manager._tickle_stop_event  # type: ignore

    @_tickle_stop_event.setter
    def _tickle_stop_event(self, value: object) -> None:
        """Set tickle stop event (for testing)"""
        if (
            not hasattr(self, "_connection_manager")
            or self._connection_manager is None
        ):
            self.__dict__["_tickle_stop_event"] = value

    @property
    def _http_client(self) -> object:
        """Get HTTP client (for testing)"""
        if not hasattr(self, "_request_client") or self._request_client is None:
            return self.__dict__.get("_http_client")
        return self._request_client._http_client  # type: ignore

    @_http_client.setter
    def _http_client(self, value: object) -> None:
        """Set HTTP client (for testing)"""
        if not hasattr(self, "_request_client") or self._request_client is None:
            self.__dict__["_http_client"] = value
        else:
            self._request_client._http_client = value  # type: ignore


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
