"""Interactive Brokers client using IBind (Client Portal API)"""

import os
from ibind import IbkrClient, QuestionType, make_order_request
from loguru import logger

from .ib_interface import IBInterface, MarketData, OrderResult


class IBIndClient(IBInterface):
    """IB client implementation using IBind for Client Portal API"""

    def __init__(
        self, base_url: str = "https://localhost:5000", paper_trading: bool = True
    ):
        """Initialize IBind client

        Args:
            base_url: Client Portal API base URL
            paper_trading: If True, enforce paper trading safety checks
        """
        # Check if OAuth credentials are available
        use_oauth = os.getenv("IBIND_USE_OAUTH", "").lower() == "true"

        if use_oauth:
            logger.info("Initializing IBind client with OAuth 1.0a authentication")
            # IBind reads OAuth config from environment variables:
            # IBIND_OAUTH1A_CONSUMER_KEY
            # IBIND_OAUTH1A_ACCESS_TOKEN
            # IBIND_OAUTH1A_ACCESS_TOKEN_SECRET
            # IBIND_OAUTH1A_SIGNATURE_KEY_FP
            # IBIND_OAUTH1A_ENCRYPTION_KEY_FP
            # IBIND_OAUTH1A_DH_PRIME
            self.client = IbkrClient(url=base_url)
        else:
            logger.info("Initializing IBind client with session-based authentication")
            self.client = IbkrClient(url=base_url)

        self.paper_trading = paper_trading
        self._connected = False
        self._account_id = None

    def connect(
        self, host: str, port: int, client_id: int, timeout: int = 20
    ) -> None:
        """Connect to Client Portal API via IBeam

        Note: Client Portal API uses session-based auth managed by IBeam,
        so traditional connect() is primarily a health check.

        Args:
            host: IBeam hostname (not used, client uses base_url from init)
            port: IBeam port (not used, client uses base_url from init)
            client_id: Client ID (not used for Client Portal API)
            timeout: Connection timeout (not used)

        Raises:
            ValueError: If connecting to wrong account type
            RuntimeError: If connection fails
        """
        try:
            # Check if gateway is authenticated and healthy
            logger.info("Checking Client Portal health...")
            health = self.client.check_health()
            if not health.ok:
                raise RuntimeError(
                    f"Client Portal not healthy: {health.error}"
                )

            # Tickle to verify session is authenticated
            logger.info("Verifying session authentication...")
            tickle = self.client.tickle()
            if not tickle.ok:
                raise RuntimeError(
                    "Session not authenticated. Please approve 2FA on your phone."
                )

            # Get accounts and verify paper trading
            logger.info("Retrieving account information...")
            accounts = self.client.portfolio_accounts()
            if not accounts.ok or not accounts.data:
                raise RuntimeError(
                    f"No accounts available: {accounts.error}"
                )

            self._account_id = accounts.data[0]["accountId"]
            logger.info(f"Connected to account: {self._account_id}")

            # CRITICAL: Verify paper trading account
            if self.paper_trading and not self._account_id.startswith("DU"):
                logger.error(
                    f"SAFETY CHECK FAILED: Expected paper account (DU prefix), got {self._account_id}"
                )
                raise ValueError("Not a paper trading account!")

            if self.paper_trading:
                logger.warning(
                    f"PAPER TRADING MODE - Account: {self._account_id}"
                )
            else:
                logger.warning(
                    f"LIVE TRADING MODE - Account: {self._account_id}"
                )

            self._connected = True
            logger.info("Client Portal connection established successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Client Portal: {e}")
            raise

    def is_connected(self) -> bool:
        """Check if connected to Client Portal

        Returns:
            True if connected and session is valid, False otherwise
        """
        if not self._connected:
            return False

        # Verify session is still valid
        try:
            tickle = self.client.tickle()
            return tickle.ok
        except Exception as e:
            logger.warning(f"Connection check failed: {e}")
            return False

    def place_order(
        self, ticker: str, action: str, quantity: int
    ) -> OrderResult | None:
        """Place market order via Client Portal API

        Args:
            ticker: Stock ticker symbol (e.g., "BHP")
            action: Order action ("BUY" or "SELL")
            quantity: Number of shares

        Returns:
            OrderResult object if order placed successfully, None otherwise
        """
        try:
            if not self._connected or not self._account_id:
                logger.error("Not connected to Client Portal")
                return None

            # Get contract ID for ticker
            logger.info(f"Looking up contract ID for {ticker}...")
            conid_response = self.client.stock_conid_by_symbol(ticker)
            if not conid_response.ok or not conid_response.data:
                logger.error(f"Could not find contract ID for {ticker}")
                return None

            conid = str(conid_response.data[0]["conid"])
            logger.info(f"Found contract ID {conid} for {ticker}")

            # Create order request
            order_request = make_order_request(
                conid=conid,
                side=action,
                quantity=quantity,
                order_type="MKT",
                acct_id=self._account_id,
                coid=f"skim_{ticker}_{action}_{quantity}",
            )

            # Auto-accept common order questions
            answers = {
                QuestionType.PRICE_PERCENTAGE_CONSTRAINT: True,
                QuestionType.ORDER_VALUE_LIMIT: True,
            }

            logger.info(
                f"Placing {action} order for {quantity} shares of {ticker}..."
            )
            response = self.client.place_order(
                order_request, answers, self._account_id
            )

            if not response.ok:
                logger.error(f"Order placement failed: {response.error}")
                return None

            # Extract order ID from response
            order_data = response.data
            if isinstance(order_data, list) and len(order_data) > 0:
                order_id = order_data[0].get("order_id", "unknown")
                status = order_data[0].get("order_status", "submitted")
            else:
                order_id = "unknown"
                status = "submitted"

            logger.info(
                f"Order placed successfully: {action} {quantity} {ticker} (ID: {order_id})"
            )

            return OrderResult(
                order_id=order_id,
                ticker=ticker,
                action=action,
                quantity=quantity,
                status=status,
            )

        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    def get_market_data(self, ticker: str) -> MarketData | None:
        """Get current market data for ticker

        Args:
            ticker: Stock ticker symbol (e.g., "BHP")

        Returns:
            MarketData object if data available, None otherwise
        """
        try:
            # Get contract ID for ticker
            conid_response = self.client.stock_conid_by_symbol(ticker)
            if not conid_response.ok or not conid_response.data:
                logger.error(f"Could not find contract ID for {ticker}")
                return None

            conid = conid_response.data[0]["conid"]

            # Get market data snapshot
            snapshot = self.client.marketdata_snapshot(conids=[conid])
            if not snapshot.ok or not snapshot.data:
                logger.error(f"Could not get market data for {ticker}")
                return None

            data = snapshot.data[0]

            # Extract market data fields
            last_price = float(data.get("31", 0))  # Last price
            bid = float(data.get("84", 0))  # Bid price
            ask = float(data.get("86", 0))  # Ask price
            volume = int(data.get("87", 0))  # Volume

            return MarketData(
                ticker=ticker,
                last_price=last_price,
                bid=bid,
                ask=ask,
                volume=volume,
            )

        except Exception as e:
            logger.error(f"Error getting market data for {ticker}: {e}")
            return None

    def disconnect(self) -> None:
        """Disconnect from Client Portal

        Note: Session is maintained by IBeam, so this just marks us as disconnected.
        """
        self._connected = False
        self._account_id = None
        logger.info("Disconnected from Client Portal")

    def get_account(self) -> str:
        """Get connected account ID

        Returns:
            Account ID string

        Raises:
            RuntimeError: If not connected
        """
        if not self._account_id:
            raise RuntimeError("Not connected - no account available")
        return self._account_id
