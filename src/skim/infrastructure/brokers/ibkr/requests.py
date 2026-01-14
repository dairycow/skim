"""IBKRRequestClient - HTTP requests with retry logic"""

import asyncio
import base64
import hmac
import logging
import random
from datetime import datetime
from hashlib import sha256
from urllib.parse import quote, quote_plus

import httpx
from loguru import logger

from .auth import IBKRAuthManager
from .exceptions import IBKRAuthenticationError, IBKRClientError


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


class IBKRRequestClient:
    """Low-level HTTP request client with retry logic

    Responsibilities:
    - HTTP request execution
    - OAuth signature building
    - Retry logic
    - Error handling
    """

    BASE_URL = "https://api.ibkr.com/v1/api"
    REALM = "limited_poa"
    _logging_bridge_installed = False

    def __init__(self, auth_manager: IBKRAuthManager) -> None:
        """Initialize request client

        Args:
            auth_manager: Auth manager for LST and OAuth credentials
        """
        self._auth_manager = auth_manager
        self._http_client: httpx.AsyncClient | None = None
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

    def set_http_client(self, client: httpx.AsyncClient) -> None:
        """Set the HTTP client (for testing or external management)"""
        self._http_client = client

    async def request(
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

        if self._auth_manager.is_expiring():
            logger.info("LST expiring soon - regenerating before request")
            self._auth_manager.generate_lst()

        url = f"{self.BASE_URL}{endpoint}"
        retry_count = 0
        delay = 1.0
        lst_regenerated = False

        while retry_count <= max_retries:
            try:
                oauth_params = {
                    "oauth_consumer_key": self._auth_manager.consumer_key,
                    "oauth_nonce": hex(random.getrandbits(128))[2:],
                    "oauth_signature_method": "HMAC-SHA256",
                    "oauth_timestamp": str(int(datetime.now().timestamp())),
                    "oauth_token": self._auth_manager.access_token,
                }

                params_string = "&".join(
                    [f"{k}={v}" for k, v in sorted(oauth_params.items())]
                )
                base_string = (
                    f"{method.upper()}&{quote_plus(url)}&{quote(params_string)}"
                )

                lst = self._auth_manager.lst
                if lst is None:
                    raise IBKRClientError("LST is None, cannot sign request")

                bytes_hmac_hash = hmac.new(
                    key=base64.b64decode(lst),
                    msg=base_string.encode("utf-8"),
                    digestmod=sha256,
                ).digest()
                b64_str_hmac_hash = base64.b64encode(bytes_hmac_hash).decode(
                    "utf-8"
                )

                oauth_params["oauth_signature"] = quote_plus(b64_str_hmac_hash)
                oauth_params["realm"] = self.REALM

                oauth_header = "OAuth " + ", ".join(
                    [f'{k}="{v}"' for k, v in sorted(oauth_params.items())]
                )
                headers = {
                    "authorization": oauth_header,
                    "User-Agent": "skim-trading-bot/1.0",
                    "Content-Type": "application/json",
                }

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

                if response.status_code == 200:
                    logger.debug(f"Request successful: {response.status_code}")
                    if response.headers.get("Content-Length", "0") == "0":
                        return {}
                    return response.json()

                elif response.status_code in (401, 410) and not lst_regenerated:
                    self._log_auth_failure(
                        response, "Unauthorized - regenerating LST"
                    )
                    self._auth_manager.generate_lst()
                    lst_regenerated = True
                    continue

                elif response.status_code in (400, 404):
                    logger.error(
                        f"Client error {response.status_code}: {response.text}"
                    )
                    raise IBKRClientError(
                        f"Request failed: {response.status_code} - {response.text}"
                    )

                elif response.status_code in (429, 500, 502, 503):
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
                    logger.error(
                        f"Unexpected error {response.status_code}: {response.text}"
                    )
                    raise IBKRClientError(self._format_error(response))

            except httpx.RequestError as e:
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
