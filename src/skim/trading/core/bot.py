"""Skim - ASX Trading Bot

Orchestrator that manages multiple trading strategies
"""

from datetime import date

from loguru import logger

from skim.domain.strategies.base import Strategy as DomainStrategy
from skim.domain.strategies.context import StrategyContext
from skim.domain.strategies.registry import registry
from skim.infrastructure.brokers.ibkr import IBKRClient
from skim.trading.brokers.ibkr_gap_scanner import IBKRGapScanner
from skim.trading.brokers.ibkr_market_data import IBKRMarketData
from skim.trading.brokers.ibkr_orders import IBKROrders
from skim.trading.core.config import Config
from skim.trading.data.database import Database
from skim.trading.data.repositories.orh_repository import (
    ORHCandidateRepository,
)
from skim.trading.notifications.discord import DiscordNotifier


class TradingBot:
    """Multi-strategy trading bot orchestrator

    Manages shared services and delegates to strategy-specific implementations
    """

    def __init__(self, config: Config):
        """Initialise bot with configuration"""
        logger.info("Initialising Skim Trading Bot...")
        self.config = config
        self.db = Database(config.db_path)

        self.ib_client = IBKRClient(paper_trading=config.paper_trading)
        self.market_data_service = IBKRMarketData(self.ib_client)
        self.order_service = IBKROrders(
            self.ib_client, self.market_data_service
        )
        self.scanner_service = IBKRGapScanner(
            self.ib_client, config.scanner_config
        )
        self.discord = DiscordNotifier(config.discord_webhook_url)

        self.strategies: dict[str, DomainStrategy] = {}
        self._register_strategies()

        logger.info("Bot initialised successfully")

    def _create_strategy_context(self) -> StrategyContext:
        """Create a strategy context with all dependencies.

        Returns:
            StrategyContext with all required services
        """
        orh_repo = ORHCandidateRepository(self.db)
        return StrategyContext(
            database=self.db,
            repository=orh_repo,
            position_repository=self.db,
            notifier=self.discord,
            config=self.config,
            market_data=self.market_data_service,
            order_service=self.order_service,
            scanner_service=self.scanner_service,
            connection_manager=self.ib_client,
        )

    def _register_strategies(self) -> None:
        """Register available strategies using the StrategyRegistry.

        Strategies are auto-registered via the @register_strategy decorator.
        We use the global registry to instantiate strategies.
        """
        available = registry.list_available()
        context = self._create_strategy_context()

        for name in available:
            self.strategies[name] = registry.get(name, context)
            logger.info(f"Registered strategy: {name}")

        logger.info(f"Registered {len(self.strategies)} strategies")

    def _get_strategy(self, strategy_name: str) -> DomainStrategy:
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
            result = await self.market_data_service.get_market_data(ticker)

            if not result or isinstance(result, dict):
                logger.warning(f"No valid market data returned for {ticker}")
                return None

            logger.info(
                f"{ticker} market data - last={result.last_price}, high={result.high}, low={result.low}, "
                f"bid={result.bid}, ask={result.ask}, volume={result.volume}"
            )
            return result
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
