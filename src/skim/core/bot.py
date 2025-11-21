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
from skim.strategy.exit import check_half_exit, check_stop_loss
from skim.strategy.order_executor import OrderExecutor
from skim.strategy.position_manager import can_open_new_position


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

        Note: Database persistence and Discord notifications are independent operations.
        Failure in one will not prevent the other from executing.
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

            # Scan for all gaps
            gap_stocks = self.ibkr_scanner.scan_for_gaps(
                min_gap=self.config.scanner_config.gap_threshold
            )

            # Filter gap stocks using set intersection with price-sensitive tickers
            filtered_gap_stocks = [
                stock
                for stock in gap_stocks
                if stock.ticker in price_sensitive_tickers
            ]

            # Build candidate data (in-memory) before persisting
            candidates_for_notification = []
            candidates_for_db = []

            for stock in filtered_gap_stocks:
                # Get current price for display
                current_price = None
                try:
                    market_data = self.ibkr_scanner.get_market_data(
                        str(stock.conid)
                    )
                    if market_data and market_data.last_price:
                        current_price = float(market_data.last_price)
                except Exception as e:
                    logger.debug(
                        f"Could not fetch market data for {stock.ticker}: {e}"
                    )

                # Build candidate dict for Discord notification
                candidate_dict = {
                    "ticker": stock.ticker,
                    "headline": f"Gap detected: {stock.gap_percent:.2f}%",
                    "gap_percent": stock.gap_percent,
                    "price": current_price,
                    "status": "watching",
                    "scan_date": datetime.now().isoformat(),
                }
                candidates_for_notification.append(candidate_dict)

                # Prepare candidate for database
                from skim.data.models import Candidate

                candidate = Candidate(
                    ticker=stock.ticker,
                    headline=candidate_dict["headline"],
                    scan_date=candidate_dict["scan_date"],
                    status=candidate_dict["status"],
                    gap_percent=stock.gap_percent,
                    prev_close=current_price,
                )
                candidates_for_db.append(candidate)

            candidates_found = len(filtered_gap_stocks)

            # Persist candidates to database (independent operation with own error handling)
            for candidate in candidates_for_db:
                try:
                    self.db.save_candidate(candidate)
                except Exception as e:
                    logger.error(
                        f"Failed to persist candidate {candidate.ticker}: {e}"
                    )

            # Send Discord notification (independent operation with own error handling)
            try:
                self.discord_notifier.send_scan_results(
                    candidates_found, candidates_for_notification
                )
            except Exception as e:
                logger.error(f"Failed to send Discord notification: {e}")

            logger.info(
                f"Scan complete. Found {candidates_found} new candidates with announcements"
            )
            return candidates_found

        except Exception as e:
            logger.error(f"Error in scan workflow: {e}")
            return 0

    def execute(self) -> int:
        """Execute orders for triggered candidates

        Returns:
            Number of orders placed
        """
        logger.info("Executing orders for triggered candidates...")

        self._ensure_connection()

        # Check if we can open new positions
        if not can_open_new_position(
            self.db.count_open_positions(),
            self.config.max_positions,
        ):
            logger.warning(
                f"Maximum positions ({self.config.max_positions}) reached, skipping execution"
            )
            return 0

        # Get triggered candidates
        candidates = self.db.get_triggered_candidates()

        if not candidates:
            logger.info("No triggered candidates to execute")
            return 0

        # Create order executor
        executor = OrderExecutor(self.ib_client, self.db, logger)

        orders_placed = 0

        for candidate in candidates:
            try:
                position_id = executor.execute_entry(
                    candidate,
                    stop_loss_source="daily_low",
                    max_position_size=self.config.max_position_size,
                    position_value=5000.0,
                )

                if position_id:
                    orders_placed += 1

            except Exception as e:
                logger.error(
                    f"Error executing order for {candidate.ticker}: {e}"
                )
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

        # Create order executor
        executor = OrderExecutor(self.ib_client, self.db, logger)

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

                # Rule 1: Sell half on day 3 first (if not already exited)
                half_exit_signal = check_half_exit(position)
                if half_exit_signal:
                    executor.execute_exit(
                        position,
                        half_exit_signal.quantity,
                        half_exit_signal.reason,
                    )

                    # Update position
                    if position_id is not None:
                        self.db.update_position_half_sold(position_id, True)
                    self.db.update_candidate_status(ticker, "half_exited")

                    actions_taken += 1

                # Rule 2: Check stop loss (may close entire position or remaining half)
                stop_loss_signal = check_stop_loss(position, current_price)
                if stop_loss_signal:
                    executor.execute_exit(
                        position,
                        stop_loss_signal.quantity,
                        stop_loss_signal.reason,
                    )

                    # Close position
                    if position_id is not None:
                        self.db.update_position_exit(
                            position_id=position_id,
                            status="closed",
                            exit_price=current_price,
                            exit_date=datetime.now().isoformat(),
                        )

                    logger.warning(
                        f"STOP LOSS HIT: {ticker} at ${current_price:.4f}"
                    )
                    actions_taken += 1
                    continue

                # Rule 3: Trailing stop with 10-day SMA (simplified for now)
                # TODO: Implement 10-day SMA trailing stop

            except Exception as e:
                logger.error(f"Error managing position {ticker}: {e}")
                continue

        logger.info(
            f"Position management complete. {actions_taken} actions taken"
        )
        return actions_taken

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

            # Execute ORH breakout orders
            self._ensure_connection()

            # Check if we can open new positions
            if not can_open_new_position(
                self.db.count_open_positions(),
                self.config.max_positions,
            ):
                logger.warning(
                    "Maximum positions reached, skipping ORH execution"
                )
                return 0

            # Create order executor
            executor = OrderExecutor(self.ib_client, self.db, logger)

            orders_placed = 0

            for candidate in candidates:
                try:
                    position_id = executor.execute_entry(
                        candidate,
                        stop_loss_source="or_low",
                        max_position_size=self.config.max_position_size,
                        position_value=5000.0,
                    )

                    if position_id:
                        orders_placed += 1

                except Exception as e:
                    logger.error(
                        f"Error executing ORH order for {candidate.ticker}: {e}"
                    )
                    continue

            logger.info(
                f"ORH execution complete. Placed {orders_placed} orders"
            )
            return orders_placed

        except Exception as e:
            logger.error(f"Error executing ORH breakout orders: {e}")
            return 0


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
                "Available methods: scan, track_or_breakouts, execute_orh_breakouts, manage_positions"
            )
            sys.exit(1)
    else:
        logger.error(
            "No method specified. Use one of: scan, track_or_breakouts, execute_orh_breakouts, manage_positions"
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
