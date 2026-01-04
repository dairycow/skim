"""Data models for Skim trading bot - SQLModel"""

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import (
    Field,
    Relationship,
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


class OpeningRangeBase(SQLModel):
    """Base model for OpeningRange"""

    ticker: str
    or_high: float
    or_low: float
    sample_date: str


class OpeningRange(OpeningRangeBase, table=True):
    """Opening range high/low for a candidate (database table)"""

    __tablename__ = "opening_ranges"

    ticker: str = Field(foreign_key="candidates.ticker", primary_key=True)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    candidate: Optional["Candidate"] = Relationship(
        back_populates="opening_range"
    )


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

    __tablename__ = "positions"

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


class Candidate(CandidateBase, table=True):
    """Candidate for trading (database table)"""

    __tablename__ = "candidates"

    gap_percent: float | None = None
    conid: int | None = None
    headline: str | None = None
    announcement_type: str = "pricesens"
    announcement_timestamp: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    opening_range: OpeningRange | None = Relationship(
        back_populates="candidate"
    )


OpeningRange.model_rebuild()
