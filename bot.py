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
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from ib_insync import IB, Stock, MarketOrder, LimitOrder, util
import yfinance as yf
import pandas as pd
from loguru import logger

# Configuration from environment variables
IB_HOST = os.getenv('IB_HOST', 'ibgateway')
IB_PORT = int(os.getenv('IB_PORT', 4001))
IB_CLIENT_ID = int(os.getenv('IB_CLIENT_ID', 1))
PAPER_TRADING = os.getenv('PAPER_TRADING', 'true').lower() == 'true'
GAP_THRESHOLD = float(os.getenv('GAP_THRESHOLD', 3.0))  # 3% gap
MAX_POSITION_SIZE = int(os.getenv('MAX_POSITION_SIZE', 1000))  # Max shares per position
MAX_POSITIONS = int(os.getenv('MAX_POSITIONS', 5))  # Max concurrent positions
DB_PATH = os.getenv('DB_PATH', 'data/skim.db')


class TradingBot:
    """ASX Pivot Trading Bot - Mobile-optimized for iPhone deployment"""

    def __init__(self):
        """Initialize the trading bot with database and IB connection"""
        logger.info("Initializing Skim Trading Bot...")

        # Ensure data directory exists
        os.makedirs(os.path.dirname(DB_PATH) if os.path.dirname(DB_PATH) else 'data', exist_ok=True)

        # Initialize database
        self.db = sqlite3.connect(DB_PATH)
        self.db.row_factory = sqlite3.Row
        self._init_db()

        # Initialize IB connection
        self.ib = IB()
        self._connect_ib()

        # ASX top 200 tickers (simplified list - you can expand this)
        self.asx_universe = [
            'BHP.AX', 'CBA.AX', 'CSL.AX', 'NAB.AX', 'WBC.AX',
            'ANZ.AX', 'WES.AX', 'MQG.AX', 'WOW.AX', 'FMG.AX',
            'RIO.AX', 'WDS.AX', 'GMG.AX', 'TCL.AX', 'TLS.AX',
            'ALL.AX', 'WTC.AX', 'COL.AX', 'STO.AX', 'QBE.AX'
            # Add more ASX200 tickers as needed
        ]

        logger.info("Bot initialized successfully")

    def _init_db(self):
        """Initialize database schema with all required tables"""
        cursor = self.db.cursor()

        # Candidates table - stocks flagged for potential entry
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS candidates (
                ticker TEXT PRIMARY KEY,
                headline TEXT,
                scan_date TEXT,
                status TEXT DEFAULT 'watching',
                gap_percent REAL,
                prev_close REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Positions table - active and historical positions
        cursor.execute("""
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
        """)

        # Trades table - all executed trades
        cursor.execute("""
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
        """)

        self.db.commit()
        logger.info("Database schema initialized")

    def _connect_ib(self):
        """Connect to IB Gateway with safety checks and reconnection logic"""
        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                logger.info(f"Connecting to IB Gateway at {IB_HOST}:{IB_PORT} (attempt {attempt + 1}/{max_retries})")
                self.ib.connect(IB_HOST, IB_PORT, clientId=IB_CLIENT_ID, timeout=20)

                # Get account info for safety checks
                account = self.ib.managedAccounts()[0]
                logger.info(f"Connected to account: {account}")

                # CRITICAL: Verify paper trading account
                if PAPER_TRADING:
                    if not account.startswith('DU'):
                        logger.error(f"SAFETY CHECK FAILED: Expected paper account (DU prefix), got {account}")
                        raise ValueError("Not a paper trading account!")
                    logger.warning(f"PAPER TRADING MODE - Account: {account}")
                else:
                    logger.warning(f"LIVE TRADING MODE - Account: {account}")

                logger.info("IB connection established successfully")
                return

            except Exception as e:
                logger.error(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))
                else:
                    logger.error("Failed to connect to IB Gateway after all retries")
                    raise

    def _ensure_connection(self):
        """Ensure IB connection is alive, reconnect if needed"""
        if not self.ib.isConnected():
            logger.warning("IB connection lost, attempting to reconnect...")
            self._connect_ib()

    def scan(self):
        """Scan ASX universe for potential candidates"""
        logger.info("Starting market scan for candidates...")

        candidates_found = 0

        for ticker in self.asx_universe:
            try:
                # Download recent data
                stock = yf.Ticker(ticker)
                hist = stock.history(period='5d')

                if hist.empty or len(hist) < 2:
                    continue

                # Get latest close
                prev_close = hist['Close'].iloc[-1]

                # Check for volume spikes or price movement
                avg_volume = hist['Volume'].mean()
                latest_volume = hist['Volume'].iloc[-1]

                # Simple heuristic: volume spike or price movement
                if latest_volume > avg_volume * 1.5:
                    logger.info(f"{ticker}: Volume spike detected ({latest_volume:.0f} vs avg {avg_volume:.0f})")

                    # Check if already in candidates
                    cursor = self.db.cursor()
                    cursor.execute("SELECT ticker FROM candidates WHERE ticker = ? AND status = 'watching'", (ticker,))

                    if not cursor.fetchone():
                        # Add to candidates
                        cursor.execute("""
                            INSERT OR REPLACE INTO candidates (ticker, headline, scan_date, status, prev_close)
                            VALUES (?, ?, ?, 'watching', ?)
                        """, (ticker, "Volume spike detected", datetime.now().isoformat(), prev_close))
                        self.db.commit()
                        candidates_found += 1
                        logger.info(f"Added {ticker} to candidates")

            except Exception as e:
                logger.error(f"Error scanning {ticker}: {e}")
                continue

        logger.info(f"Scan complete. Found {candidates_found} new candidates")
        return candidates_found

    def monitor(self):
        """Monitor candidates for gap at market open"""
        logger.info("Monitoring candidates for gaps at market open...")

        cursor = self.db.cursor()
        cursor.execute("SELECT * FROM candidates WHERE status = 'watching'")
        candidates = cursor.fetchall()

        if not candidates:
            logger.info("No candidates to monitor")
            return

        gaps_found = 0

        for candidate in candidates:
            ticker = candidate['ticker']
            prev_close = candidate['prev_close']

            try:
                # Get current price
                stock = yf.Ticker(ticker)
                current_data = stock.history(period='1d', interval='1m')

                if current_data.empty:
                    continue

                current_price = current_data['Close'].iloc[-1]
                gap_percent = ((current_price - prev_close) / prev_close) * 100

                logger.info(f"{ticker}: Current price ${current_price:.2f}, Gap: {gap_percent:.2f}%")

                # Check for gap threshold
                if abs(gap_percent) >= GAP_THRESHOLD:
                    logger.warning(f"{ticker}: GAP DETECTED! {gap_percent:.2f}%")

                    # Update candidate status
                    cursor.execute("""
                        UPDATE candidates
                        SET status = 'triggered', gap_percent = ?
                        WHERE ticker = ?
                    """, (gap_percent, ticker))
                    self.db.commit()
                    gaps_found += 1

            except Exception as e:
                logger.error(f"Error monitoring {ticker}: {e}")
                continue

        logger.info(f"Monitoring complete. Found {gaps_found} gaps")
        return gaps_found

    def execute(self):
        """Execute orders for triggered candidates"""
        logger.info("Executing orders for triggered candidates...")

        self._ensure_connection()

        cursor = self.db.cursor()

        # Check how many open positions we have
        cursor.execute("SELECT COUNT(*) as count FROM positions WHERE status = 'open' OR status = 'half_exited'")
        position_count = cursor.fetchone()['count']

        if position_count >= MAX_POSITIONS:
            logger.warning(f"Maximum positions ({MAX_POSITIONS}) reached, skipping execution")
            return

        # Get triggered candidates
        cursor.execute("SELECT * FROM candidates WHERE status = 'triggered'")
        candidates = cursor.fetchall()

        if not candidates:
            logger.info("No triggered candidates to execute")
            return

        orders_placed = 0

        for candidate in candidates:
            ticker = candidate['ticker']

            try:
                # Convert ticker format (ASX uses different format in IB)
                # Remove .AX suffix for IB
                ib_ticker = ticker.replace('.AX', '')

                # Create stock contract
                contract = Stock(ib_ticker, 'ASX', 'AUD')
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
                quantity = min(int(position_value / current_price), MAX_POSITION_SIZE)

                if quantity < 1:
                    logger.warning(f"{ticker}: Calculated quantity too small")
                    continue

                # Calculate stop loss at low of day (simplified: -5% for now)
                stop_loss = current_price * 0.95

                # Place market order
                order = MarketOrder('BUY', quantity)
                trade = self.ib.placeOrder(contract, order)

                logger.info(f"Order placed: BUY {quantity} {ticker} @ market")

                # Wait for fill (with timeout)
                timeout = 30
                start_time = time.time()
                while not trade.isDone() and (time.time() - start_time) < timeout:
                    self.ib.sleep(1)

                if trade.isDone():
                    fill_price = trade.orderStatus.avgFillPrice
                    logger.info(f"Order filled: {quantity} {ticker} @ ${fill_price:.2f}")

                    # Record position
                    cursor.execute("""
                        INSERT INTO positions (ticker, quantity, entry_price, stop_loss, entry_date, status)
                        VALUES (?, ?, ?, ?, ?, 'open')
                    """, (ticker, quantity, fill_price, stop_loss, datetime.now().isoformat()))
                    position_id = cursor.lastrowid

                    # Record trade
                    cursor.execute("""
                        INSERT INTO trades (ticker, action, quantity, price, timestamp, position_id)
                        VALUES (?, 'BUY', ?, ?, ?, ?)
                    """, (ticker, quantity, fill_price, datetime.now().isoformat(), position_id))

                    # Update candidate status
                    cursor.execute("UPDATE candidates SET status = 'entered' WHERE ticker = ?", (ticker,))

                    self.db.commit()
                    orders_placed += 1
                else:
                    logger.warning(f"Order for {ticker} did not fill within timeout")

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
        cursor.execute("SELECT * FROM positions WHERE status IN ('open', 'half_exited')")
        positions = cursor.fetchall()

        if not positions:
            logger.info("No positions to manage")
            return

        actions_taken = 0

        for position in positions:
            ticker = position['ticker']
            position_id = position['id']
            entry_date = datetime.fromisoformat(position['entry_date'])
            days_held = (datetime.now() - entry_date).days

            try:
                # Get current price
                ib_ticker = ticker.replace('.AX', '')
                contract = Stock(ib_ticker, 'ASX', 'AUD')
                self.ib.qualifyContracts(contract)

                ticker_data = self.ib.reqMktData(contract)
                time.sleep(2)

                if not ticker_data.last or ticker_data.last <= 0:
                    logger.warning(f"{ticker}: No valid market data")
                    continue

                current_price = ticker_data.last

                # Rule 1: Sell half on day 3
                if days_held >= 3 and position['half_sold'] == 0:
                    quantity_to_sell = position['quantity'] // 2

                    if quantity_to_sell > 0:
                        order = MarketOrder('SELL', quantity_to_sell)
                        trade = self.ib.placeOrder(contract, order)

                        logger.info(f"Day 3: Selling half position {quantity_to_sell} {ticker}")

                        # Wait for fill
                        timeout = 30
                        start_time = time.time()
                        while not trade.isDone() and (time.time() - start_time) < timeout:
                            self.ib.sleep(1)

                        if trade.isDone():
                            fill_price = trade.orderStatus.avgFillPrice
                            pnl = (fill_price - position['entry_price']) * quantity_to_sell

                            logger.info(f"Half position sold: {quantity_to_sell} {ticker} @ ${fill_price:.2f}, PnL: ${pnl:.2f}")

                            # Update position
                            cursor.execute("""
                                UPDATE positions
                                SET half_sold = 1, status = 'half_exited'
                                WHERE id = ?
                            """, (position_id,))

                            # Record trade
                            cursor.execute("""
                                INSERT INTO trades (ticker, action, quantity, price, timestamp, position_id, pnl, notes)
                                VALUES (?, 'SELL', ?, ?, ?, ?, ?, 'Day 3 half exit')
                            """, (ticker, quantity_to_sell, fill_price, datetime.now().isoformat(), position_id, pnl))

                            self.db.commit()
                            actions_taken += 1

                # Rule 2: Check stop loss (low of day approximation)
                if current_price <= position['stop_loss']:
                    remaining_qty = position['quantity'] if position['half_sold'] == 0 else position['quantity'] // 2

                    order = MarketOrder('SELL', remaining_qty)
                    trade = self.ib.placeOrder(contract, order)

                    logger.warning(f"STOP LOSS HIT: Selling {remaining_qty} {ticker}")

                    # Wait for fill
                    timeout = 30
                    start_time = time.time()
                    while not trade.isDone() and (time.time() - start_time) < timeout:
                        self.ib.sleep(1)

                    if trade.isDone():
                        fill_price = trade.orderStatus.avgFillPrice
                        pnl = (fill_price - position['entry_price']) * remaining_qty

                        logger.info(f"Stop loss executed: ${fill_price:.2f}, PnL: ${pnl:.2f}")

                        # Close position
                        cursor.execute("""
                            UPDATE positions
                            SET status = 'closed', exit_date = ?, exit_price = ?
                            WHERE id = ?
                        """, (datetime.now().isoformat(), fill_price, position_id))

                        # Record trade
                        cursor.execute("""
                            INSERT INTO trades (ticker, action, quantity, price, timestamp, position_id, pnl, notes)
                            VALUES (?, 'SELL', ?, ?, ?, ?, ?, 'Stop loss')
                        """, (ticker, remaining_qty, fill_price, datetime.now().isoformat(), position_id, pnl))

                        self.db.commit()
                        actions_taken += 1

                # Rule 3: Trailing stop with 10-day SMA (simplified for now)
                # TODO: Implement 10-day SMA trailing stop

            except Exception as e:
                logger.error(f"Error managing position {ticker}: {e}")
                continue

        logger.info(f"Position management complete. {actions_taken} actions taken")
        return actions_taken

    def status(self):
        """Display current bot status and positions"""
        logger.info("=== SKIM BOT STATUS ===")

        cursor = self.db.cursor()

        # Candidates
        cursor.execute("SELECT COUNT(*) as count FROM candidates WHERE status = 'watching'")
        watching = cursor.fetchone()['count']
        logger.info(f"Watching candidates: {watching}")

        # Positions
        cursor.execute("SELECT COUNT(*) as count FROM positions WHERE status = 'open' OR status = 'half_exited'")
        open_positions = cursor.fetchone()['count']
        logger.info(f"Open positions: {open_positions}")

        # Display open positions
        cursor.execute("SELECT * FROM positions WHERE status IN ('open', 'half_exited')")
        positions = cursor.fetchall()

        for pos in positions:
            logger.info(f"  {pos['ticker']}: {pos['quantity']} shares @ ${pos['entry_price']:.2f} ({pos['status']})")

        # Total PnL
        cursor.execute("SELECT SUM(pnl) as total_pnl FROM trades WHERE pnl IS NOT NULL")
        result = cursor.fetchone()
        total_pnl = result['total_pnl'] if result['total_pnl'] else 0.0
        logger.info(f"Total PnL: ${total_pnl:.2f}")

        logger.info("=====================")

    def run(self):
        """Main orchestration - run all workflows"""
        logger.info("Running full trading workflow...")

        try:
            self.scan()
            self.monitor()
            self.execute()
            self.manage_positions()
            self.status()

            logger.info("Workflow complete")

        except Exception as e:
            logger.error(f"Error in workflow: {e}")
        finally:
            # Cleanup
            if self.ib.isConnected():
                self.ib.disconnect()
            self.db.close()


if __name__ == '__main__':
    # Setup logging
    logger.add(
        "logs/skim_{time}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO"
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
            logger.info("Available methods: scan, monitor, execute, manage_positions, status, run")
    else:
        # No argument - run full workflow
        bot.run()
