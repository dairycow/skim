"""Custom IBKR Client Portal API client with OAuth authentication

This module provides a lightweight client for IBKR's Client Portal API,
implementing only the operations needed for swing trading:
- Order management (market, stop market, stop limit)
- Position queries
- Account information
- Market data snapshots

Architecture:
- OAuth 1.0a authentication via Live Session Token (LST)
- Exponential backoff retry logic
- Automatic LST regeneration on 401 errors
- Contract ID caching to reduce API calls
"""

import base64
import hmac
import logging
import os
import random
import threading
import time
from datetime import datetime
from hashlib import sha256
from typing import Any
from urllib.parse import quote, quote_plus

import requests

from .ib_interface import IBInterface, MarketData, OrderResult
from .ibkr_oauth import generate_lst

logger = logging.getLogger(__name__)


class IBKRClient(IBInterface):
    """Custom IBKR Client Portal API client with OAuth

    This client implements the IBInterface protocol and provides
    authenticated access to IBKR's Client Portal API endpoints.
    """

    BASE_URL = "https://api.ibkr.com/v1/api"
    REALM = "limited_poa"

    def __init__(self, paper_trading: bool = True):
        """Initialize IBKR client

        Args:
            paper_trading: If True, verify connected to paper account (DU prefix)
        """
        self._lst: str | None = None
        self._lst_expiration: int | None = None
        self._account_id: str | None = None
        self._connected: bool = False
        self._paper_trading = paper_trading
        self._contract_cache: dict[str, str] = {}  # ticker -> conid

        # Session keepalive (tickle) thread
        self._tickle_thread: threading.Thread | None = None
        self._tickle_stop_event: threading.Event = threading.Event()

        # Load OAuth config from environment
        self._consumer_key = os.getenv("OAUTH_CONSUMER_KEY")
        self._access_token = os.getenv("OAUTH_ACCESS_TOKEN")
        self._access_token_secret = os.getenv("OAUTH_ACCESS_TOKEN_SECRET")
        self._dh_prime_hex = os.getenv("OAUTH_DH_PRIME")
        self._signature_key_path = os.getenv("OAUTH_SIGNATURE_PATH")
        self._encryption_key_path = os.getenv("OAUTH_ENCRYPTION_PATH")

        # Validate required config
        required_vars = [
            "OAUTH_CONSUMER_KEY",
            "OAUTH_ACCESS_TOKEN",
            "OAUTH_ACCESS_TOKEN_SECRET",
            "OAUTH_DH_PRIME",
            "OAUTH_SIGNATURE_PATH",
            "OAUTH_ENCRYPTION_PATH",
        ]
        missing = [var for var in required_vars if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")

    def _generate_lst(self) -> None:
        """Generate new Live Session Token via OAuth flow

        Updates self._lst and self._lst_expiration

        Raises:
            RuntimeError: If LST generation fails
        """
        logger.info("Generating new Live Session Token...")
        self._lst, self._lst_expiration = generate_lst(
            consumer_key=self._consumer_key,
            access_token=self._access_token,
            access_token_secret=self._access_token_secret,
            dh_prime_hex=self._dh_prime_hex,
            signature_key_path=self._signature_key_path,
            encryption_key_path=self._encryption_key_path,
            realm=self.REALM,
        )
        expiration_dt = datetime.fromtimestamp(self._lst_expiration / 1000)
        logger.info(f"LST generated successfully, expires at {expiration_dt}")

    def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        params: dict | None = None,
        max_retries: int = 5,
    ) -> dict:
        """Make authenticated HTTP request with retry logic

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
            RuntimeError: If request fails after all retries
        """
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
                bytes_hmac_hash = hmac.new(
                    key=base64.b64decode(self._lst),
                    msg=base_string.encode("utf-8"),
                    digestmod=sha256,
                ).digest()
                b64_str_hmac_hash = base64.b64encode(bytes_hmac_hash).decode("utf-8")
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
                    response = requests.get(
                        url, headers=headers, params=params, timeout=30
                    )
                elif method.upper() == "POST":
                    response = requests.post(
                        url, headers=headers, json=data, params=params, timeout=30
                    )
                elif method.upper() == "DELETE":
                    response = requests.delete(
                        url, headers=headers, params=params, timeout=30
                    )
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                # Handle response
                if response.status_code == 200:
                    logger.debug(f"Request successful: {response.status_code}")
                    return response.json()

                elif response.status_code == 401 and not lst_regenerated:
                    # Auth expired - regenerate LST and retry once
                    logger.warning("401 Unauthorized - regenerating LST")
                    self._generate_lst()
                    lst_regenerated = True
                    continue

                elif response.status_code in (400, 404):
                    # Client errors - don't retry
                    logger.error(
                        f"Client error {response.status_code}: {response.text}"
                    )
                    raise RuntimeError(
                        f"Request failed: {response.status_code} - {response.text}"
                    )

                elif response.status_code in (429, 500, 502, 503):
                    # Rate limit or server errors - retry with backoff
                    logger.warning(
                        f"Retryable error {response.status_code}: {response.text}"
                    )
                    if retry_count < max_retries:
                        # Add jitter (±10%)
                        jitter = delay * 0.1 * (random.random() * 2 - 1)
                        sleep_time = delay + jitter
                        logger.info(f"Retrying in {sleep_time:.2f}s...")
                        time.sleep(sleep_time)
                        delay *= 2  # Exponential backoff
                        retry_count += 1
                        continue
                    else:
                        raise RuntimeError(
                            f"Max retries exceeded: {response.status_code} - {response.text}"
                        )

                else:
                    # Other errors
                    logger.error(
                        f"Unexpected error {response.status_code}: {response.text}"
                    )
                    raise RuntimeError(
                        f"Request failed: {response.status_code} - {response.text}"
                    )

            except requests.exceptions.RequestException as e:
                # Network errors - retry with backoff
                logger.warning(f"Network error: {e}")
                if retry_count < max_retries:
                    jitter = delay * 0.1 * (random.random() * 2 - 1)
                    sleep_time = delay + jitter
                    logger.info(f"Retrying in {sleep_time:.2f}s...")
                    time.sleep(sleep_time)
                    delay *= 2
                    retry_count += 1
                    continue
                else:
                    raise RuntimeError(f"Max retries exceeded: {e}")

        raise RuntimeError("Request failed after all retries")

    def _tickle_worker(self) -> None:
        """Background worker that pings /tickle every 60 seconds to keep session alive

        This prevents the IBKR session from timing out due to inactivity.
        Runs in a daemon thread until _tickle_stop_event is set.
        """
        logger.info("Tickle worker started - will ping every 60s")
        while not self._tickle_stop_event.wait(timeout=60):
            try:
                logger.debug("Sending tickle request to keep session alive...")
                response = self._request("POST", "/tickle")
                logger.debug(f"Tickle response: {response}")
            except Exception as e:
                logger.warning(f"Tickle request failed: {e}")
                # Continue trying - session may recover

        logger.info("Tickle worker stopped")

    def _start_tickle_thread(self) -> None:
        """Start the background tickle thread"""
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
        """Stop the background tickle thread"""
        if not self._tickle_thread or not self._tickle_thread.is_alive():
            return

        logger.info("Stopping tickle thread...")
        self._tickle_stop_event.set()
        self._tickle_thread.join(timeout=5)
        if self._tickle_thread.is_alive():
            logger.warning("Tickle thread did not stop gracefully")

    # ========== Connection & Session Management ==========

    def connect(
        self, host: str, port: int, client_id: int, timeout: int = 20
    ) -> None:
        """Establish authenticated session with IBKR

        Steps:
        1. Generate LST via OAuth flow
        2. POST /iserver/auth/ssodh/init - Initialize brokerage session
        3. GET /iserver/account - Get account ID
        4. Verify paper trading (account starts with 'DU')

        Args:
            host: Ignored (OAuth uses api.ibkr.com)
            port: Ignored (OAuth uses HTTPS)
            client_id: Ignored (OAuth uses consumer key)
            timeout: Connection timeout in seconds

        Raises:
            ValueError: If not paper trading account when paper_trading=True
            RuntimeError: If connection fails
        """
        logger.info("Connecting to IBKR via OAuth...")

        # Step 1: Generate LST
        self._generate_lst()

        # Step 2: Initialize brokerage session
        logger.info("Initializing brokerage session...")
        # Note: Paper trading requires compete: True to fully authenticate
        init_data = {"publish": True, "compete": True}
        init_response = self._request("POST", "/iserver/auth/ssodh/init", data=init_data)
        logger.info(f"Session initialized: {init_response}")

        # Step 3: Poll for authentication status if needed
        # If response contains 'wait': True, we need to poll until authenticated
        if init_response.get("wait"):
            logger.info("Session requires polling - checking authentication status...")
            max_poll_attempts = 10
            poll_delay = 2.0

            for poll_attempt in range(max_poll_attempts):
                time.sleep(poll_delay)
                try:
                    # Try to get accounts - if it works, we're authenticated
                    logger.debug(f"Polling attempt {poll_attempt + 1}/{max_poll_attempts}")
                    status_response = self._request("GET", "/iserver/auth/status")
                    logger.info(f"Auth status: {status_response}")

                    if status_response.get("authenticated"):
                        logger.info("Session authenticated successfully!")
                        break
                except RuntimeError as e:
                    if poll_attempt < max_poll_attempts - 1:
                        logger.debug(f"Not yet authenticated: {e}")
                        continue
                    else:
                        raise RuntimeError(
                            f"Session did not authenticate after {max_poll_attempts} attempts"
                        )
        else:
            # Session initialized immediately, give it a brief moment
            time.sleep(2)

        # Step 4: Get account ID
        logger.info("Retrieving account ID...")
        account_response = self._request("GET", "/iserver/accounts")
        logger.debug(f"Account response: {account_response}")

        # Response can be various formats - parse carefully
        if isinstance(account_response, dict):
            # If dict has 'accounts' key with a list
            if "accounts" in account_response:
                accounts_list = account_response["accounts"]
                if accounts_list and len(accounts_list) > 0:
                    self._account_id = accounts_list[0]
            # If dict is a single account object with 'accountId'
            elif "accountId" in account_response:
                self._account_id = account_response["accountId"]
            # If dict has other account ID fields
            else:
                # Try common variations
                self._account_id = (
                    account_response.get("id")
                    or account_response.get("accountId")
                    or account_response.get("account")
                )
        elif isinstance(account_response, list) and len(account_response) > 0:
            # Response is a list - take first item
            first_item = account_response[0]
            if isinstance(first_item, str):
                self._account_id = first_item
            elif isinstance(first_item, dict):
                self._account_id = first_item.get("accountId") or first_item.get("id")

        if not self._account_id:
            raise RuntimeError(
                f"Could not retrieve account ID from IBKR. Response: {account_response}"
            )

        logger.info(f"Account ID: {self._account_id}")

        # Step 4: Verify paper trading account if required
        if self._paper_trading and not self._account_id.startswith("DU"):
            raise ValueError(
                f"Paper trading mode enabled but connected to live account: {self._account_id}"
            )

        self._connected = True

        # Step 5: Start keepalive thread
        self._start_tickle_thread()

        logger.info("Successfully connected to IBKR")

    def is_connected(self) -> bool:
        """Check if session is still valid

        Simple check: self._connected and self._lst is not None
        (Will regenerate LST on 401 automatically)
        """
        return self._connected and self._lst is not None

    def disconnect(self) -> None:
        """Disconnect from IBKR

        Stops the tickle thread and clears session state
        """
        # Stop keepalive thread
        self._stop_tickle_thread()

        # Clear session state
        self._connected = False
        self._lst = None
        self._lst_expiration = None
        self._account_id = None
        logger.info("Disconnected from IBKR")

    def get_account(self) -> str:
        """Get the connected account ID

        Returns:
            Account ID string (e.g., "DUN090463" for paper account)

        Raises:
            RuntimeError: If not connected
        """
        if not self._account_id:
            raise RuntimeError("Not connected - call connect() first")
        return self._account_id

    def get_account_balance(self) -> dict:
        """Get account balance for position sizing

        Endpoint: GET /portfolio/{accountId}/summary

        Returns:
            Dictionary with:
            - availableFunds: Cash available for trading
            - netLiquidation: Total account value
            - buyingPower: Margin buying power

        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self._connected:
            raise RuntimeError("Not connected - call connect() first")

        endpoint = f"/portfolio/{self._account_id}/summary"
        response = self._request("GET", endpoint)

        # Extract key balance fields from response
        # IBKR returns a complex structure - parse carefully
        balance = {}

        if isinstance(response, dict):
            # Try to find balance info in various possible locations
            if "availablefunds" in response:
                balance["availableFunds"] = float(response["availablefunds"].get("amount", 0))
            if "netliquidation" in response:
                balance["netLiquidation"] = float(response["netliquidation"].get("amount", 0))
            if "buyingpower" in response:
                balance["buyingPower"] = float(response["buyingpower"].get("amount", 0))

            # If no fields found, log the response structure
            if not balance:
                logger.warning(f"Could not parse balance from response: {response}")
                # Return raw response for debugging
                return response

        return balance

    def get_positions(self) -> list[dict]:
        """Get current positions from IBKR (source of truth)

        Endpoint: GET /portfolio/{accountId}/positions/0

        Returns:
            List of position dictionaries with:
            - ticker (symbol): Stock ticker
            - conid: IBKR contract ID
            - position: Quantity (negative = short)
            - avgPrice: Average entry price
            - mktPrice: Current market price
            - unrealizedPnL: Unrealized profit/loss

        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self._connected:
            raise RuntimeError("Not connected - call connect() first")

        endpoint = f"/portfolio/{self._account_id}/positions/0"
        response = self._request("GET", endpoint)

        positions = []

        if isinstance(response, list):
            for pos in response:
                if isinstance(pos, dict):
                    # Extract relevant fields
                    position_dict = {
                        "ticker": pos.get("contractDesc") or pos.get("ticker") or pos.get("symbol"),
                        "conid": pos.get("conid"),
                        "position": pos.get("position", 0),
                        "avgPrice": pos.get("avgPrice", 0.0),
                        "mktPrice": pos.get("mktPrice", 0.0),
                        "unrealizedPnL": pos.get("unrealizedPnL", 0.0),
                    }
                    positions.append(position_dict)

        return positions

    # ========== Market Data ==========

    def _get_contract_id(self, ticker: str) -> str:
        """Look up IBKR contract ID (conid) for ticker

        Endpoint: GET /iserver/secdef/search?symbol={ticker}

        Uses cache to avoid repeated lookups. Filters for:
        - secType="STK" (stocks)
        - Prefers ASX exchange for Australian stocks, falls back to any STK

        Args:
            ticker: Stock ticker symbol (e.g., "BHP", "AAPL")

        Returns:
            Contract ID (conid) as string

        Raises:
            RuntimeError: If ticker not found or request fails
        """
        # Check cache first
        if ticker in self._contract_cache:
            logger.debug(f"Contract ID for {ticker} found in cache: {self._contract_cache[ticker]}")
            return self._contract_cache[ticker]

        # Search for contract
        endpoint = "/iserver/secdef/search"
        params = {"symbol": ticker}
        response = self._request("GET", endpoint, params=params)

        logger.debug(f"Contract search response for {ticker}: {response}")

        conid = None
        asx_conid = None

        if isinstance(response, list):
            # Response is a list of matching contracts
            # First pass: look for ASX stocks specifically
            for contract in response:
                if isinstance(contract, dict):
                    description = contract.get("description", "")
                    sections = contract.get("sections", [])

                    # Check if this contract has STK (stock) in sections
                    has_stk = any(
                        isinstance(section, dict) and section.get("secType") == "STK"
                        for section in sections
                    )

                    if has_stk:
                        current_conid = str(contract.get("conid"))
                        logger.debug(f"Found STK contract: {contract.get('companyHeader')} - conid: {current_conid}")

                        # Prefer ASX exchange
                        if "ASX" in description.upper():
                            asx_conid = current_conid
                            logger.debug(f"Found ASX contract: {contract.get('companyHeader')}")
                            break

                        # Keep first STK as fallback
                        if not conid:
                            conid = current_conid

            # Prefer ASX if found, otherwise use first STK
            conid = asx_conid or conid

        if not conid:
            raise RuntimeError(
                f"Could not find contract ID for ticker: {ticker}. Response: {response}"
            )

        # Cache the result
        self._contract_cache[ticker] = conid
        logger.debug(f"Cached contract ID for {ticker}: {conid}")

        return conid

    def get_market_data(self, ticker: str) -> MarketData | None:
        """Get current market snapshot

        Flow:
        1. Look up conid via _get_contract_id()
        2. GET /iserver/marketdata/snapshot?conids={conid}
        3. Parse fields: 31=last, 84=bid, 86=ask, 87=volume
        4. Return MarketData object

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")

        Returns:
            MarketData object if successful, None on failure

        Raises:
            RuntimeError: If not connected or ticker not found
        """
        if not self._connected:
            raise RuntimeError("Not connected - call connect() first")

        # Step 1: Get contract ID
        conid = self._get_contract_id(ticker)

        # Step 2: Get market snapshot
        endpoint = "/iserver/marketdata/snapshot"
        params = {"conids": conid}
        response = self._request("GET", endpoint, params=params)

        # Step 3: Parse response
        if isinstance(response, list) and len(response) > 0:
            data = response[0]
            if isinstance(data, dict):
                # IBKR uses field codes: 31=last, 84=bid, 86=ask, 87=volume
                last_price = data.get("31") or data.get("last") or 0.0
                bid = data.get("84") or data.get("bid") or 0.0
                ask = data.get("86") or data.get("ask") or 0.0
                volume = data.get("87") or data.get("volume") or 0

                return MarketData(
                    ticker=ticker,
                    last_price=float(last_price),
                    bid=float(bid),
                    ask=float(ask),
                    volume=int(volume),
                )

        logger.warning(f"Could not get market data for {ticker}")
        return None

    # ========== Order Management ==========

    def place_order(
        self,
        ticker: str,
        action: str,
        quantity: int,
        order_type: str = "MKT",
        limit_price: float | None = None,
        stop_price: float | None = None,
    ) -> OrderResult | None:
        """Place order with flexible order types

        Order Types:
        - "MKT": Market order (immediate execution)
        - "STP": Stop market (triggers market order at stop_price)
        - "STP LMT": Stop limit (triggers limit at stop_price, fills at limit_price)

        Flow:
        1. Look up contract ID (conid) via _get_contract_id()
        2. Build order JSON based on order_type
        3. POST /iserver/account/{accountId}/orders
        4. Handle confirmation questions (auto-accept common ones)
        5. Return OrderResult with order_id and status

        Args:
            ticker: Stock ticker symbol (e.g., "AAPL")
            action: Order action ("BUY" or "SELL")
            quantity: Number of shares
            order_type: Order type ("MKT", "STP", "STP LMT")
            limit_price: Limit price (required for "STP LMT")
            stop_price: Stop price (required for "STP" and "STP LMT")

        Returns:
            OrderResult or None on failure

        Raises:
            RuntimeError: If not connected or order fails
            ValueError: If invalid order type or missing prices
        """
        if not self._connected:
            raise RuntimeError("Not connected - call connect() first")

        # Validate order type
        if order_type not in ("MKT", "STP", "STP LMT"):
            raise ValueError(f"Invalid order type: {order_type}")

        if order_type in ("STP", "STP LMT") and stop_price is None:
            raise ValueError(f"stop_price required for {order_type} orders")

        if order_type == "STP LMT" and limit_price is None:
            raise ValueError("limit_price required for STP LMT orders")

        # Step 1: Get contract ID
        conid = self._get_contract_id(ticker)

        # Step 2: Build order JSON
        order_data = {
            "conid": int(conid),
            "orderType": order_type,
            "side": action.upper(),
            "quantity": quantity,
            "tif": "DAY",  # Time in force: Day order
        }

        if limit_price is not None:
            order_data["price"] = limit_price

        if stop_price is not None:
            order_data["auxPrice"] = stop_price

        logger.info(f"Placing {order_type} order: {action} {quantity} {ticker} @ {order_data}")

        # Step 3: Submit order
        endpoint = f"/iserver/account/{self._account_id}/orders"
        orders_payload = {"orders": [order_data]}

        try:
            response = self._request("POST", endpoint, data=orders_payload)
            logger.debug(f"Order response: {response}")

            # Step 4: Handle confirmation questions
            # IBKR may return confirmation questions that need to be answered
            if isinstance(response, list) and len(response) > 0:
                first_response = response[0]

                # Check if order was accepted
                if isinstance(first_response, dict):
                    order_id = first_response.get("order_id") or first_response.get("id")
                    status = first_response.get("order_status", "submitted")

                    # If we have an order ID, it was accepted
                    if order_id:
                        return OrderResult(
                            order_id=str(order_id),
                            ticker=ticker,
                            action=action,
                            quantity=quantity,
                            status=status,
                        )

                # Check if confirmation is needed
                if isinstance(first_response, dict) and "message" in first_response:
                    # Confirmation required - reply to confirm
                    reply_id = first_response.get("id")
                    if reply_id:
                        logger.info(f"Order requires confirmation: {first_response.get('message')}")
                        confirm_endpoint = f"/iserver/reply/{reply_id}"
                        confirm_data = {"confirmed": True}
                        confirm_response = self._request("POST", confirm_endpoint, data=confirm_data)
                        logger.debug(f"Confirmation response: {confirm_response}")

                        # Extract order ID from confirmation response
                        if isinstance(confirm_response, list) and len(confirm_response) > 0:
                            confirmed_order = confirm_response[0]
                            if isinstance(confirmed_order, dict):
                                order_id = confirmed_order.get("order_id") or confirmed_order.get("id")
                                status = confirmed_order.get("order_status", "submitted")

                                return OrderResult(
                                    order_id=str(order_id),
                                    ticker=ticker,
                                    action=action,
                                    quantity=quantity,
                                    status=status,
                                )

            logger.error(f"Unexpected order response format: {response}")
            return None

        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None

    def get_open_orders(self) -> list[dict]:
        """Query all open orders from IBKR

        Endpoint: GET /iserver/account/orders

        Returns:
            List of order dictionaries with:
            - order_id: Order ID
            - ticker: Stock ticker
            - quantity: Number of shares
            - order_type: Order type (MKT, STP, etc.)
            - status: Order status
            - limit_price: Limit price (if applicable)
            - stop_price: Stop price (if applicable)

        Raises:
            RuntimeError: If not connected or request fails
        """
        if not self._connected:
            raise RuntimeError("Not connected - call connect() first")

        endpoint = "/iserver/account/orders"
        response = self._request("GET", endpoint)

        orders = []

        if isinstance(response, dict) and "orders" in response:
            orders_list = response["orders"]
        elif isinstance(response, list):
            orders_list = response
        else:
            logger.warning(f"Unexpected orders response format: {response}")
            return orders

        for order in orders_list:
            if isinstance(order, dict):
                order_dict = {
                    "order_id": order.get("orderId") or order.get("order_id"),
                    "ticker": order.get("ticker") or order.get("symbol"),
                    "quantity": order.get("totalSize") or order.get("quantity", 0),
                    "order_type": order.get("orderType"),
                    "status": order.get("status"),
                    "limit_price": order.get("price"),
                    "stop_price": order.get("auxPrice"),
                }
                orders.append(order_dict)

        return orders

    def cancel_order(self, order_id: str) -> bool:
        """Cancel specific order

        Endpoint: DELETE /iserver/account/{accountId}/order/{orderId}

        Args:
            order_id: Order ID to cancel

        Returns:
            True if cancellation successful, False otherwise

        Raises:
            RuntimeError: If not connected
        """
        if not self._connected:
            raise RuntimeError("Not connected - call connect() first")

        endpoint = f"/iserver/account/{self._account_id}/order/{order_id}"

        try:
            response = self._request("DELETE", endpoint)
            logger.info(f"Cancel order response: {response}")

            # IBKR may return various response formats
            if isinstance(response, dict):
                # Check for success indicators
                if response.get("msg") == "Order cancelled" or response.get("conid"):
                    logger.info(f"Order {order_id} cancelled successfully")
                    return True

            # If we got here without error, consider it successful
            logger.info(f"Order {order_id} cancellation submitted")
            return True

        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
