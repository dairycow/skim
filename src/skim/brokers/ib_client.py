"""Interactive Brokers client implementation"""

import socket
import time

from ib_insync import IB, MarketOrder, Stock, Trade
from loguru import logger

from .ib_interface import MarketData


class IBClient:
    """Interactive Brokers client with connection management and order execution"""

    def __init__(self, paper_trading: bool = True):
        """Initialize IB client

        Args:
            paper_trading: If True, enforce paper trading safety checks
        """
        self.ib = IB()
        self.paper_trading = paper_trading
        self._connected = False

    def connect(
        self, host: str, port: int, client_id: int, timeout: int = 20
    ) -> None:
        """Connect to IB Gateway with safety checks and reconnection logic

        Args:
            host: IB Gateway hostname or IP
            port: IB Gateway port
            client_id: Unique client ID
            timeout: Connection timeout in seconds

        Raises:
            ValueError: If connecting to wrong account type (e.g., live when expecting paper)
            RuntimeError: If connection fails after maximum retries
        """
        if self._connected and self.ib.isConnected():
            return

        max_retries = 10
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                # Test network connectivity first
                if not self._test_network_connectivity(host, port):
                    logger.warning(
                        "Network connectivity test failed, waiting before retry..."
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue

                logger.info(
                    f"Connecting to IB Gateway at {host}:{port} (attempt {attempt + 1}/{max_retries})"
                )
                logger.info(f"Using clientId={client_id}, timeout={timeout}s")

                self.ib.connect(
                    host,
                    port,
                    clientId=client_id,
                    timeout=timeout,
                )

                # Get account info for safety checks
                account = self.ib.managedAccounts()[0]
                logger.info(f"Connected to account: {account}")

                # CRITICAL: Verify paper trading account
                if self.paper_trading:
                    if not account.startswith("DU"):
                        logger.error(
                            f"SAFETY CHECK FAILED: Expected paper account (DU prefix), got {account}"
                        )
                        raise ValueError("Not a paper trading account!")
                    logger.warning(f"PAPER TRADING MODE - Account: {account}")
                else:
                    logger.warning(f"LIVE TRADING MODE - Account: {account}")

                logger.info("IB connection established successfully")
                self._connected = True
                return

            except Exception as e:
                error_msg = str(e)
                logger.error(f"Connection attempt {attempt + 1} failed: {error_msg}")

                # Check for specific error conditions that won't resolve with retries
                if "clientid already in use" in error_msg.lower():
                    logger.error(
                        "Client ID already in use. Try changing IB_CLIENT_ID environment variable."
                    )
                    raise
                elif "not connected" in error_msg.lower():
                    logger.warning("IB Gateway may not be accepting connections yet")

                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Failed to connect to IB Gateway after {max_retries} retries"
                    )
                    logger.error("Possible issues:")
                    logger.error(
                        "1. IB Gateway may not be fully started (check: docker logs ibgateway)"
                    )
                    logger.error("2. Trusted IPs not configured in jts.ini")
                    logger.error("3. Wrong credentials or 2FA timeout")
                    logger.error("4. Client ID already in use")
                    raise RuntimeError(
                        f"Failed to connect to IB Gateway after {max_retries} retries"
                    ) from e

    def _test_network_connectivity(self, host: str, port: int) -> bool:
        """Test network connectivity to IB Gateway before attempting connection

        Args:
            host: IB Gateway hostname or IP
            port: IB Gateway port

        Returns:
            True if network connectivity is successful, False otherwise
        """
        try:
            logger.info(f"Testing network connectivity to {host}:{port}...")

            # Test DNS resolution
            ip_address = socket.gethostbyname(host)
            logger.info(f"DNS resolved {host} -> {ip_address}")

            # Test TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                logger.info(f"TCP connection to {host}:{port} successful")
                return True
            else:
                logger.warning(
                    f"TCP connection to {host}:{port} failed (error code: {result})"
                )
                return False

        except socket.gaierror as e:
            logger.error(f"DNS resolution failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Network test failed: {e}")
            return False

    def ensure_connection(self) -> None:
        """Ensure IB connection is alive, reconnect if needed

        This method should be called before performing any IB operations
        to ensure the connection is healthy.
        """
        if not self._connected or not self.ib.isConnected():
            logger.warning("IB connection not established or lost, connecting...")
            # Note: This will fail if connect() was never called with proper parameters
            # In production, connection parameters should be stored and reused
            raise RuntimeError(
                "Connection lost and cannot reconnect without connection parameters"
            )

    def is_connected(self) -> bool:
        """Check if connected to IB Gateway

        Returns:
            True if connected, False otherwise
        """
        return self._connected and self.ib.isConnected()

    def place_order(
        self, ticker: str, action: str, quantity: int, wait_for_fill: bool = True
    ) -> Trade | None:
        """Place a market order

        Args:
            ticker: Stock ticker symbol (e.g., "BHP")
            action: Order action ("BUY" or "SELL")
            quantity: Number of shares
            wait_for_fill: If True, wait up to 30 seconds for order to fill

        Returns:
            Trade object if order placed successfully, None otherwise
        """
        try:
            # Create ASX stock contract
            contract = Stock(ticker, "ASX", "AUD")
            self.ib.qualifyContracts(contract)

            # Create market order
            order = MarketOrder(action, quantity)
            trade = self.ib.placeOrder(contract, order)

            logger.info(f"Order placed: {action} {quantity} {ticker} @ market")

            # Wait for fill if requested
            if wait_for_fill:
                timeout = 30
                start_time = time.time()
                while not trade.isDone() and (time.time() - start_time) < timeout:
                    self.ib.sleep(1)

                if trade.isDone():
                    fill_price = trade.orderStatus.avgFillPrice
                    logger.info(
                        f"Order filled: {action} {quantity} {ticker} @ ${fill_price:.2f}"
                    )
                else:
                    logger.warning(
                        f"Order timeout: {action} {quantity} {ticker} (status: {trade.orderStatus.status})"
                    )

            return trade

        except Exception as e:
            logger.error(f"Error placing order for {ticker}: {e}")
            return None

    def get_market_data(self, ticker: str) -> MarketData | None:
        """Get current market data for a ticker

        Args:
            ticker: Stock ticker symbol (e.g., "BHP")

        Returns:
            MarketData object if data available, None otherwise
        """
        try:
            # Create ASX stock contract
            contract = Stock(ticker, "ASX", "AUD")
            self.ib.qualifyContracts(contract)

            # Request market data
            ticker_data = self.ib.reqMktData(contract)
            time.sleep(2)  # Wait for data to arrive

            if not ticker_data.last or ticker_data.last <= 0:
                logger.warning(f"{ticker}: No valid market data available")
                return None

            return MarketData(
                ticker=ticker,
                last_price=ticker_data.last,
                contract=contract,
            )

        except Exception as e:
            logger.error(f"Error getting market data for {ticker}: {e}")
            return None

    def disconnect(self) -> None:
        """Disconnect from IB Gateway"""
        if self.ib.isConnected():
            self.ib.disconnect()
            self._connected = False
            logger.info("Disconnected from IB Gateway")

    def get_account(self) -> str:
        """Get the connected account ID

        Returns:
            Account ID string

        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to IB Gateway")

        accounts = self.ib.managedAccounts()
        if not accounts:
            raise RuntimeError("No managed accounts found")

        return accounts[0]
