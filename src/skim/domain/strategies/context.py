"""Strategy context providing all dependencies to a strategy"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    pass

from skim.domain.repositories import CandidateRepository
from skim.domain.repositories.position import PositionRepository
from skim.infrastructure.brokers.protocols import (
    BrokerConnectionManager,
    GapScannerService,
    MarketDataProvider,
    OrderManager,
)
from skim.infrastructure.database.historical import HistoricalDataService


class Notifier(Protocol):
    """Protocol for notification services"""

    def alert(self, message: str) -> None:
        """Send an alert"""
        ...

    def notify_trade(self, trade_info: dict) -> None:
        """Notify of a trade"""
        ...


class ConfigProvider(Protocol):
    """Protocol for configuration access"""

    @property
    def paper_trading(self) -> bool: ...

    @property
    def max_position_size(self) -> int: ...


@dataclass
class StrategyContext:
    """Context object providing all services a strategy needs.

    This dataclass aggregates all dependencies a strategy requires,
    simplifying constructor signatures and making testing easier.
    """

    database: object
    repository: CandidateRepository
    position_repository: PositionRepository
    notifier: Notifier
    config: ConfigProvider
    market_data: MarketDataProvider
    order_service: OrderManager
    scanner_service: GapScannerService
    connection_manager: BrokerConnectionManager
    historical_service: HistoricalDataService | None = None
