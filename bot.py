#!/usr/bin/env python3
"""
Skim - ASX Pivot Trading Bot
iPhone-optimized indie trading system for paper trading on Interactive Brokers

Strategy:
1. Scan ASX for price-sensitive announcements
2. Monitor opening auction for gaps >3%
3. Enter on breakout above opening range high
4. Stop loss at low of day
5. Sell half position on day 3
6. Trail remaining with 10-day SMA
"""

import os
import sqlite3
import time
from datetime import datetime

import requests
from bs4 import BeautifulSoup
from ib_insync import IB, MarketOrder, Stock
from loguru import logger

# Configuration from environment variables
IB_HOST = os.getenv("IB_HOST", "ibgateway")
IB_PORT = int(os.getenv("IB_PORT", "4004"))
IB_CLIENT_ID = int(os.getenv("IB_CLIENT_ID", "1"))
PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"
GAP_THRESHOLD = float(os.getenv("GAP_THRESHOLD", "3.0"))  # 3% gap
MAX_POSITION_SIZE = int(
    os.getenv("MAX_POSITION_SIZE", "1000")
)  # Max shares per position
MAX_POSITIONS = int(os.getenv("MAX_POSITIONS", "5"))  # Max concurrent positions
DB_PATH = os.getenv("DB_PATH", "data/skim.db")


class TradingBot:
    """ASX Pivot Trading Bot - Mobile-optimized for iPhone deployment"""

    def __init__(self):
        """Initialize the trading bot with database (lazy IB connection)"""
        logger.info("Initializing Skim Trading Bot...")

        # Ensure data directory exists
        os.makedirs(
            os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else "data",
            exist_ok=True,
        )

        # Initialize database
        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
        self._init_db()

        # Initialize IB connection object (lazy connection)
        self.ib = IB()
        self._ib_connected = False

        # TradingView API endpoint
        self.tv_api_url = "https://scanner.tradingview.com/australia/scan"

        logger.info("Bot initialized successfully")

    def _init_db(self):
        """Initialize database schema with all required tables"""
        cursor = self.db.cursor()

        # Candidates table - stocks flagged for potential entry
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                ticker TEXT PRIMARY KEY,
                headline TEXT,
                scan_date TEXT,
                status TEXT DEFAULT 'watching',
                gap_percent REAL,
                prev_close REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Positions table - active and historical positions
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                stop_loss REAL NOT NULL,
                entry_date TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                half_sold INTEGER DEFAULT 0,
                exit_date TEXT,
                exit_price REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        # Trades table - all executed trades
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                price REAL NOT NULL,
                timestamp TEXT NOT NULL,
                position_id INTEGER,
                pnl REAL,
                notes TEXT,
                FOREIGN KEY (position_id) REFERENCES positions(id)
            )
        """
        )

        self.db.commit()
        logger.info("Database schema initialized")

    def _test_network_connectivity(self):
        """Test network connectivity to IB Gateway before attempting connection"""
        import socket

        try:
            logger.info(
                f"Testing network connectivity to {IB_HOST}:{IB_PORT}..."
            )

            # Test DNS resolution
            ip_address = socket.gethostbyname(IB_HOST)
            logger.info(f"DNS resolved {IB_HOST} -> {ip_address}")

            # Test TCP connection
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((IB_HOST, IB_PORT))
            sock.close()

            if result == 0:
                logger.info(f"TCP connection to {IB_HOST}:{IB_PORT} successful")
                return True
            else:
                logger.warning(
                    f"TCP connection to {IB_HOST}:{IB_PORT} failed (error code: {result})"
                )
                return False

        except socket.gaierror as e:
            logger.error(f"DNS resolution failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Network test failed: {e}")
            return False

    def _connect_ib(self):
        """Connect to IB Gateway with safety checks and reconnection logic"""
        if self._ib_connected and self.ib.isConnected():
            return

        max_retries = 10
        retry_delay = 5
        connection_timeout = 20  # Reduced from 60 to fail faster

        for attempt in range(max_retries):
            try:
                # Test network connectivity first
                if not self._test_network_connectivity():
                    logger.warning(
                        "Network connectivity test failed, waiting before retry..."
                    )
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue

                logger.info(
                    f"Connecting to IB Gateway at {IB_HOST}:{IB_PORT} (attempt {attempt + 1}/{max_retries})"
                )
                logger.info(
                    f"Using clientId={IB_CLIENT_ID}, timeout={connection_timeout}s"
                )

                self.ib.connect(
                    IB_HOST,
                    IB_PORT,
                    clientId=IB_CLIENT_ID,
                    timeout=connection_timeout,
                )

                # Get account info for safety checks
                account = self.ib.managedAccounts()[0]
                logger.info(f"Connected to account: {account}")

                # CRITICAL: Verify paper trading account
                if PAPER_TRADING:
                    if not account.startswith("DU"):
                        logger.error(
                            f"SAFETY CHECK FAILED: Expected paper account (DU prefix), got {account}"
                        )
                        raise ValueError("Not a paper trading account!")
                    logger.warning(f"PAPER TRADING MODE - Account: {account}")
                else:
                    logger.warning(f"LIVE TRADING MODE - Account: {account}")

                logger.info("IB connection established successfully")
                self._ib_connected = True
                return

            except Exception as e:
                error_msg = str(e)
                logger.error(
                    f"Connection attempt {attempt + 1} failed: {error_msg}"
                )

                # Check for specific error conditions that won't resolve with retries
                if "clientid already in use" in error_msg.lower():
                    logger.error(
                        "Client ID already in use. Try changing IB_CLIENT_ID environment variable."
                    )
                    raise
                elif "not connected" in error_msg.lower():
                    logger.warning(
                        "IB Gateway may not be accepting connections yet"
                    )

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
                    raise

    def _ensure_connection(self):
        """Ensure IB connection is alive, reconnect if needed"""
        if not self._ib_connected or not self.ib.isConnected():
            logger.warning(
                "IB connection not established or lost, connecting..."
            )
            self._connect_ib()

    def _query_tradingview(
        self, min_gap: float
    ) -> list[tuple[str, float, float]]:
        """
        Query TradingView scanner API for ASX stocks with gaps

        Args:
            min_gap: Minimum gap percentage (change_from_open)

        Returns:
            List of tuples: (ticker, gap_percent, close_price)
        """
        try:
            # TradingView API payload
            payload = {
                "markets": ["australia"],
                "symbols": {"query": {"types": []}, "tickers": []},
                "options": {"lang": "en"},
                "columns": ["name", "close", "change_from_open"],
                "sort": {"sortBy": "change_from_open", "sortOrder": "desc"},
                "range": [0, 100],
                "filter": [
                    {
                        "left": "change_from_open",
                        "operation": "greater",
                        "right": min_gap,
                    }
                ],
            }

            # Headers to mimic browser request
            headers = {
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "origin": "https://www.tradingview.com",
                "referer": "https://www.tradingview.com/",
                "accept": "text/plain, */*; q=0.01",
                "sec-fetch-site": "same-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
            }

            logger.info(f"Querying TradingView for gaps > {min_gap}%")

            response = requests.post(
                self.tv_api_url, json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()

            data = response.json()

            results = []
            for item in data.get("data", []):
                ticker = item.get("s", "")  # Symbol like "ASX:BHP"
                values = item.get("d", [])

                if len(values) >= 3:
                    # Extract ticker name (remove ASX: prefix)
                    ticker_name = ticker.replace("ASX:", "")
                    close_price = float(values[1]) if values[1] else 0.0
                    gap_percent = float(values[2]) if values[2] else 0.0

                    results.append((ticker_name, gap_percent, close_price))

            logger.info(
                f"TradingView returned {len(results)} stocks with gaps > {min_gap}%"
            )
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying TradingView API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying TradingView: {e}")
            return []

    def _fetch_price_sensitive_announcements(self) -> set[str]:
        """
        Fetch today's price-sensitive announcements from ASX

        Returns:
            Set of ticker symbols with price-sensitive announcements today
        """
        try:
            asx_url = "https://www.asx.com.au/asx/v2/statistics/todayAnns.do"
            logger.info("Fetching price-sensitive announcements from ASX...")

            response = requests.get(asx_url, timeout=10)
            response.raise_for_status()

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, "lxml")

            # Find all table rows
            rows = soup.find_all("tr")

            price_sensitive_tickers = set()

            for row in rows:
                # Check if row contains "pricesens" indicator
                if "pricesens" in str(row):
                    # Extract ticker from first <td> element
                    cells = row.find_all("td")
                    if cells:
                        ticker = cells[0].get_text(strip=True)
                        if ticker:
                            price_sensitive_tickers.add(ticker)

            logger.info(
                f"Found {len(price_sensitive_tickers)} price-sensitive announcements today"
            )
            return price_sensitive_tickers

        except requests.exceptions.Timeout:
            logger.warning(
                "ASX announcement fetch timed out, continuing without filter"
            )
            return set()
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Error fetching ASX announcements: {e}, continuing without filter"
            )
            return set()
        except Exception as e:
            logger.warning(
                f"Unexpected error parsing ASX announcements: {e}, continuing without filter"
            )
            return set()

    def scan(self):
        """Scan ASX market for stocks showing momentum (gaps > 2%) and price-sensitive announcements"""
        logger.info("Starting TradingView market scan for candidates...")

        # Fetch price-sensitive announcements first
        price_sensitive_tickers = self._fetch_price_sensitive_announcements()

        # Query TradingView for stocks with gaps > 2% (lower threshold for scanning)
        scan_threshold = 2.0
        stocks = self._query_tradingview(min_gap=scan_threshold)

        if not stocks:
            logger.info("No stocks found in scan")
            return 0

        candidates_found = 0
        cursor = self.db.cursor()

        for ticker, gap_percent, close_price in stocks:
            # Only process if ticker has price-sensitive announcement
            if ticker not in price_sensitive_tickers:
                logger.debug(
                    f"{ticker}: Skipped (no price-sensitive announcement)"
                )
                continue

            try:
                logger.info(
                    f"{ticker}: Gap {gap_percent:.2f}% @ ${close_price:.2f}"
                )

                # Check if already in candidates
                cursor.execute(
                    "SELECT ticker FROM candidates WHERE ticker = ? AND status = 'watching'",
                    (ticker,),
                )

                if not cursor.fetchone():
                    # Add to candidates
                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO candidates (ticker, headline, scan_date, status, gap_percent, prev_close)
                        VALUES (?, ?, ?, 'watching', ?, ?)
                    """,
                        (
                            ticker,
                            f"Gap detected: {gap_percent:.2f}%",
                            datetime.now().isoformat(),
                            gap_percent,
                            close_price,
                        ),
                    )
                    self.db.commit()
                    candidates_found += 1
                    logger.info(
                        f"Added {ticker} to candidates (gap: {gap_percent:.2f}%, price-sensitive announcement)"
                    )

            except Exception as e:
                logger.error(f"Error adding candidate {ticker}: {e}")
                continue

        logger.info(
            f"Scan complete. Found {candidates_found} new candidates with both momentum and announcements"
        )
        return candidates_found

    def monitor(self):
        """Monitor candidates and trigger on gap threshold"""
        logger.info("Monitoring for gaps at market open...")

        # Query TradingView for stocks with gaps >= threshold
        stocks = self._query_tradingview(min_gap=GAP_THRESHOLD)

        if not stocks:
            logger.info("No stocks meeting gap threshold")
            return 0

        cursor = self.db.cursor()
        gaps_found = 0

        # Get existing candidates
        cursor.execute("SELECT * FROM candidates WHERE status = 'watching'")
        candidates = cursor.fetchall()
        candidate_tickers = {c["ticker"] for c in candidates}

        for ticker, gap_percent, close_price in stocks:
            try:
                logger.info(
                    f"{ticker}: Gap {gap_percent:.2f}% @ ${close_price:.2f}"
                )

                # Check if this ticker is in our candidates
                if ticker in candidate_tickers:
                    # Trigger existing candidate
                    logger.warning(
                        f"{ticker}: CANDIDATE TRIGGERED! Gap: {gap_percent:.2f}%"
                    )

                    cursor.execute(
                        """
                        UPDATE candidates
                        SET status = 'triggered', gap_percent = ?
                        WHERE ticker = ? AND status = 'watching'
                    """,
                        (gap_percent, ticker),
                    )
                    self.db.commit()
                    gaps_found += 1
                else:
                    # New stock meeting threshold - add directly as triggered
                    logger.warning(
                        f"{ticker}: NEW STOCK TRIGGERED! Gap: {gap_percent:.2f}%"
                    )

                    cursor.execute(
                        """
                        INSERT OR REPLACE INTO candidates (ticker, headline, scan_date, status, gap_percent, prev_close)
                        VALUES (?, ?, ?, 'triggered', ?, ?)
                    """,
                        (
                            ticker,
                            f"Gap triggered: {gap_percent:.2f}%",
                            datetime.now().isoformat(),
                            gap_percent,
                            close_price,
                        ),
                    )
                    self.db.commit()
                    gaps_found += 1

            except Exception as e:
                logger.error(f"Error monitoring {ticker}: {e}")
                continue

        logger.info(f"Monitoring complete. Found {gaps_found} triggered stocks")
        return gaps_found

    def execute(self):
        """Execute orders for triggered candidates"""
        logger.info("Executing orders for triggered candidates...")

        self._ensure_connection()

        cursor = self.db.cursor()

        # Check how many open positions we have
        cursor.execute(
            "SELECT COUNT(*) as count FROM positions WHERE status = 'open' OR status = 'half_exited'"
        )
        position_count = cursor.fetchone()["count"]

        if position_count >= MAX_POSITIONS:
            logger.warning(
                f"Maximum positions ({MAX_POSITIONS}) reached, skipping execution"
            )
            return

        # Get triggered candidates
        cursor.execute("SELECT * FROM candidates WHERE status = 'triggered'")
        candidates = cursor.fetchall()

        if not candidates:
            logger.info("No triggered candidates to execute")
            return

        orders_placed = 0

        for candidate in candidates:
            ticker = candidate["ticker"]

            try:
                # TradingView returns ticker without suffix (e.g., "BHP")
                # IB uses same format for ASX stocks
                ib_ticker = ticker

                # Create stock contract
                contract = Stock(ib_ticker, "ASX", "AUD")
                self.ib.qualifyContracts(contract)

                # Get current market price
                ticker_data = self.ib.reqMktData(contract)
                time.sleep(2)  # Wait for data

                if not ticker_data.last or ticker_data.last <= 0:
                    logger.warning(f"{ticker}: No valid market data available")
                    continue

                current_price = ticker_data.last

                # Calculate position size (simple: fixed dollar amount)
                position_value = 5000  # $5000 per position
                quantity = min(
                    int(position_value / current_price), MAX_POSITION_SIZE
                )

                if quantity < 1:
                    logger.warning(f"{ticker}: Calculated quantity too small")
                    continue

                # Calculate stop loss at low of day (simplified: -5% for now)
                stop_loss = current_price * 0.95

                # Place market order
                order = MarketOrder("BUY", quantity)
                trade = self.ib.placeOrder(contract, order)

                logger.info(f"Order placed: BUY {quantity} {ticker} @ market")

                # Wait for fill (with timeout)
                timeout = 30
                start_time = time.time()
                while (
                    not trade.isDone() and (time.time() - start_time) < timeout
                ):
                    self.ib.sleep(1)

                if trade.isDone():
                    fill_price = trade.orderStatus.avgFillPrice
                    logger.info(
                        f"Order filled: {quantity} {ticker} @ ${fill_price:.2f}"
                    )

                    # Record position
                    cursor.execute(
                        """
                        INSERT INTO positions (ticker, quantity, entry_price, stop_loss, entry_date, status)
                        VALUES (?, ?, ?, ?, ?, 'open')
                    """,
                        (
                            ticker,
                            quantity,
                            fill_price,
                            stop_loss,
                            datetime.now().isoformat(),
                        ),
                    )
                    position_id = cursor.lastrowid

                    # Record trade
                    cursor.execute(
                        """
                        INSERT INTO trades (ticker, action, quantity, price, timestamp, position_id)
                        VALUES (?, 'BUY', ?, ?, ?, ?)
                    """,
                        (
                            ticker,
                            quantity,
                            fill_price,
                            datetime.now().isoformat(),
                            position_id,
                        ),
                    )

                    # Update candidate status
                    cursor.execute(
                        "UPDATE candidates SET status = 'entered' WHERE ticker = ?",
                        (ticker,),
                    )

                    self.db.commit()
                    orders_placed += 1
                else:
                    logger.warning(
                        f"Order for {ticker} did not fill within timeout"
                    )

            except Exception as e:
                logger.error(f"Error executing order for {ticker}: {e}")
                continue

        logger.info(f"Execution complete. Placed {orders_placed} orders")
        return orders_placed

    def manage_positions(self):
        """Manage existing positions (Day 3 exit, trailing stops)"""
        logger.info("Managing existing positions...")

        self._ensure_connection()

        cursor = self.db.cursor()
        cursor.execute(
            "SELECT * FROM positions WHERE status IN ('open', 'half_exited')"
        )
        positions = cursor.fetchall()

        if not positions:
            logger.info("No positions to manage")
            return

        actions_taken = 0

        for position in positions:
            ticker = position["ticker"]
            position_id = position["id"]
            entry_date = datetime.fromisoformat(position["entry_date"])
            days_held = (datetime.now() - entry_date).days

            try:
                # Get current price (ticker already in IB format from TradingView)
                ib_ticker = ticker
                contract = Stock(ib_ticker, "ASX", "AUD")
                self.ib.qualifyContracts(contract)

                ticker_data = self.ib.reqMktData(contract)
                time.sleep(2)

                if not ticker_data.last or ticker_data.last <= 0:
                    logger.warning(f"{ticker}: No valid market data")
                    continue

                current_price = ticker_data.last

                # Rule 1: Sell half on day 3
                if days_held >= 3 and position["half_sold"] == 0:
                    quantity_to_sell = position["quantity"] // 2

                    if quantity_to_sell > 0:
                        order = MarketOrder("SELL", quantity_to_sell)
                        trade = self.ib.placeOrder(contract, order)

                        logger.info(
                            f"Day 3: Selling half position {quantity_to_sell} {ticker}"
                        )

                        # Wait for fill
                        timeout = 30
                        start_time = time.time()
                        while (
                            not trade.isDone()
                            and (time.time() - start_time) < timeout
                        ):
                            self.ib.sleep(1)

                        if trade.isDone():
                            fill_price = trade.orderStatus.avgFillPrice
                            pnl = (
                                fill_price - position["entry_price"]
                            ) * quantity_to_sell

                            logger.info(
                                f"Half position sold: {quantity_to_sell} {ticker} @ ${fill_price:.2f}, PnL: ${pnl:.2f}"
                            )

                            # Update position
                            cursor.execute(
                                """
                                UPDATE positions
                                SET half_sold = 1, status = 'half_exited'
                                WHERE id = ?
                            """,
                                (position_id,),
                            )

                            # Record trade
                            cursor.execute(
                                """
                                INSERT INTO trades (ticker, action, quantity, price, timestamp, position_id, pnl, notes)
                                VALUES (?, 'SELL', ?, ?, ?, ?, ?, 'Day 3 half exit')
                            """,
                                (
                                    ticker,
                                    quantity_to_sell,
                                    fill_price,
                                    datetime.now().isoformat(),
                                    position_id,
                                    pnl,
                                ),
                            )

                            self.db.commit()
                            actions_taken += 1

                # Rule 2: Check stop loss (low of day approximation)
                if current_price <= position["stop_loss"]:
                    remaining_qty = (
                        position["quantity"]
                        if position["half_sold"] == 0
                        else position["quantity"] // 2
                    )

                    order = MarketOrder("SELL", remaining_qty)
                    trade = self.ib.placeOrder(contract, order)

                    logger.warning(
                        f"STOP LOSS HIT: Selling {remaining_qty} {ticker}"
                    )

                    # Wait for fill
                    timeout = 30
                    start_time = time.time()
                    while (
                        not trade.isDone()
                        and (time.time() - start_time) < timeout
                    ):
                        self.ib.sleep(1)

                    if trade.isDone():
                        fill_price = trade.orderStatus.avgFillPrice
                        pnl = (
                            fill_price - position["entry_price"]
                        ) * remaining_qty

                        logger.info(
                            f"Stop loss executed: ${fill_price:.2f}, PnL: ${pnl:.2f}"
                        )

                        # Close position
                        cursor.execute(
                            """
                            UPDATE positions
                            SET status = 'closed', exit_date = ?, exit_price = ?
                            WHERE id = ?
                        """,
                            (
                                datetime.now().isoformat(),
                                fill_price,
                                position_id,
                            ),
                        )

                        # Record trade
                        cursor.execute(
                            """
                            INSERT INTO trades (ticker, action, quantity, price, timestamp, position_id, pnl, notes)
                            VALUES (?, 'SELL', ?, ?, ?, ?, ?, 'Stop loss')
                        """,
                            (
                                ticker,
                                remaining_qty,
                                fill_price,
                                datetime.now().isoformat(),
                                position_id,
                                pnl,
                            ),
                        )

                        self.db.commit()
                        actions_taken += 1

                # Rule 3: Trailing stop with 10-day SMA (simplified for now)
                # TODO: Implement 10-day SMA trailing stop

            except Exception as e:
                logger.error(f"Error managing position {ticker}: {e}")
                continue

        logger.info(
            f"Position management complete. {actions_taken} actions taken"
        )
        return actions_taken

    def status(self):
        """Display current bot status and positions"""
        logger.info("=== SKIM BOT STATUS ===")

        cursor = self.db.cursor()

        # Candidates
        cursor.execute(
            "SELECT COUNT(*) as count FROM candidates WHERE status = 'watching'"
        )
        watching = cursor.fetchone()["count"]
        logger.info(f"Watching candidates: {watching}")

        # Positions
        cursor.execute(
            "SELECT COUNT(*) as count FROM positions WHERE status = 'open' OR status = 'half_exited'"
        )
        open_positions = cursor.fetchone()["count"]
        logger.info(f"Open positions: {open_positions}")

        # Display open positions
        cursor.execute(
            "SELECT * FROM positions WHERE status IN ('open', 'half_exited')"
        )
        positions = cursor.fetchall()

        for pos in positions:
            logger.info(
                f"  {pos['ticker']}: {pos['quantity']} shares @ ${pos['entry_price']:.2f} ({pos['status']})"
            )

        # Total PnL
        cursor.execute(
            "SELECT SUM(pnl) as total_pnl FROM trades WHERE pnl IS NOT NULL"
        )
        result = cursor.fetchone()
        total_pnl = result["total_pnl"] if result["total_pnl"] else 0.0
        logger.info(f"Total PnL: ${total_pnl:.2f}")

        logger.info("=====================")

    def run(self):
        """Main orchestration - run all workflows"""
        logger.info("Running full trading workflow...")

        try:
            self.scan()
            self.monitor()
            # Only execute if we can connect to IB
            try:
                self.execute()
                self.manage_positions()
            except Exception as e:
                logger.error(
                    f"Skipping trading operations due to IB connection issue: {e}"
                )
            self.status()

            logger.info("Workflow complete")

        except Exception as e:
            logger.error(f"Error in workflow: {e}")
        finally:
            # Cleanup
            if self.ib.isConnected():
                self.ib.disconnect()
            self.db.close()


if __name__ == "__main__":
    # Setup logging
    logger.add(
        "logs/skim_{time}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
    )

    logger.info("=" * 60)
    logger.info("SKIM TRADING BOT - ASX PIVOT STRATEGY")
    logger.info("=" * 60)

    # Run based on command line argument
    import sys

    bot = TradingBot()

    if len(sys.argv) > 1:
        method = sys.argv[1]
        if hasattr(bot, method) and callable(getattr(bot, method)):
            logger.info(f"Executing method: {method}")
            getattr(bot, method)()
        else:
            logger.error(f"Unknown method: {method}")
            logger.info(
                "Available methods: scan, monitor, execute, manage_positions, status, run"
            )
    else:
        # No argument - run full workflow
        bot.run()
