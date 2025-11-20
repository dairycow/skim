#!/usr/bin/env python3
"""
Skim - ASX Trading Bot
"""

import sys
from datetime import datetime

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient
from skim.core.config import Config
from skim.data.database import Database
from skim.notifications.discord import DiscordNotifier
from skim.scanners.asx_announcements import ASXAnnouncementScanner
from skim.scanners.ibkr_gap_scanner import IBKRGapScanner


class TradingBot:
    """ASX Pivot Trading Bot"""

    def __init__(self, config: Config):
        """Initialise the trading bot with configuration

        Args:
            config: Configuration object with all settings
        """
        logger.info("Initializing Skim Trading Bot...")

        self.config = config

        # Initialise database
        self.db = Database(config.db_path)

        # Initialise scanners
        self.ibkr_scanner = IBKRGapScanner(
            paper_trading=config.paper_trading,
            scanner_config=config.scanner_config,
        )
        self.asx_scanner = ASXAnnouncementScanner()

        # Initialise IB client (lazy connection)
        self.ib_client = IBKRClient(paper_trading=config.paper_trading)

        # Initialise Discord notifier
        self.discord_notifier = DiscordNotifier(config.discord_webhook_url)

        logger.info("Bot initialised successfully")

    def _connect_ib(self):
        """Connect to IB Client Portal with safety checks and reconnection logic"""
        if self.ib_client.is_connected():
            return

        self.ib_client.connect(timeout=20)

    def _ensure_connection(self):
        """Ensure IB connection is alive, reconnect if needed"""
        if not self.ib_client.is_connected():
            logger.warning(
                "IB connection not established or lost, connecting..."
            )
            self._connect_ib()

    def scan(self) -> int:
        """Scan ASX market for stocks showing momentum and price-sensitive announcements

        Returns:
            Number of new candidates found
        """
        logger.info("Starting IBKR market scan for candidates...")

        try:
            # Fetch price-sensitive announcements first
            price_sensitive_tickers = (
                self.asx_scanner.fetch_price_sensitive_tickers()
            )

            # Connect to IBKR if needed
            if not self.ibkr_scanner.is_connected():
                self._ensure_connection()
                self.ibkr_scanner.connect()

            # Use enhanced scanner for complete gap scanning workflow
            gap_stocks, new_candidates = (
                self.ibkr_scanner.scan_gaps_with_announcements(
                    price_sensitive_tickers=price_sensitive_tickers, db=self.db
                )
            )

            candidates_found = len(new_candidates)

            # Send Discord notification
            try:
                self.discord_notifier.send_scan_results(
                    candidates_found, new_candidates
                )
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")

            logger.info(
                f"Scan complete. Found {candidates_found} new candidates with both momentum and announcements"
            )
            return candidates_found

        except Exception as e:
            logger.error(f"Error in scan workflow: {e}")
            return 0

    def monitor(self) -> int:
        """Monitor candidates and trigger on gap threshold

        Returns:
            Number of stocks triggered
        """
        logger.info("Monitoring for gaps at market open...")

        # Get existing candidates
        candidates = self.db.get_watching_candidates()

        # Connect to IBKR if needed
        if not self.ibkr_scanner.is_connected():
            self._ensure_connection()
            self.ibkr_scanner.connect()

        # Use enhanced scanner for complete gap monitoring workflow
        gap_stocks, gaps_triggered = self.ibkr_scanner.scan_and_monitor_gaps(
            existing_candidates=candidates, db=self.db
        )

        logger.info(
            f"Monitoring complete. Found {gaps_triggered} triggered stocks"
        )
        return gaps_triggered

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
                conid = self.ib_client._get_contract_id(ticker)
                market_data = self.ib_client.get_market_data(conid)

                if (
                    not market_data
                    or not market_data.last_price
                    or market_data.last_price <= 0
                ):
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

                # Calculate stop loss at low of day
                conid = self.ib_client._get_contract_id(ticker)
                market_data = self.ib_client.get_market_data(conid)
                if market_data and market_data.low > 0:
                    stop_loss = market_data.low
                    logger.info(
                        f"{ticker}: Using daily low stop loss: ${stop_loss:.4f}"
                    )
                else:
                    # Fallback to -5% if daily low unavailable
                    stop_loss = current_price * 0.95
                    logger.warning(
                        f"{ticker}: Using fallback stop loss: ${stop_loss:.4f} (daily low unavailable)"
                    )

                # Place market order
                order_result = self.ib_client.place_order(
                    ticker, "BUY", quantity
                )

                if not order_result:
                    logger.warning(f"Order placement failed for {ticker}")
                    continue

                logger.info(f"Order placed: BUY {quantity} {ticker} @ market")

                # Use filled price if available, otherwise use current price as estimate
                fill_price = (
                    order_result.filled_price
                    if order_result.filled_price
                    else current_price
                )

                logger.info(
                    f"Order {order_result.status}: {quantity} {ticker} @ ${fill_price:.4f}"
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
                conid = self.ib_client._get_contract_id(ticker)
                market_data = self.ib_client.get_market_data(conid)

                if (
                    not market_data
                    or not market_data.last_price
                    or market_data.last_price <= 0
                ):
                    logger.warning(f"{ticker}: No valid market data")
                    continue

                current_price = market_data.last_price

                # Rule 1: Sell half on day 3
                if position.days_held >= 3 and not position.half_sold:
                    quantity_to_sell = position.quantity // 2

                    if quantity_to_sell > 0:
                        order_result = self.ib_client.place_order(
                            ticker, "SELL", quantity_to_sell
                        )

                        if not order_result:
                            logger.warning(
                                f"Day 3 sell order failed for {ticker}"
                            )
                            continue

                        logger.info(
                            f"Day 3: Selling half position {quantity_to_sell} {ticker}"
                        )

                        # Use filled price if available, otherwise use current price as estimate
                        fill_price = (
                            order_result.filled_price
                            if order_result.filled_price
                            else current_price
                        )
                        pnl = (
                            fill_price - position.entry_price
                        ) * quantity_to_sell

                        logger.info(
                            f"Half position sold: {quantity_to_sell} {ticker} @ ${fill_price:.4f}, PnL: ${pnl:.4f}"
                        )

                        # Update position
                        if position_id is not None:
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

                    order_result = self.ib_client.place_order(
                        ticker, "SELL", remaining_qty
                    )

                    if not order_result:
                        logger.warning(f"Stop loss order failed for {ticker}")
                        continue

                    logger.warning(
                        f"STOP LOSS HIT: Selling {remaining_qty} {ticker}"
                    )

                    # Use filled price if available, otherwise use current price as estimate
                    fill_price = (
                        order_result.filled_price
                        if order_result.filled_price
                        else current_price
                    )
                    pnl = (fill_price - position.entry_price) * remaining_qty

                    logger.info(
                        f"Stop loss executed: ${fill_price:.4f}, PnL: ${pnl:.4f}"
                    )

                    # Close position
                    if position_id is not None:
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

        logger.info(
            f"Position management complete. {actions_taken} actions taken"
        )
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
                f"  {pos.ticker}: {pos.quantity} shares @ ${pos.entry_price:.4f} ({pos.status})"
            )

        # Total PnL
        total_pnl = self.db.get_total_pnl()
        logger.info(f"Total PnL: ${total_pnl:.4f}")

        logger.info("=====================")

    def track_or_breakouts(self) -> int:
        """Track opening range for OR tracking candidates and detect breakouts

        Returns:
            Number of ORH breakout candidates detected
        """
        logger.info("Tracking opening range breakouts...")

        try:
            # Get OR tracking candidates
            candidates = self.db.get_or_tracking_candidates()

            if not candidates:
                logger.info("No OR tracking candidates found")
                return 0

            # Convert to GapStock objects for scanner
            gap_stocks = []
            for candidate in candidates:
                if candidate.conid:
                    from skim.scanners.ibkr_gap_scanner import GapStock

                    gap_stock = GapStock(
                        ticker=candidate.ticker,
                        gap_percent=candidate.gap_percent or 0.0,
                        conid=candidate.conid,
                    )
                    gap_stocks.append(gap_stock)

            if not gap_stocks:
                logger.warning("No valid gap stocks for OR tracking")
                return 0

            # Connect scanner if needed
            if not self.ibkr_scanner.is_connected():
                self._ensure_connection()
                self.ibkr_scanner.connect()

            # Track opening range for 10 minutes
            or_data = self.ibkr_scanner.track_opening_range(
                gap_stocks, duration_seconds=600, poll_interval=30
            )

            # Filter for breakouts
            breakouts = self.ibkr_scanner.filter_breakouts(or_data)

            breakout_count = 0
            for breakout in breakouts:
                try:
                    # Update candidate with OR data and breakout status
                    self.db.update_candidate_or_data(
                        ticker=breakout.ticker,
                        or_high=breakout.or_high,
                        or_low=breakout.or_low,
                        or_timestamp=breakout.timestamp.isoformat(),
                    )

                    # Update status to ORH breakout
                    self.db.update_candidate_status(
                        breakout.ticker, "orh_breakout"
                    )
                    breakout_count += 1

                    logger.info(
                        f"ORH breakout detected: {breakout.ticker} @ ${breakout.current_price:.4f} (ORH: ${breakout.or_high:.4f})"
                    )

                except Exception as e:
                    logger.error(
                        f"Error updating ORH breakout {breakout.ticker}: {e}"
                    )
                    continue

            logger.info(
                f"OR tracking complete. Found {breakout_count} ORH breakouts"
            )
            return breakout_count

        except Exception as e:
            logger.error(f"Error in OR tracking: {e}")
            return 0

    def scan_for_or_breakouts(self) -> int:
        """Scan for gaps and track OR breakouts in one workflow

        Returns:
            Number of ORH breakout candidates detected
        """
        logger.info("Scanning for gaps and tracking OR breakouts...")

        try:
            # Connect scanner if needed
            if not self.ibkr_scanner.is_connected():
                self._ensure_connection()
                self.ibkr_scanner.connect()

            # Use enhanced scanner for OR tracking workflow
            candidates_found = self.ibkr_scanner.scan_for_or_tracking(
                db=self.db
            )

            if candidates_found == 0:
                logger.info("No OR tracking candidates found")
                return 0

            # Get OR tracking candidates for breakout detection
            candidates = self.db.get_or_tracking_candidates()

            # Convert to GapStock objects for scanner
            gap_stocks = []
            for candidate in candidates:
                if candidate.conid:
                    from skim.scanners.ibkr_gap_scanner import GapStock

                    gap_stock = GapStock(
                        ticker=candidate.ticker,
                        gap_percent=candidate.gap_percent or 0.0,
                        conid=candidate.conid,
                    )
                    gap_stocks.append(gap_stock)

            if not gap_stocks:
                logger.warning("No valid gap stocks for OR tracking")
                return 0

            # Track opening range for 10 minutes
            or_data = self.ibkr_scanner.track_opening_range(
                gap_stocks, duration_seconds=600, poll_interval=30
            )

            # Filter for breakouts
            breakouts = self.ibkr_scanner.filter_breakouts(or_data)

            breakout_count = 0
            for breakout in breakouts:
                try:
                    # Update candidate with OR data and breakout status
                    self.db.update_candidate_or_data(
                        ticker=breakout.ticker,
                        or_high=breakout.or_high,
                        or_low=breakout.or_low,
                        or_timestamp=breakout.timestamp.isoformat(),
                    )

                    # Update status to ORH breakout
                    self.db.update_candidate_status(
                        breakout.ticker, "orh_breakout"
                    )
                    breakout_count += 1

                    logger.info(
                        f"ORH breakout detected: {breakout.ticker} @ ${breakout.current_price:.4f} (ORH: ${breakout.or_high:.4f})"
                    )

                except Exception as e:
                    logger.error(
                        f"Error updating ORH breakout {breakout.ticker}: {e}"
                    )
                    continue

            logger.info(
                f"OR tracking complete. Found {breakout_count} ORH breakouts"
            )
            return breakout_count

        except Exception as e:
            logger.error(f"Error in OR tracking: {e}")
            return 0

    def execute_orh_breakouts(self) -> int:
        """Execute orders for ORH breakout candidates using existing breakout order logic

        Returns:
            Number of orders placed
        """
        logger.info("Executing orders for ORH breakout candidates...")

        try:
            # Get ORH breakout candidates
            candidates = self.db.get_orh_breakout_candidates()

            if not candidates:
                logger.info("No ORH breakout candidates to execute")
                return 0

            # Use fallback execution logic
            return self._execute_orh_orders_fallback(candidates)

        except Exception as e:
            logger.error(f"Error executing ORH breakout orders: {e}")
            return 0

    def _execute_orh_orders_fallback(self, candidates) -> int:
        """Fallback method for executing ORH breakout orders

        Args:
            candidates: List of ORH breakout candidates

        Returns:
            Number of orders placed
        """
        logger.info("Using fallback ORH breakout execution...")

        self._ensure_connection()

        # Check position limits
        position_count = self.db.count_open_positions()
        if position_count >= self.config.max_positions:
            logger.warning("Maximum positions reached, skipping ORH execution")
            return 0

        orders_placed = 0

        for candidate in candidates:
            ticker = candidate.ticker

            try:
                # Get current market data
                conid = self.ib_client._get_contract_id(ticker)
                market_data = self.ib_client.get_market_data(conid)

                if not market_data or not market_data.last_price:
                    logger.warning(
                        f"{ticker}: No valid market data for ORH execution"
                    )
                    continue

                current_price = market_data.last_price

                # Calculate position size
                position_value = 5000  # $5000 per position
                quantity = min(
                    int(position_value / current_price),
                    self.config.max_position_size,
                )

                if quantity < 1:
                    logger.warning(f"{ticker}: Calculated quantity too small")
                    continue

                # Set stop loss at OR low or 5% below entry
                stop_loss = (
                    candidate.or_low
                    if candidate.or_low and candidate.or_low > 0
                    else current_price * 0.95
                )

                # Place market order
                order_result = self.ib_client.place_order(
                    ticker, "BUY", quantity
                )

                if not order_result:
                    logger.warning(f"ORH order placement failed for {ticker}")
                    continue

                logger.info(
                    f"ORH order placed: BUY {quantity} {ticker} @ market"
                )

                # Use filled price if available
                fill_price = (
                    order_result.filled_price
                    if order_result.filled_price
                    else current_price
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
                    notes="ORH breakout entry",
                )

                # Update candidate status
                self.db.update_candidate_status(ticker, "entered")

                orders_placed += 1

            except Exception as e:
                logger.error(f"Error executing ORH order for {ticker}: {e}")
                continue

        logger.info(f"ORH execution complete. Placed {orders_placed} orders")
        return orders_placed

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
        compression="gz",
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
                "Available methods: scan, monitor, execute, manage_positions, status, run, scan_for_or_breakouts, track_or_breakouts, execute_orh_breakouts"
            )
            sys.exit(1)
    else:
        # No argument - run full workflow
        bot.run()


if __name__ == "__main__":
    main()
