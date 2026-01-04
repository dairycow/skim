"""Data models for Skim trading bot - simplified"""

from dataclasses import dataclass


@dataclass
class StockInPlay:
    """Base class for stocks identified as potential trading opportunities"""

    ticker: str
    scan_date: str
    status: str  # 'watching' | 'entered' | 'closed'


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
class OpeningRange:
    """Opening range high/low for a candidate"""

    ticker: str
    or_high: float
    or_low: float
    sample_date: str

    @classmethod
    def from_db_row(cls, row: dict) -> "OpeningRange":
        return cls(
            ticker=row["ticker"],
            or_high=row["or_high"],
            or_low=row["or_low"],
            sample_date=row["sample_date"],
        )


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
class Position:
    """Open trading position"""

    ticker: str
    quantity: int
    entry_price: float
    stop_loss: float
    entry_date: str
    status: str  # 'open' | 'closed'
    id: int | None = None
    exit_price: float | None = None
    exit_date: str | None = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Position":
        """Create from database row"""
        return cls(
            id=row.get("id"),
            ticker=row["ticker"],
            quantity=row["quantity"],
            entry_price=row["entry_price"],
            stop_loss=row["stop_loss"],
            entry_date=row["entry_date"],
            status=row["status"],
            exit_price=row.get("exit_price"),
            exit_date=row.get("exit_date"),
        )

    @property
    def is_open(self) -> bool:
        """Check if position is still open"""
        return self.status == "open"


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
