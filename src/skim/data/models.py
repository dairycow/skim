"""Data models for Skim trading bot - SQLModel"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import (
    Field,
    SQLModel,
)

if TYPE_CHECKING:
    pass


@dataclass
class StockInPlay:
    """Base class for stocks identified as potential trading opportunities"""

    ticker: str
    scan_date: str
    status: str


@dataclass
class GapStockInPlay(StockInPlay):
    """Stock identified by gap scanner"""

    gap_percent: float
    conid: int | None = None


@dataclass
class NewsStockInPlay(StockInPlay):
    """Stock identified by announcement scanner"""

    headline: str
    announcement_type: str = "pricesens"
    announcement_timestamp: str | None = None


@dataclass
class TradeableCandidate:
    """Combined view of candidate + opening range for trading"""

    ticker: str
    scan_date: str
    status: str
    gap_percent: float
    conid: int | None
    headline: str
    or_high: float
    or_low: float


@dataclass
class OpeningRange:
    """Opening range data (dataclass only, no DB table)"""

    ticker: str
    or_high: float
    or_low: float
    sample_date: str


@dataclass
class MarketData:
    """Real-time market data snapshot"""

    ticker: str
    conid: str
    last_price: float
    high: float
    low: float
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    volume: int
    open: float
    prior_close: float
    change_percent: float

    @property
    def mid_price(self) -> float:
        """Calculate mid price from bid/ask"""
        return (self.bid + self.ask) / 2


@dataclass
class OrderResult:
    """Result of placing an order"""

    order_id: str
    ticker: str
    action: str
    quantity: int
    filled_price: float | None = None
    status: str = "submitted"


class PositionBase(SQLModel):
    """Base model for Position"""

    ticker: str
    quantity: int
    entry_price: float
    stop_loss: float
    entry_date: str
    status: str = "open"


class Position(PositionBase, table=True):
    """Open trading position (database table)"""

    __tablename__ = "positions"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)
    exit_price: float | None = None
    exit_date: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @property
    def is_open(self) -> bool:
        """Check if position is still open"""
        return self.status == "open"


class CandidateBase(SQLModel):
    """Base model for Candidate"""

    ticker: str = Field(primary_key=True)
    scan_date: str
    status: str = "watching"
    strategy_name: str = Field(index=True)


class Candidate(CandidateBase, table=True):
    """Generic candidate for trading (database table)"""

    __tablename__ = "candidates"  # type: ignore[assignment]

    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ORHCandidate(SQLModel, table=True):
    """ORH-specific candidate data"""

    __tablename__ = "orh_candidates"  # type: ignore[assignment]

    ticker: str = Field(primary_key=True, foreign_key="candidates.ticker")
    gap_percent: float | None = None
    conid: int | None = None
    headline: str | None = None
    announcement_type: str = "pricesens"
    announcement_timestamp: str | None = None
    or_high: float | None = None
    or_low: float | None = None
    sample_date: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
