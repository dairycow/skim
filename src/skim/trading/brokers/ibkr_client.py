"""IBKR Client Portal API connection manager

Handles OAuth authentication, session lifecycle, and low-level HTTP requests.
Does NOT handle market data, orders, or scanning - those are delegated to
specialized classes that use this client internally.
"""

import asyncio
import base64
import hmac
import logging
import os
import random
import threading
from datetime import datetime
from hashlib import sha256
from typing import Any, cast
from urllib.parse import quote, quote_plus

import httpx
from loguru import logger

from ..core.config import Config
from .ibkr_oauth import generate_lst


class IBKRClientError(Exception):
    """Base exception for IBKR client errors"""

    pass


class IBKRAuthenticationError(IBKRClientError):
    """Raised when OAuth authentication fails"""

    pass


class IBKRConnectionError(IBKRClientError):
    """Raised when connection fails"""

    pass


class IBKRClient:
    """IBKR Client Portal API connection manager

    Manages:
    - OAuth LST generation and validation
    - Session initialization
    - Keepalive (tickle) mechanism
    - Low-level authenticated HTTP requests with retry logic
    - Account information

    This is a lightweight connection manager. Market data, orders, and scanning
    are handled by specialized classes that use this client internally.
    """

    BASE_URL = "https://api.ibkr.com/v1/api"
    REALM = "limited_poa"
    _logging_bridge_installed = False

    def __init__(self, paper_trading: bool = True) -> None:
        """Initialize IBKR connection manager

        Args:
            paper_trading: If True, verify connected to paper account (DU prefix)

        Raises:
            ValueError: If required OAuth environment variables are missing
        """
        # OAuth credentials from environment
        self._consumer_key = os.getenv("OAUTH_CONSUMER_KEY")
        self._access_token = os.getenv("OAUTH_ACCESS_TOKEN")
        self._access_token_secret = os.getenv("OAUTH_ACCESS_TOKEN_SECRET")
        self._dh_prime_hex = os.getenv("OAUTH_DH_PRIME")

        # OAuth key paths from Config
        config = Config.from_env()
        self._signature_key_path = config.oauth_signature_key_path
        self._encryption_key_path = config.oauth_encryption_key_path

        # Validate all required OAuth config is present
        required_vars = {
            "OAUTH_CONSUMER_KEY": self._consumer_key,
            "OAUTH_ACCESS_TOKEN": self._access_token,
            "OAUTH_ACCESS_TOKEN_SECRET": self._access_token_secret,
            "OAUTH_DH_PRIME": self._dh_prime_hex,
            "signature_key_path": self._signature_key_path,
            "encryption_key_path": self._encryption_key_path,
        }
        missing = [k for k, v in required_vars.items() if v is None]
        if missing:
            raise ValueError(f"Missing OAuth configuration: {missing}")

        # Session state
        self._lst: str | None = None
        self._lst_expiration: int | None = None
        self._account_id: str | None = None
        self._connected: bool = False
        self._paper_trading = paper_trading

        # Keepalive thread
        self._tickle_thread: threading.Thread | None = None
        self._tickle_stop_event: threading.Event = threading.Event()

        # Async HTTP client (lazy init)
        self._http_client: httpx.AsyncClient | None = None

        # Ensure stdlib logging is bridged into loguru for IBKR/httpx modules
        self.install_logging_bridge()

    class _LoguruHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            logger.opt(depth=6, exception=record.exc_info).log(
                level, record.getMessage()
            )

    @classmethod
    def install_logging_bridge(cls) -> None:
        """Bridge stdlib logging used by httpx/ibkr modules into loguru once."""
        if cls._logging_bridge_installed:
            return

        handler = cls._LoguruHandler()
        for name in ("skim.brokers", "httpx"):
            std_logger = logging.getLogger(name)
            std_logger.setLevel(logging.DEBUG)
            std_logger.addHandler(handler)
            std_logger.propagate = False

        cls._logging_bridge_installed = True

    # ========== Connection Management ==========

    def _build_http_client(
        self,
        timeout: int,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> httpx.AsyncClient:
        """Create an AsyncClient with httpx request/response logging hooks."""
        self.install_logging_bridge()
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
        headers = {
            k: ("***" if k.lower() == "authorization" else v)
            for k, v in request.headers.items()
        }
        logger.debug(f"HTTPX request: {request.method} {request.url} {headers}")

    async def _log_httpx_response(self, response: httpx.Response) -> None:
        """Log httpx responses including status and body."""
        try:
            body = response.text
        except Exception:
            body = "<unreadable body>"
        logger.debug(
            f"HTTPX response: status={response.status_code} url={response.url} body={body}"
        )

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
            # Initialize async HTTP client
            if self._http_client is None:
                self._http_client = self._build_http_client(timeout=timeout)

            # Step 1: Generate LST via OAuth
            self._generate_lst()

            # Step 2: Initialize brokerage session
            logger.info("Initializing brokerage session...")
            init_data = {"publish": True, "compete": True}
            init_response = await self._request(
                "POST", "/iserver/auth/ssodh/init", data=init_data
            )
            logger.info(f"Session initialised: {init_response}")

            # Step 3: Poll for authentication if needed
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
                        status_response = await self._request(
                            "GET", "/iserver/auth/status"
                        )
                        logger.info(f"Auth status: {status_response}")

                        if status_response.get("authenticated"):
                            logger.info("Session authenticated successfully!")
                            break
                    except IBKRClientError as e:
                        if poll_attempt < max_poll_attempts - 1:
                            logger.debug(f"Not yet authenticated: {e}")
                            continue
                        else:
                            raise IBKRConnectionError(
                                f"Session did not authenticate after {max_poll_attempts} attempts"
                            ) from e
            else:
                # Session initialised immediately, give it a brief moment
                await asyncio.sleep(2)

            # Step 4: Get account ID
            logger.info("Retrieving account ID...")
            account_response = await self._request("GET", "/iserver/accounts")
            logger.debug(f"Account response: {account_response}")

            # Parse account ID from various response formats
            self._account_id = self._parse_account_id(account_response)

            if not self._account_id:
                raise IBKRConnectionError(
                    f"Could not retrieve account ID from IBKR. Response: {account_response}"
                )

            logger.info(f"Account ID: {self._account_id}")

            # Step 5: Verify paper trading account if required
            if self._paper_trading and not self._account_id.startswith("DU"):
                raise ValueError(
                    f"Paper trading mode enabled but connected to live account: {self._account_id}"
                )

            self._connected = True

            # Step 6: Start keepalive thread
            self._start_tickle_thread()

            logger.info("Successfully connected to IBKR")

        except Exception as e:
            self._connected = False
            if isinstance(e, (IBKRClientError, ValueError)):
                raise
            raise IBKRConnectionError(f"Connection failed: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from IBKR and cleanup resources"""
        logger.info("Disconnecting from IBKR...")

        # Stop keepalive thread
        self._stop_tickle_thread()

        # Close HTTP client
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

        # Clear session state
        self._connected = False
        self._lst = None
        self._lst_expiration = None
        self._account_id = None

        logger.info("Disconnected from IBKR")

    def is_connected(self) -> bool:
        """Check if session is still valid

        Returns:
            True if connected and LST is valid, False otherwise
        """
        return self._connected and self._lst is not None

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

    # ========== OAuth & Session Management (Private) ==========

    def _generate_lst(self) -> None:
        """Generate new Live Session Token via OAuth flow

        Updates self._lst and self._lst_expiration

        Raises:
            IBKRAuthenticationError: If LST generation fails
        """
        logger.info("Generating new Live Session Token...")

        try:
            self._lst, self._lst_expiration = generate_lst(
                cast(str, self._consumer_key),
                cast(str, self._access_token),
                cast(str, self._access_token_secret),
                cast(str, self._dh_prime_hex),
                cast(str, self._signature_key_path),
                cast(str, self._encryption_key_path),
                realm=self.REALM,
            )
            expiration_dt = datetime.fromtimestamp(self._lst_expiration / 1000)
            logger.info(
                f"LST generated successfully, expires at {expiration_dt}"
            )

        except Exception as e:
            raise IBKRAuthenticationError(f"LST generation failed: {e}") from e

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

    # ========== Keepalive Thread (Tickle) ==========

    def _tickle_worker(self) -> None:
        """Background worker that pings /tickle every 60 seconds

        Keeps session alive during inactivity.
        """
        logger.info("Tickle worker started - will ping every 60s")
        while not self._tickle_stop_event.wait(timeout=60):
            try:
                logger.debug("Sending tickle request to keep session alive...")
                asyncio.run(self._request("POST", "/iserver/tickle"))
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

    # ========== Low-Level HTTP Requests ==========

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
        max_retries: int = 5,
    ) -> dict:
        """Make authenticated HTTP request with exponential backoff retry logic

        Retry Strategy:
        - Exponential backoff: 1s, 2s, 4s, 8s, 16s (±10% jitter)
        - Retry on: network errors, 500/502/503, 429 (rate limit)
        - Don't retry: 400 (bad request), 404 (not found)
        - Special: 401 → regenerate LST → retry once

        Args:
            method: HTTP method (GET, POST, DELETE)
            endpoint: API endpoint path (e.g., "/iserver/account")
            data: JSON payload for POST requests
            params: Query parameters
            max_retries: Maximum number of retry attempts

        Returns:
            Response JSON as dict

        Raises:
            IBKRClientError: If request fails after all retries
        """
        if self._http_client is None:
            raise IBKRClientError("HTTP client not initialized")

        if self._is_lst_expiring():
            logger.info("LST expiring soon - regenerating before request")
            self._generate_lst()

        url = f"{self.BASE_URL}{endpoint}"
        retry_count = 0
        delay = 1.0
        lst_regenerated = False

        while retry_count <= max_retries:
            try:
                # Build OAuth signature for this request
                oauth_params = {
                    "oauth_consumer_key": self._consumer_key,
                    "oauth_nonce": hex(random.getrandbits(128))[2:],
                    "oauth_signature_method": "HMAC-SHA256",
                    "oauth_timestamp": str(int(datetime.now().timestamp())),
                    "oauth_token": self._access_token,
                }

                # Create signature base string
                params_string = "&".join(
                    [f"{k}={v}" for k, v in sorted(oauth_params.items())]
                )
                base_string = (
                    f"{method.upper()}&{quote_plus(url)}&{quote(params_string)}"
                )

                # Sign with HMAC-SHA256 using LST
                if self._lst is None:
                    raise IBKRClientError("LST is None, cannot sign request")

                bytes_hmac_hash = hmac.new(
                    key=base64.b64decode(cast(str, self._lst)),
                    msg=base_string.encode("utf-8"),
                    digestmod=sha256,
                ).digest()
                b64_str_hmac_hash = base64.b64encode(bytes_hmac_hash).decode(
                    "utf-8"
                )

                oauth_params["oauth_signature"] = quote_plus(b64_str_hmac_hash)
                oauth_params["realm"] = self.REALM

                # Build authorization header
                oauth_header = "OAuth " + ", ".join(
                    [f'{k}="{v}"' for k, v in sorted(oauth_params.items())]
                )
                headers = {
                    "authorization": oauth_header,
                    "User-Agent": "skim-trading-bot/1.0",
                    "Content-Type": "application/json",
                }

                # Make request
                logger.debug(f"{method} {url} (attempt {retry_count + 1})")

                if method.upper() == "GET":
                    response = await self._http_client.get(
                        url, headers=headers, params=params
                    )
                elif method.upper() == "POST":
                    response = await self._http_client.post(
                        url, headers=headers, json=data, params=params
                    )
                elif method.upper() == "DELETE":
                    response = await self._http_client.delete(
                        url, headers=headers, params=params
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle response
                if response.status_code == 200:
                    logger.debug(f"Request successful: {response.status_code}")
                    # Handle tickle response which may be empty
                    if response.headers.get("Content-Length", "0") == "0":
                        return {}
                    return response.json()

                elif response.status_code in (401, 410) and not lst_regenerated:
                    # Auth expired - regenerate LST and retry once
                    self._log_auth_failure(
                        response, "Unauthorized - regenerating LST"
                    )
                    self._generate_lst()
                    lst_regenerated = True
                    continue

                elif response.status_code in (400, 404):
                    # Client errors - don't retry
                    logger.error(
                        f"Client error {response.status_code}: {response.text}"
                    )
                    raise IBKRClientError(
                        f"Request failed: {response.status_code} - {response.text}"
                    )

                elif response.status_code in (429, 500, 502, 503):
                    # Rate limit or server errors - retry with backoff
                    logger.warning(
                        f"Retryable error {response.status_code}: {response.text}"
                    )
                    if retry_count < max_retries:
                        jitter = delay * 0.1 * (random.random() * 2 - 1)
                        sleep_time = delay + jitter
                        logger.info(f"Retrying in {sleep_time:.2f}s...")
                        await asyncio.sleep(sleep_time)
                        delay *= 2
                        retry_count += 1
                        continue
                    else:
                        raise IBKRClientError(
                            f"Max retries exceeded: {response.status_code} - {response.text}"
                        )

                elif response.status_code in (401, 410) and lst_regenerated:
                    self._log_auth_failure(
                        response,
                        "Authentication failed after LST regeneration",
                    )
                    raise IBKRAuthenticationError(self._format_error(response))

                else:
                    # Other errors
                    logger.error(
                        f"Unexpected error {response.status_code}: {response.text}"
                    )
                    raise IBKRClientError(self._format_error(response))

            except httpx.RequestError as e:
                # Network errors - retry with backoff
                logger.warning(f"Network error: {e}")
                if retry_count < max_retries:
                    jitter = delay * 0.1 * (random.random() * 2 - 1)
                    sleep_time = delay + jitter
                    logger.info(f"Retrying in {sleep_time:.2f}s...")
                    await asyncio.sleep(sleep_time)
                    delay *= 2
                    retry_count += 1
                    continue
                else:
                    raise IBKRClientError(f"Max retries exceeded: {e}") from e

        if lst_regenerated:
            raise IBKRAuthenticationError(
                f"Authentication failed after LST regeneration: {endpoint}"
            )

        raise IBKRClientError("Request failed after all retries")

    def _format_error(self, response: httpx.Response) -> str:
        """Return a safe string describing an HTTP error without assuming keys."""
        body: str
        try:
            parsed = response.json()
            body = str(parsed)
        except Exception:
            body = response.text
        return f"Request failed: {response.status_code} - {body}"

    def _log_auth_failure(self, response: httpx.Response, prefix: str) -> None:
        """Log auth failures with safe body parsing to avoid KeyError."""
        try:
            body = response.json()
        except Exception:
            body = response.text
        logger.warning(f"{prefix} ({response.status_code}): {body}")

    def _is_lst_expiring(self, skew_seconds: int = 300) -> bool:
        """Check if current LST is close to expiring.

        Returns:
            True if close to expiration (within skew_seconds)
        """
        if self._lst_expiration is None:
            return False
        now_ms = int(datetime.now().timestamp() * 1000)
        return self._lst_expiration <= now_ms + (skew_seconds * 1000)
