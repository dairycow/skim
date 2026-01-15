"""Trading context extending StrategyContext with trading-specific dependencies."""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skim.domain.repositories import CandidateRepository
    from skim.infrastructure.brokers.protocols import (
        BrokerConnectionManager,
        GapScannerService,
        MarketDataProvider,
        OrderManager,
    )
    from skim.infrastructure.database.base import BaseDatabase
    from skim.infrastructure.database.historical import HistoricalDataService
    from skim.trading.core.config import Config
    from skim.trading.notifications.discord import DiscordNotifier


@dataclass
class TradingContext:
    """Trading-specific context providing all dependencies to a trading strategy.

    This class aggregates all dependencies required by trading strategies,
    including database access, broker connections, repositories, and notifications.
    """

    database: "BaseDatabase"
    repository: "CandidateRepository"
    notifier: "DiscordNotifier"
    config: "Config"
    market_data: "MarketDataProvider"
    order_service: "OrderManager"
    scanner_service: "GapScannerService"
    connection_manager: "BrokerConnectionManager"
    historical_service: "HistoricalDataService | None" = None
