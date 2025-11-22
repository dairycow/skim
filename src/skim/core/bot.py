#!/usr/bin/env python3
"""Skim - ASX Trading Bot

Thin orchestrator that dispatches work to specialized modules:
- scanner: Find candidates with gap + announcement + opening range
- trader: Execute entries on ORH breakouts, exits on stops
- monitor: Check positions for stop loss triggers
"""

import sys

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient
from skim.core.config import Config
from skim.data.database import Database
from skim.monitor import Monitor
from skim.notifications.discord import DiscordNotifier
from skim.scanner import Scanner
from skim.trader import Trader


class TradingBot:
    """Minimal trading bot orchestrator"""

    def __init__(self, config: Config):
        """Initialise bot with configuration

        Args:
            config: Configuration object with all settings
        """
        logger.info("Initialising Skim Trading Bot...")

        self.config = config

        # Initialise database
        self.db = Database(config.db_path)

        # Initialise IB client (lazy connection)
        self.ib_client = IBKRClient(paper_trading=config.paper_trading)

        # Initialise core modules with shared client
        self.scanner = Scanner(
            ib_client=self.ib_client,
            gap_threshold=config.scanner_config.gap_threshold,
        )
        self.trader = Trader(self.ib_client, self.db)
        self.monitor = Monitor(self.ib_client)

        # Initialise Discord notifier
        self.discord = DiscordNotifier(config.discord_webhook_url)

        logger.info("Bot initialised successfully")

    def _ensure_connection(self):
        """Ensure IB connection is active"""
        if not self.ib_client.is_connected():
            logger.info("Connecting to IBKR...")
            self.ib_client.connect(timeout=20)

    def scan(self) -> int:
        """Scan for candidates with gap + announcement + opening range

        Returns:
            Number of candidates found
        """
        logger.info("Scanning for candidates...")

        try:
            # Find candidates with gap + announcement + OR data
            candidates = self.scanner.find_candidates()

            if not candidates:
                logger.warning("No candidates found")
                return 0

            # Save candidates to database
            for candidate in candidates:
                try:
                    self.db.save_candidate(candidate)
                except Exception as e:
                    logger.error(
                        f"Failed to save candidate {candidate.ticker}: {e}"
                    )

            # Notify Discord
            try:
                self.discord.send_scan_results(
                    len(candidates),
                    [
                        {
                            "ticker": c.ticker,
                            "or_high": c.or_high,
                            "or_low": c.or_low,
                            "status": c.status,
                        }
                        for c in candidates
                    ],
                )
            except Exception as e:
                logger.error(f"Failed to notify Discord: {e}")

            logger.info(f"Scan complete. Found {len(candidates)} candidates")
            return len(candidates)

        except Exception as e:
            logger.error(f"Scan failed: {e}")
            return 0

    def trade(self) -> int:
        """Execute breakout entries for watching candidates

        Returns:
            Number of orders placed
        """
        logger.info("Executing breakouts...")

        try:
            self._ensure_connection()

            # Check position limit
            open_count = self.db.count_open_positions()
            if open_count >= self.config.max_positions:
                logger.warning(
                    f"Max positions ({self.config.max_positions}) reached"
                )
                return 0

            # Get watching candidates
            candidates = self.db.get_watching_candidates()

            if not candidates:
                logger.info("No watching candidates")
                return 0

            # Execute breakouts
            entries = self.trader.execute_breakouts(candidates)

            logger.info(f"Trade complete. {entries} entries executed")
            return entries

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return 0

    def manage(self) -> int:
        """Monitor positions and execute stops

        Returns:
            Number of actions taken
        """
        logger.info("Managing positions...")

        try:
            self._ensure_connection()

            # Get open positions
            positions = self.db.get_open_positions()

            if not positions:
                logger.info("No open positions")
                return 0

            # Check for stop hits
            stops = self.monitor.check_stops(positions)

            if not stops:
                logger.info("No stops triggered")
                return 0

            # Execute stops
            exits = self.trader.execute_stops(stops)

            logger.info(f"Management complete. {exits} stops executed")
            return exits

        except Exception as e:
            logger.error(f"Position management failed: {e}")
            return 0


def main():
    """CLI entry point"""
    # Setup logging
    logger.add(
        "logs/skim_{time}.log",
        rotation="1 day",
        retention="30 days",
        compression="gz",
        level="INFO",
    )

    logger.info("=" * 60)
    logger.info("SKIM TRADING BOT - ORH BREAKOUT STRATEGY")
    logger.info("=" * 60)

    # Load configuration
    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    # Create bot
    bot = TradingBot(config)

    # Execute command
    if len(sys.argv) < 2:
        logger.error("No method specified")
        logger.info("Available methods: scan, trade, manage")
        sys.exit(1)

    method = sys.argv[1]

    if method == "scan":
        bot.scan()
    elif method == "trade":
        bot.trade()
    elif method == "manage":
        bot.manage()
    else:
        logger.error(f"Unknown method: {method}")
        logger.info("Available methods: scan, trade, manage")
        sys.exit(1)


if __name__ == "__main__":
    main()
