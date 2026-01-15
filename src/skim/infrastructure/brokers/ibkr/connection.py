"""IBKRConnectionManager - Connection lifecycle and keepalive"""

import asyncio
import logging
import threading
from typing import TYPE_CHECKING, Any

from loguru import logger

from .exceptions import IBKRConnectionError

if TYPE_CHECKING:
    from .auth import IBKRAuthManager
    from .requests import IBKRRequestClient


class _LoguruHandler(logging.Handler):
    """Bridge stdlib logging into loguru"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno
        logger.opt(depth=6, exception=record.exc_info).log(
            level, record.getMessage()
        )


class IBKRConnectionManager:
    """Manages IBKR connection lifecycle and keepalive

    Responsibilities:
    - Session initialization
    - Keepalive thread management
    - Account ID retrieval
    """

    BASE_URL = "https://api.ibkr.com/v1/api"
    _logging_bridge_installed = False

    def __init__(
        self,
        auth_manager: "IBKRAuthManager",
        request_client: "IBKRRequestClient",
        paper_trading: bool = True,
    ) -> None:
        """Initialize connection manager

        Args:
            auth_manager: Auth manager instance for LST generation
            request_client: Request client for HTTP calls
            paper_trading: If True, verify connected to paper account (DU prefix)

        Raises:
            ValueError: If paper_trading required but not a paper account
        """
        self._auth_manager = auth_manager
        self._request_client = request_client
        self._paper_trading = paper_trading

        self._account_id: str | None = None
        self._connected: bool = False

        self._tickle_thread: threading.Thread | None = None
        self._tickle_stop_event: threading.Event = threading.Event()

        self.install_logging_bridge()

    @classmethod
    def install_logging_bridge(cls) -> None:
        """Bridge stdlib logging used by httpx/ibkr modules into loguru once."""
        if cls._logging_bridge_installed:
            return

        handler = _LoguruHandler()
        for name in ("skim.brokers", "httpx"):
            std_logger = logging.getLogger(name)
            std_logger.setLevel(logging.DEBUG)
            std_logger.addHandler(handler)
            std_logger.propagate = False

        cls._logging_bridge_installed = True

    @property
    def is_connected(self) -> bool:
        """Check if session is still valid

        Returns:
            True if connected and LST is valid, False otherwise
        """
        return self._connected and self._auth_manager.lst is not None

    @property
    def account_id(self) -> str | None:
        """Get connected account ID"""
        return self._account_id

    async def connect(self, timeout: int = 20) -> None:
        """Establish authenticated session with IBKR

        Steps:
        1. Generate LST via OAuth flow
        2. POST /iserver/auth/ssodh/init - Initialise brokerage session
        3. GET /iserver/auth/status - Poll until authenticated (if needed)
        4. GET /iserver/accounts - Get account ID
        5. Verify paper trading (account starts with 'DU')
        6. Start keepalive thread

        Args:
            timeout: Connection timeout in seconds

        Raises:
            IBKRAuthenticationError: If OAuth flow fails
            IBKRConnectionError: If connection or authentication fails
            ValueError: If not paper trading account when paper_trading=True
        """
        logger.info("Connecting to IBKR via OAuth...")

        try:
            self._auth_manager.generate_lst()

            logger.info("Initializing HTTP client...")
            self._request_client._http_client = (
                self._request_client._build_http_client(timeout=timeout)
            )

            logger.info("Initializing brokerage session...")
            init_data = {"publish": True, "compete": True}
            init_response = await self._request_client.request(
                "POST", "/iserver/auth/ssodh/init", data=init_data
            )
            logger.info(f"Session initialised: {init_response}")

            if init_response.get("wait"):
                logger.info(
                    "Session requires polling - checking authentication status..."
                )
                max_poll_attempts = 10
                poll_delay = 2.0

                for poll_attempt in range(max_poll_attempts):
                    await asyncio.sleep(poll_delay)
                    try:
                        logger.debug(
                            f"Polling attempt {poll_attempt + 1}/{max_poll_attempts}"
                        )
                        status_response = await self._request_client.request(
                            "GET", "/iserver/auth/status"
                        )
                        logger.info(f"Auth status: {status_response}")

                        if status_response.get("authenticated"):
                            logger.info("Session authenticated successfully!")
                            break
                    except Exception as e:
                        if poll_attempt < max_poll_attempts - 1:
                            logger.debug(f"Not yet authenticated: {e}")
                            continue
                        else:
                            raise IBKRConnectionError(
                                f"Session did not authenticate after {max_poll_attempts} attempts"
                            ) from e
            else:
                await asyncio.sleep(2)

            logger.info("Retrieving account ID...")
            account_response = await self._request_client.request(
                "GET", "/iserver/accounts"
            )
            logger.debug(f"Account response: {account_response}")

            self._account_id = self._parse_account_id(account_response)

            if not self._account_id:
                raise IBKRConnectionError(
                    f"Could not retrieve account ID from IBKR. Response: {account_response}"
                )

            logger.info(f"Account ID: {self._account_id}")

            if self._paper_trading and not self._account_id.startswith("DU"):
                raise ValueError(
                    f"Paper trading mode enabled but connected to live account: {self._account_id}"
                )

            self._connected = True

            self._start_tickle_thread()

            logger.info("Successfully connected to IBKR")

        except Exception as e:
            self._connected = False
            from .exceptions import IBKRClientError

            if isinstance(e, (IBKRClientError, ValueError)):
                raise
            raise IBKRConnectionError(f"Connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from IBKR and cleanup resources"""
        logger.info("Disconnecting from IBKR...")

        if self._request_client._http_client is not None:
            await self._request_client._http_client.aclose()
            self._request_client._http_client = None

        self._stop_tickle_thread()

        self._connected = False
        self._account_id = None

        logger.info("Disconnected from IBKR")

    def get_account(self) -> str:
        """Get connected account ID

        Returns:
            Account ID string (e.g., "DUN090463" for paper account)

        Raises:
            IBKRConnectionError: If not connected
        """
        if not self._account_id:
            raise IBKRConnectionError("Not connected - call connect() first")
        return self._account_id

    def _parse_account_id(self, response: Any) -> str | None:
        """Parse account ID from various IBKR response formats

        Args:
            response: Response from /iserver/accounts endpoint

        Returns:
            Account ID string or None if not found
        """
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

    def _tickle_worker(self) -> None:
        """Background worker that pings /tickle every 60 seconds

        Keeps session alive during inactivity.
        """
        logger.info("Tickle worker started - will ping every 60s")
        while not self._tickle_stop_event.wait(timeout=60):
            try:
                logger.debug("Sending tickle request to keep session alive...")
                asyncio.run(
                    self._request_client.request("POST", "/iserver/tickle")
                )
            except Exception as e:
                logger.warning(f"Tickle request failed: {e}")

        logger.info("Tickle worker stopped")

    def _start_tickle_thread(self) -> None:
        """Start the background keepalive thread"""
        if self._tickle_thread and self._tickle_thread.is_alive():
            logger.warning("Tickle thread already running")
            return

        self._tickle_stop_event.clear()
        self._tickle_thread = threading.Thread(
            target=self._tickle_worker, daemon=True, name="IBKRTickle"
        )
        self._tickle_thread.start()
        logger.info("Started session keepalive thread")

    def _stop_tickle_thread(self) -> None:
        """Stop the background keepalive thread"""
        if not self._tickle_thread or not self._tickle_thread.is_alive():
            return

        logger.info("Stopping tickle thread...")
        self._tickle_stop_event.set()
        self._tickle_thread.join(timeout=5)
        if self._tickle_thread.is_alive():
            logger.warning("Tickle thread did not stop gracefully")
