"""Data models for historical price data - SQLModel."""

from datetime import date
from typing import TYPE_CHECKING

from sqlmodel import Field, SQLModel

if TYPE_CHECKING:
    pass


class DailyPriceBase(SQLModel):
    """Base model for daily price data."""

    ticker: str = Field(index=True)
    trade_date: date = Field(index=True)
    open: float
    high: float
    low: float
    close: float
    volume: int


class DailyPrice(DailyPriceBase, table=True):
    """Historical daily price data for ASX stocks (database table)."""

    __tablename__ = "daily_prices"  # type: ignore[assignment]

    id: int | None = Field(default=None, primary_key=True)

    __table_args__ = ({"sqlite_autoincrement": True},)


class HistoricalPerformance(SQLModel):
    """Historical performance metrics for a stock over a period."""

    ticker: str
    period_days: int
    start_date: date
    end_date: date
    start_close: float
    end_close: float
    return_percent: float
    avg_daily_volume: int
    trading_days: int
