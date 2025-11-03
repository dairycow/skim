"""Data models for Skim trading bot"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Candidate:
    """Stock candidate identified by scanner"""

    ticker: str
    headline: str
    scan_date: str
    status: str  # watching, triggered, expired
    gap_percent: float | None = None
    prev_close: float | None = None
    created_at: str | None = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Candidate":
        """Create Candidate from database row dictionary"""
        return cls(
            ticker=row["ticker"],
            headline=row["headline"],
            scan_date=row["scan_date"],
            status=row["status"],
            gap_percent=row.get("gap_percent"),
            prev_close=row.get("prev_close"),
            created_at=row.get("created_at"),
        )


@dataclass
class Position:
    """Open trading position"""

    ticker: str
    quantity: int
    entry_price: float
    stop_loss: float
    entry_date: str
    status: str  # open, half_exited, closed
    half_sold: bool | int = False
    exit_date: str | None = None
    exit_price: float | None = None
    id: int | None = None
    created_at: str | None = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Position":
        """Create Position from database row dictionary"""
        # Convert 0/1 to False/True for half_sold
        half_sold = bool(row.get("half_sold", 0))

        return cls(
            id=row.get("id"),
            ticker=row["ticker"],
            quantity=row["quantity"],
            entry_price=row["entry_price"],
            stop_loss=row["stop_loss"],
            entry_date=row["entry_date"],
            status=row["status"],
            half_sold=half_sold,
            exit_date=row.get("exit_date"),
            exit_price=row.get("exit_price"),
            created_at=row.get("created_at"),
        )

    @property
    def is_open(self) -> bool:
        """Check if position is still open (open or half_exited)"""
        return self.status in ("open", "half_exited")

    @property
    def days_held(self) -> int:
        """Calculate days position has been held"""
        if isinstance(self.entry_date, str):
            entry = datetime.fromisoformat(self.entry_date)
        else:
            entry = self.entry_date

        now = datetime.now()
        delta = now - entry
        return delta.days


@dataclass
class Trade:
    """Individual trade execution"""

    ticker: str
    action: str  # BUY or SELL
    quantity: int
    price: float
    timestamp: str
    position_id: int | None = None
    pnl: float | None = None
    notes: str | None = None
    id: int | None = None

    @classmethod
    def from_db_row(cls, row: dict) -> "Trade":
        """Create Trade from database row dictionary"""
        return cls(
            id=row.get("id"),
            ticker=row["ticker"],
            action=row["action"],
            quantity=row["quantity"],
            price=row["price"],
            timestamp=row["timestamp"],
            position_id=row.get("position_id"),
            pnl=row.get("pnl"),
            notes=row.get("notes"),
        )


@dataclass
class MarketData:
    """Real-time market data snapshot"""

    ticker: str
    bid: float
    ask: float
    last: float
    high: float
    low: float
    volume: int
    timestamp: datetime

    @property
    def mid_price(self) -> float:
        """Calculate mid price from bid/ask"""
        return (self.bid + self.ask) / 2
