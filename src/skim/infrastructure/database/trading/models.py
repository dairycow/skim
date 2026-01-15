"""Trading database persistence models (SQLModel tables)"""

from datetime import datetime

from sqlmodel import Field, SQLModel


class PositionTable(SQLModel, table=True):
    """Position database table"""

    __tablename__ = "positions"

    id: int | None = Field(default=None, primary_key=True)
    ticker: str
    quantity: int
    entry_price: float
    stop_loss: float
    entry_date: str
    status: str = "open"
    exit_price: float | None = None
    exit_date: str | None = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CandidateTable(SQLModel, table=True):
    """Candidate database table"""

    __tablename__ = "candidates"

    ticker: str = Field(primary_key=True)
    scan_date: str
    status: str = "watching"
    strategy_name: str = Field(index=True)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class ORHCandidateTable(SQLModel, table=True):
    """ORH-specific candidate data database table"""

    __tablename__ = "orh_candidates"

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
