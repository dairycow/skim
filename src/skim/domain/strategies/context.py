"""Strategy context providing all dependencies to a strategy"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from skim.infrastructure.brokers.protocols import (
        BrokerConnectionManager,
        GapScannerService,
        MarketDataProvider,
        OrderManager,
    )
    from skim.infrastructure.database.historical import HistoricalDataService
    from skim.trading.core.config import Config
    from skim.trading.data.database import Database
    from skim.trading.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )
    from skim.trading.notifications.discord import DiscordNotifier


@dataclass
class StrategyContext:
    """Context object providing all services a strategy needs.

    This dataclass aggregates all dependencies a strategy requires,
    simplifying constructor signatures and making testing easier.
    """

    database: "Database"
    repository: "ORHCandidateRepository"
    notifier: "DiscordNotifier"
    config: "Config"
    market_data: "MarketDataProvider"
    order_service: "OrderManager"
    scanner_service: "GapScannerService"
    connection_manager: "BrokerConnectionManager"
    historical_service: "HistoricalDataService | None" = None
