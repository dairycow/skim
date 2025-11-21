"""Data models for Skim trading bot - simplified"""

from dataclasses import dataclass


@dataclass
class Candidate:
    """Stock candidate with opening range data"""

    ticker: str
    or_high: float
    or_low: float
    scan_date: str
    status: str  # 'watching' | 'entered' | 'closed'

    @classmethod
    def from_db_row(cls, row: dict) -> "Candidate":
        """Create from database row"""
        return cls(
            ticker=row["ticker"],
            or_high=row["or_high"],
            or_low=row["or_low"],
            scan_date=row["scan_date"],
            status=row["status"],
        )


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
