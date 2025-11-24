#!/usr/bin/env python3
"""Skim - ASX Trading Bot

Thin orchestrator that dispatches work to specialized modules
"""

import asyncio
import sys

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient
from skim.brokers.ibkr_market_data import IBKRMarketData
from skim.brokers.ibkr_orders import IBKROrders
from skim.brokers.ibkr_scanner import IBKRScanner
from skim.core.config import Config
from skim.data.database import Database
from skim.monitor import Monitor
from skim.notifications.discord import DiscordNotifier
from skim.range_tracker import RangeTracker
from skim.scanner import Scanner
from skim.trader import Trader


class TradingBot:
    """Minimal trading bot orchestrator"""

    def __init__(self, config: Config):
        """Initialise bot with configuration"""
        logger.info("Initialising Skim Trading Bot...")
        self.config = config
        self.db = Database(config.db_path)

        # --- Service Instantiation ---
        self.ib_client = IBKRClient(paper_trading=config.paper_trading)
        self.market_data_service = IBKRMarketData(self.ib_client)
        self.order_service = IBKROrders(
            self.ib_client, self.market_data_service
        )
        self.scanner_service = IBKRScanner(
            self.ib_client, config.scanner_config
        )
        self.discord = DiscordNotifier(config.discord_webhook_url)

        # --- Business Logic Modules ---
        self.scanner = Scanner(
            scanner_service=self.scanner_service,
            gap_threshold=config.scanner_config.gap_threshold,
        )
        self.range_tracker = RangeTracker(
            market_data_service=self.market_data_service,
            db=self.db,
        )
        self.trader = Trader(
            self.market_data_service,
            self.order_service,
            self.db,
            notifier=self.discord,
        )
        self.monitor = Monitor(self.market_data_service)

        logger.info("Bot initialised successfully")

    async def _ensure_connection(self):
        """Ensure IB connection is active"""
        if not self.ib_client.is_connected():
            logger.info("Connecting to IBKR...")
            await self.ib_client.connect(timeout=20)

    async def scan(self) -> int:
        """Scan for candidates with gap + announcement + opening range"""
        logger.info("Scanning for candidates...")
        try:
            await self._ensure_connection()
            candidates = await self.scanner.find_candidates()

            count = len(candidates)
            if not candidates:
                logger.warning("No candidates found")
            else:
                for candidate in candidates:
                    self.db.save_candidate(candidate)

            # Notify via Discord (safe to call even when zero candidates)
            try:
                payload = [
                    {
                        "ticker": c.ticker,
                        "gap_percent": getattr(c, "gap_percent", None),
                        "price": getattr(c, "price", None),
                    }
                    for c in candidates
                ]
                self.discord.send_scan_results(count, payload)
            except Exception as notify_err:
                logger.error(
                    f"Failed to send Discord scan notification: {notify_err}"
                )

            logger.info(f"Scan complete. Found {count} candidates")
            return count
        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            return 0

    async def track_ranges(self) -> int:
        """Track opening ranges for candidates without ORH/ORL values"""
        logger.info("Tracking opening ranges...")
        try:
            await self._ensure_connection()
            updated = await self.range_tracker.track_opening_ranges()
            logger.info(
                f"Opening range tracking complete. Updated {updated} candidates"
            )
            return updated
        except Exception as e:
            logger.error(f"Opening range tracking failed: {e}", exc_info=True)
            return 0

    async def fetch_market_data(self, ticker: str):
        """Fetch a single ticker's market data via IBKR."""
        if not ticker:
            logger.error("Ticker is required to fetch market data")
            return None

        logger.info(f"Fetching market data for {ticker}...")
        try:
            await self._ensure_connection()
            data = await self.market_data_service.get_market_data(ticker)

            if not data:
                logger.warning(f"No market data returned for {ticker}")
                return None

            logger.info(
                f"{ticker} market data - last={data.last_price}, high={data.high}, low={data.low}, "
                f"bid={data.bid}, ask={data.ask}, volume={data.volume}"
            )
            return data
        except Exception as e:
            logger.error(
                f"Market data fetch failed for {ticker}: {e}", exc_info=True
            )
            return None

    async def trade(self) -> int:
        """Execute breakout entries for watching candidates"""
        logger.info("Executing breakouts...")
        try:
            await self._ensure_connection()
            candidates = self.db.get_watching_candidates()
            if not candidates:
                logger.info("No candidates to trade.")
                return 0
            return await self.trader.execute_breakouts(candidates)
        except Exception as e:
            logger.error(f"Trade execution failed: {e}", exc_info=True)
            return 0

    async def manage(self) -> int:
        """Monitor positions and execute stops"""
        logger.info("Managing positions...")
        try:
            await self._ensure_connection()
            positions = self.db.get_open_positions()
            if not positions:
                logger.info("No open positions to manage.")
                return 0

            stops_hit = await self.monitor.check_stops(positions)
            if not stops_hit:
                logger.info("No stop losses hit.")
                return 0

            return await self.trader.execute_stops(stops_hit)
        except Exception as e:
            logger.error(f"Position management failed: {e}", exc_info=True)
            return 0

    async def status(self) -> bool:
        """Lightweight health check - ensures IBKR connection is live."""
        logger.info("Performing health check...")
        try:
            await self._ensure_connection()
            account = self.ib_client.get_account()
            logger.info(f"Health check OK. Connected account: {account}")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}", exc_info=True)
            return False


def main():
    """CLI entry point"""
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

    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    bot = TradingBot(config)

    if len(sys.argv) < 2:
        logger.error(
            "No method specified. Available: scan, track_ranges, trade, manage, status"
        )
        sys.exit(1)

    method = sys.argv[1]

    async def run():
        try:
            if method == "scan":
                await bot.scan()
            elif method == "track_ranges":
                await bot.track_ranges()
            elif method in ("fetch_market_data", "market_data"):
                if len(sys.argv) < 3:
                    logger.error(
                        "Ticker required. Usage: python -m skim.core.bot fetch_market_data <TICKER>"
                    )
                    sys.exit(1)
                ticker = sys.argv[2]
                await bot.fetch_market_data(ticker)
            elif method == "trade":
                await bot.trade()
            elif method == "manage":
                await bot.manage()
            elif method == "status":
                await bot.status()
            else:
                logger.error(f"Unknown method: {method}")
                sys.exit(1)
        finally:
            if bot.ib_client.is_connected():
                logger.info("Shutting down IBKR connection...")
                await bot.ib_client.disconnect()

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.warning("Bot stopped manually.")
    except Exception as e:
        logger.critical(
            f"Unhandled exception in bot execution: {e}", exc_info=True
        )
    finally:
        logger.info("Bot shutdown complete.")


if __name__ == "__main__":
    main()
