#!/usr/bin/env python3
"""Skim - ASX Trading Bot

Orchestrator that manages multiple trading strategies
"""

import asyncio
import sys
from datetime import date

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient
from skim.brokers.ibkr_gap_scanner import IBKRGapScanner
from skim.brokers.ibkr_market_data import IBKRMarketData
from skim.brokers.ibkr_orders import IBKROrders
from skim.core.config import Config
from skim.data.database import Database
from skim.notifications.discord import DiscordNotifier
from skim.strategies import ORHBreakoutStrategy
from skim.strategies.base import Strategy


class TradingBot:
    """Multi-strategy trading bot orchestrator

    Manages shared services and delegates to strategy-specific implementations
    """

    def __init__(self, config: Config):
        """Initialise bot with configuration"""
        logger.info("Initialising Skim Trading Bot...")
        self.config = config
        self.db = Database(config.db_path)

        # --- Shared Service Instantiation ---
        self.ib_client = IBKRClient(paper_trading=config.paper_trading)
        self.market_data_service = IBKRMarketData(self.ib_client)
        self.order_service = IBKROrders(
            self.ib_client, self.market_data_service
        )
        self.scanner_service = IBKRGapScanner(
            self.ib_client, config.scanner_config
        )
        self.discord = DiscordNotifier(config.discord_webhook_url)

        # --- Strategy Registration ---
        self.strategies: dict[str, Strategy] = {}
        self._register_strategies()

        logger.info("Bot initialised successfully")

    def _register_strategies(self) -> None:
        """Register available strategies

        Add new strategies here when implemented
        """
        self.strategies["orh_breakout"] = ORHBreakoutStrategy(
            ib_client=self.ib_client,
            scanner_service=self.scanner_service,
            market_data_service=self.market_data_service,
            order_service=self.order_service,
            db=self.db,
            discord=self.discord,
            config=self.config,
        )

        logger.info(f"Registered {len(self.strategies)} strategies")

    def _get_strategy(self, strategy_name: str) -> Strategy:
        """Get strategy by name

        Args:
            strategy_name: Name of the strategy

        Returns:
            Strategy instance

        Raises:
            ValueError: If strategy not found
        """
        if strategy_name not in self.strategies:
            raise ValueError(
                f"Unknown strategy: {strategy_name}. "
                f"Available strategies: {list(self.strategies.keys())}"
            )
        return self.strategies[strategy_name]

    async def _ensure_connection(self):
        """Ensure IB connection is active"""
        if not self.ib_client.is_connected():
            logger.info("Connecting to IBKR...")
            await self.ib_client.connect(timeout=20)

    async def scan(self, strategy: str = "orh_breakout") -> int:
        """Execute strategy scan phase

        Args:
            strategy: Strategy name to scan

        Returns:
            Number of candidates found
        """
        strat = self._get_strategy(strategy)
        return await strat.scan()

    async def track_ranges(self, strategy: str = "orh_breakout") -> int:
        """Track opening ranges for candidates

        Args:
            strategy: Strategy name to track ranges for

        Returns:
            Number of candidates updated with opening ranges
        """
        strat = self._get_strategy(strategy)
        return await strat.track_ranges()

    async def alert(self, strategy: str = "orh_breakout") -> int:
        """Send alerts for tradeable candidates

        Args:
            strategy: Strategy name to alert for

        Returns:
            Number of candidates alerted
        """
        strat = self._get_strategy(strategy)
        return await strat.alert()

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

    async def trade(self, strategy: str = "orh_breakout") -> int:
        """Execute breakout entries

        Args:
            strategy: Strategy name to trade

        Returns:
            Number of trades executed
        """
        strat = self._get_strategy(strategy)
        return await strat.trade()

    async def manage(self, strategy: str = "orh_breakout") -> int:
        """Monitor positions and execute stops

        Args:
            strategy: Strategy name to manage

        Returns:
            Number of positions managed
        """
        strat = self._get_strategy(strategy)
        return await strat.manage()

    async def status(self, strategy: str = "orh_breakout") -> bool:
        """Perform health check

        Args:
            strategy: Strategy name to check

        Returns:
            True if healthy
        """
        strat = self._get_strategy(strategy)
        return await strat.health_check()

    async def purge_candidates(
        self, only_before_utc_date: date | None = None
    ) -> int:
        """Clear candidate rows before a scan.

        Args:
            only_before_utc_date: Optional UTC date to limit deletions. When
                omitted, all candidates are deleted.
        """
        logger.info("Purging candidates...")
        try:
            deleted = self.db.purge_candidates(only_before_utc_date)
            logger.info(f"Deleted {deleted} candidate rows")
            return deleted
        except Exception as e:
            logger.error(f"Candidate purge failed: {e}", exc_info=True)
            return 0


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
    logger.info("SKIM TRADING BOT - MULTI-STRATEGY")
    logger.info("=" * 60)

    try:
        config = Config.from_env()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    bot = TradingBot(config)

    if len(sys.argv) < 2:
        logger.error(
            "No method specified. Available: scan, track_ranges, alert, trade, manage, status, purge_candidates, fetch_market_data"
        )
        sys.exit(1)

    method = sys.argv[1]

    async def run():
        try:
            if method == "scan":
                await bot.scan()
            elif method == "track_ranges":
                await bot.track_ranges()
            elif method == "alert":
                await bot.alert()
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
            elif method == "purge_candidates":
                cutoff = None
                if len(sys.argv) >= 3:
                    try:
                        cutoff = date.fromisoformat(sys.argv[2])
                    except ValueError:
                        logger.error(
                            "Invalid date format. Use YYYY-MM-DD for cutoff."
                        )
                        sys.exit(1)
                await bot.purge_candidates(cutoff)
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
