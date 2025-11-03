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

import sys
import time
from datetime import datetime

from loguru import logger

from skim.brokers import IBIndClient
from skim.core.config import Config
from skim.data.database import Database
from skim.data.models import Candidate
from skim.scanners.asx_announcements import ASXAnnouncementScanner
from skim.scanners.tradingview import TradingViewScanner


class TradingBot:
    """ASX Pivot Trading Bot - Mobile-optimized for iPhone deployment"""

    def __init__(self, config: Config):
        """Initialize the trading bot with configuration

        Args:
            config: Configuration object with all settings
        """
        logger.info("Initializing Skim Trading Bot...")

        self.config = config

        # Initialize database
        self.db = Database(config.db_path)

        # Initialize scanners
        self.tv_scanner = TradingViewScanner()
        self.asx_scanner = ASXAnnouncementScanner()

        # Initialize IB client (lazy connection)
        base_url = f"https://{config.ib_host}:{config.ib_port}"
        self.ib_client = IBIndClient(base_url=base_url, paper_trading=config.paper_trading)

        logger.info("Bot initialized successfully")

    def _connect_ib(self):
        """Connect to IB Client Portal with safety checks and reconnection logic"""
        if self.ib_client.is_connected():
            return

        # IBIndClient handles retries internally
        self.ib_client.connect(
            host=self.config.ib_host,
            port=self.config.ib_port,
            client_id=self.config.ib_client_id,
            timeout=20,
        )

    def _ensure_connection(self):
        """Ensure IB connection is alive, reconnect if needed"""
        if not self.ib_client.is_connected():
            logger.warning("IB connection not established or lost, connecting...")
            self._connect_ib()

    def scan(self) -> int:
        """Scan ASX market for stocks showing momentum and price-sensitive announcements

        Returns:
            Number of new candidates found
        """
        logger.info("Starting TradingView market scan for candidates...")

        # Fetch price-sensitive announcements first
        price_sensitive_tickers = self.asx_scanner.fetch_price_sensitive_tickers()

        # Query TradingView for stocks with gaps > 2% (lower threshold for scanning)
        scan_threshold = 2.0
        gap_stocks = self.tv_scanner.scan_for_gaps(min_gap=scan_threshold)

        if not gap_stocks:
            logger.info("No stocks found in scan")
            return 0

        candidates_found = 0

        for stock in gap_stocks:
            # Only process if ticker has price-sensitive announcement
            if stock.ticker not in price_sensitive_tickers:
                logger.debug(
                    f"{stock.ticker}: Skipped (no price-sensitive announcement)"
                )
                continue

            try:
                logger.info(
                    f"{stock.ticker}: Gap {stock.gap_percent:.2f}% @ ${stock.close_price:.2f}"
                )

                # Check if already in candidates
                existing = self.db.get_candidate(stock.ticker)

                if not existing or existing.status != "watching":
                    # Add to candidates
                    candidate = Candidate(
                        ticker=stock.ticker,
                        headline=f"Gap detected: {stock.gap_percent:.2f}%",
                        scan_date=datetime.now().isoformat(),
                        status="watching",
                        gap_percent=stock.gap_percent,
                        prev_close=stock.close_price,
                    )
                    self.db.save_candidate(candidate)
                    candidates_found += 1
                    logger.info(
                        f"Added {stock.ticker} to candidates (gap: {stock.gap_percent:.2f}%, price-sensitive announcement)"
                    )

            except Exception as e:
                logger.error(f"Error adding candidate {stock.ticker}: {e}")
                continue

        logger.info(
            f"Scan complete. Found {candidates_found} new candidates with both momentum and announcements"
        )
        return candidates_found

    def monitor(self) -> int:
        """Monitor candidates and trigger on gap threshold

        Returns:
            Number of stocks triggered
        """
        logger.info("Monitoring for gaps at market open...")

        # Query TradingView for stocks with gaps >= threshold
        gap_stocks = self.tv_scanner.scan_for_gaps(
            min_gap=self.config.gap_threshold
        )

        if not gap_stocks:
            logger.info("No stocks meeting gap threshold")
            return 0

        gaps_found = 0

        # Get existing candidates
        candidates = self.db.get_watching_candidates()
        candidate_tickers = {c.ticker for c in candidates}

        for stock in gap_stocks:
            try:
                logger.info(
                    f"{stock.ticker}: Gap {stock.gap_percent:.2f}% @ ${stock.close_price:.2f}"
                )

                # Check if this ticker is in our candidates
                if stock.ticker in candidate_tickers:
                    # Trigger existing candidate
                    logger.warning(
                        f"{stock.ticker}: CANDIDATE TRIGGERED! Gap: {stock.gap_percent:.2f}%"
                    )

                    self.db.update_candidate_status(
                        stock.ticker, "triggered", stock.gap_percent
                    )
                    gaps_found += 1
                else:
                    # New stock meeting threshold - add directly as triggered
                    logger.warning(
                        f"{stock.ticker}: NEW STOCK TRIGGERED! Gap: {stock.gap_percent:.2f}%"
                    )

                    candidate = Candidate(
                        ticker=stock.ticker,
                        headline=f"Gap triggered: {stock.gap_percent:.2f}%",
                        scan_date=datetime.now().isoformat(),
                        status="triggered",
                        gap_percent=stock.gap_percent,
                        prev_close=stock.close_price,
                    )
                    self.db.save_candidate(candidate)
                    gaps_found += 1

            except Exception as e:
                logger.error(f"Error monitoring {stock.ticker}: {e}")
                continue

        logger.info(f"Monitoring complete. Found {gaps_found} triggered stocks")
        return gaps_found

    def execute(self) -> int:
        """Execute orders for triggered candidates

        Returns:
            Number of orders placed
        """
        logger.info("Executing orders for triggered candidates...")

        self._ensure_connection()

        # Check how many open positions we have
        position_count = self.db.count_open_positions()

        if position_count >= self.config.max_positions:
            logger.warning(
                f"Maximum positions ({self.config.max_positions}) reached, skipping execution"
            )
            return 0

        # Get triggered candidates
        candidates = self.db.get_triggered_candidates()

        if not candidates:
            logger.info("No triggered candidates to execute")
            return 0

        orders_placed = 0

        for candidate in candidates:
            ticker = candidate.ticker

            try:
                # Get current market price
                market_data = self.ib_client.get_market_data(ticker)

                if not market_data or not market_data.last_price or market_data.last_price <= 0:
                    logger.warning(f"{ticker}: No valid market data available")
                    continue

                current_price = market_data.last_price

                # Calculate position size (simple: fixed dollar amount)
                position_value = 5000  # $5000 per position
                quantity = min(
                    int(position_value / current_price),
                    self.config.max_position_size,
                )

                if quantity < 1:
                    logger.warning(f"{ticker}: Calculated quantity too small")
                    continue

                # Calculate stop loss at low of day (simplified: -5% for now)
                stop_loss = current_price * 0.95

                # Place market order
                order_result = self.ib_client.place_order(ticker, "BUY", quantity)

                if not order_result:
                    logger.warning(f"Order placement failed for {ticker}")
                    continue

                logger.info(f"Order placed: BUY {quantity} {ticker} @ market")

                # Use filled price if available, otherwise use current price as estimate
                fill_price = order_result.filled_price if order_result.filled_price else current_price

                logger.info(
                    f"Order {order_result.status}: {quantity} {ticker} @ ${fill_price:.2f}"
                )

                # Record position
                position_id = self.db.create_position(
                    ticker=ticker,
                    quantity=quantity,
                    entry_price=fill_price,
                    stop_loss=stop_loss,
                    entry_date=datetime.now().isoformat(),
                )

                # Record trade
                self.db.create_trade(
                    ticker=ticker,
                    action="BUY",
                    quantity=quantity,
                    price=fill_price,
                    position_id=position_id,
                )

                # Update candidate status
                self.db.update_candidate_status(ticker, "entered")

                orders_placed += 1

            except Exception as e:
                logger.error(f"Error executing order for {ticker}: {e}")
                continue

        logger.info(f"Execution complete. Placed {orders_placed} orders")
        return orders_placed

    def manage_positions(self) -> int:
        """Manage existing positions (Day 3 exit, trailing stops)

        Returns:
            Number of actions taken
        """
        logger.info("Managing existing positions...")

        self._ensure_connection()

        positions = self.db.get_open_positions()

        if not positions:
            logger.info("No positions to manage")
            return 0

        actions_taken = 0

        for position in positions:
            ticker = position.ticker
            position_id = position.id

            try:
                # Get current price
                market_data = self.ib_client.get_market_data(ticker)

                if not market_data or not market_data.last_price or market_data.last_price <= 0:
                    logger.warning(f"{ticker}: No valid market data")
                    continue

                current_price = market_data.last_price

                # Rule 1: Sell half on day 3
                if position.days_held >= 3 and not position.half_sold:
                    quantity_to_sell = position.quantity // 2

                    if quantity_to_sell > 0:
                        order_result = self.ib_client.place_order(ticker, "SELL", quantity_to_sell)

                        if not order_result:
                            logger.warning(f"Day 3 sell order failed for {ticker}")
                            continue

                        logger.info(
                            f"Day 3: Selling half position {quantity_to_sell} {ticker}"
                        )

                        # Use filled price if available, otherwise use current price as estimate
                        fill_price = order_result.filled_price if order_result.filled_price else current_price
                        pnl = (fill_price - position.entry_price) * quantity_to_sell

                        logger.info(
                            f"Half position sold: {quantity_to_sell} {ticker} @ ${fill_price:.2f}, PnL: ${pnl:.2f}"
                        )

                        # Update position
                        self.db.update_position_half_sold(position_id, True)
                        self.db.update_candidate_status(ticker, "half_exited")

                        # Record trade
                        self.db.create_trade(
                            ticker=ticker,
                            action="SELL",
                            quantity=quantity_to_sell,
                            price=fill_price,
                            position_id=position_id,
                            pnl=pnl,
                            notes="Day 3 half exit",
                        )

                        actions_taken += 1

                # Rule 2: Check stop loss (low of day approximation)
                if current_price <= position.stop_loss:
                    remaining_qty = (
                        position.quantity
                        if not position.half_sold
                        else position.quantity // 2
                    )

                    order_result = self.ib_client.place_order(ticker, "SELL", remaining_qty)

                    if not order_result:
                        logger.warning(f"Stop loss order failed for {ticker}")
                        continue

                    logger.warning(f"STOP LOSS HIT: Selling {remaining_qty} {ticker}")

                    # Use filled price if available, otherwise use current price as estimate
                    fill_price = order_result.filled_price if order_result.filled_price else current_price
                    pnl = (fill_price - position.entry_price) * remaining_qty

                    logger.info(
                        f"Stop loss executed: ${fill_price:.2f}, PnL: ${pnl:.2f}"
                    )

                    # Close position
                    self.db.update_position_exit(
                        position_id=position_id,
                        status="closed",
                        exit_price=fill_price,
                        exit_date=datetime.now().isoformat(),
                    )

                    # Record trade
                    self.db.create_trade(
                        ticker=ticker,
                        action="SELL",
                        quantity=remaining_qty,
                        price=fill_price,
                        position_id=position_id,
                        pnl=pnl,
                        notes="Stop loss",
                    )

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

        # Candidates
        watching = self.db.count_watching_candidates()
        logger.info(f"Watching candidates: {watching}")

        # Positions
        open_positions = self.db.count_open_positions()
        logger.info(f"Open positions: {open_positions}")

        # Display open positions
        positions = self.db.get_open_positions()

        for pos in positions:
            logger.info(
                f"  {pos.ticker}: {pos.quantity} shares @ ${pos.entry_price:.2f} ({pos.status})"
            )

        # Total PnL
        total_pnl = self.db.get_total_pnl()
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
            if self.ib_client.is_connected():
                self.ib_client.disconnect()
            self.db.close()


def main():
    """Main CLI entry point for the trading bot"""
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

    # Load configuration
    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create bot instance
    bot = TradingBot(config)

    # Run based on command line argument
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
            sys.exit(1)
    else:
        # No argument - run full workflow
        bot.run()


if __name__ == "__main__":
    main()
