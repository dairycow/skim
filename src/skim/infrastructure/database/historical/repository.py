"""Historical data repository for price history queries."""

from __future__ import annotations

from datetime import date as datetime_date
from datetime import timedelta
from typing import TYPE_CHECKING, cast

from loguru import logger
from sqlalchemy import and_, asc, desc, select
from sqlmodel import func

from skim.infrastructure.database.base import BaseDatabase
from skim.infrastructure.database.historical.models import (
    DailyPrice,
    HistoricalPerformance,
)

if TYPE_CHECKING:
    pass


class HistoricalDatabase(BaseDatabase):
    """SQLite database manager for historical price data."""

    def __init__(self, db_path: str):
        """Initialise database connection and create schema.

        Args:
            db_path: Path to SQLite database file or ":memory:" for in-memory DB
        """
        super().__init__(db_path)
        logger.info(f"Historical database initialised: {db_path}")

    def _create_schema(self) -> None:
        """Create database tables if they don't exist."""
        DailyPrice.metadata.create_all(self.engine)


class HistoricalDataRepository:
    """Repository for historical price data queries."""

    def __init__(self, db: HistoricalDatabase):
        """Initialise historical data repository.

        Args:
            db: HistoricalDatabase instance for database operations
        """
        self.db = db

    def get_latest_date(self) -> datetime_date | None:
        """Get the most recent date in the database.

        Returns:
            Latest date or None if database is empty
        """
        with self.db.get_session() as session:
            result = session.exec(
                select(DailyPrice.trade_date).order_by(  # type: ignore[arg-type]
                    desc(DailyPrice.trade_date)  # type: ignore[arg-type]
                )
            ).first()
            return cast(datetime_date | None, result[0]) if result else None

    def get_earliest_date(self) -> datetime_date | None:
        """Get the earliest date in the database.

        Returns:
            Earliest date or None if database is empty
        """
        with self.db.get_session() as session:
            result = session.exec(
                select(DailyPrice.trade_date).order_by(  # type: ignore[arg-type]
                    asc(DailyPrice.trade_date)  # type: ignore[arg-type]
                )
            ).first()
            return cast(datetime_date | None, result[0]) if result else None

    def get_tickers_with_data(self) -> list[str]:
        """Get all tickers that have data in the database.

        Returns:
            List of ticker symbols
        """
        with self.db.get_session() as session:
            stmt = (
                select(DailyPrice.ticker).distinct().order_by(DailyPrice.ticker)  # type: ignore[arg-type]
            )
            result = session.execute(stmt).scalars().all()
            return list(result)

    def get_price_on_date(
        self, ticker: str, target_date: datetime_date
    ) -> DailyPrice | None:
        """Get price data for a specific ticker on a specific date.

        Args:
            ticker: Stock ticker symbol
            target_date: Date to query

        Returns:
            DailyPrice record or None if not found
        """
        with self.db.get_session() as session:
            result = session.execute(
                select(DailyPrice).where(  # type: ignore[arg-type]
                    and_(
                        DailyPrice.ticker == ticker.upper(),
                        DailyPrice.trade_date == target_date,
                    )
                )
            ).scalar_one_or_none()
            return result

    def get_prices_in_range(
        self, ticker: str, start_date: datetime_date, end_date: datetime_date
    ) -> list[DailyPrice]:
        """Get price data for a ticker within a date range.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            List of DailyPrice records sorted by date
        """
        with self.db.get_session() as session:
            results = (
                session.execute(
                    select(DailyPrice)
                    .where(  # type: ignore[arg-type]
                        (DailyPrice.ticker == ticker.upper())
                        & (DailyPrice.trade_date >= start_date)
                        & (DailyPrice.trade_date <= end_date)
                    )
                    .order_by(asc(DailyPrice.trade_date))  # type: ignore[arg-type]
                )
                .scalars()
                .all()
            )
            return list(results)

    def get_performance(
        self, ticker: str, days: int, end_date: datetime_date | None = None
    ) -> HistoricalPerformance | None:
        """Calculate historical performance over a period.

        Args:
            ticker: Stock ticker symbol
            days: Number of days to look back
            end_date: End date for calculation (defaults to latest available)

        Returns:
            HistoricalPerformance object or None if insufficient data
        """
        if end_date is None:
            end_date = self.get_latest_date()
            if end_date is None:
                return None

        start_date = end_date - timedelta(days=days)

        with self.db.get_session() as session:
            prices = (
                session.execute(
                    select(DailyPrice)
                    .where(  # type: ignore[arg-type]
                        (DailyPrice.ticker == ticker.upper())
                        & (DailyPrice.trade_date >= start_date)
                        & (DailyPrice.trade_date <= end_date)
                    )
                    .order_by(asc(DailyPrice.trade_date))  # type: ignore[arg-type]
                )
                .scalars()
                .all()
            )

            if len(prices) < 2:
                logger.debug(
                    f"Insufficient data for {ticker}: {len(prices)} days in range"
                )
                return None

            first_price = prices[0]
            last_price = prices[-1]

            start_close = float(first_price.close)
            end_close = float(last_price.close)

            if start_close == 0:
                return None

            return_percent = ((end_close - start_close) / start_close) * 100

            avg_volume = int(sum(p.volume for p in prices) / len(prices))

            return HistoricalPerformance(
                ticker=ticker.upper(),
                period_days=days,
                start_date=first_price.trade_date,
                end_date=last_price.trade_date,
                start_close=start_close,
                end_close=end_close,
                return_percent=return_percent,
                avg_daily_volume=avg_volume,
                trading_days=len(prices),
            )

    def get_3month_performance(
        self, ticker: str, end_date: datetime_date | None = None
    ) -> HistoricalPerformance | None:
        """Get 3-month (approximately 90 days) performance.

        Args:
            ticker: Stock ticker symbol
            end_date: End date for calculation

        Returns:
            HistoricalPerformance for 3-month period
        """
        return self.get_performance(ticker, 90, end_date)

    def get_6month_performance(
        self, ticker: str, end_date: datetime_date | None = None
    ) -> HistoricalPerformance | None:
        """Get 6-month (approximately 180 days) performance.

        Args:
            ticker: Stock ticker symbol
            end_date: End date for calculation

        Returns:
            HistoricalPerformance for 6-month period
        """
        return self.get_performance(ticker, 180, end_date)

    def bulk_insert_prices(self, prices: list[DailyPrice]) -> int:
        """Bulk insert daily price records.

        Args:
            prices: List of DailyPrice objects to insert

        Returns:
            Number of records inserted
        """
        if not prices:
            return 0

        with self.db.get_session() as session:
            for price in prices:
                existing = session.execute(
                    select(DailyPrice).where(  # type: ignore[arg-type]
                        (DailyPrice.ticker == price.ticker)
                        & (DailyPrice.trade_date == price.trade_date)
                    )
                ).scalar_one_or_none()

                if existing:
                    existing.open = price.open
                    existing.high = price.high
                    existing.low = price.low
                    existing.close = price.close
                    existing.volume = price.volume
                else:
                    session.add(price)

            session.commit()
            return len(prices)

    def delete_ticker_data(self, ticker: str) -> int:
        """Delete all data for a specific ticker.

        Args:
            ticker: Stock ticker symbol

        Returns:
            Number of records deleted
        """
        with self.db.get_session() as session:
            result = (
                session.execute(
                    select(DailyPrice).where(  # type: ignore[arg-type]
                        DailyPrice.ticker == ticker.upper()
                    )
                )
                .scalars()
                .all()
            )
            count = len(result)
            for price in result:
                session.delete(price)
            session.commit()
            return count

    def get_tickers_count(self) -> int:
        """Get total number of unique tickers.

        Returns:
            Number of unique tickers
        """
        with self.db.get_session() as session:
            result = session.exec(
                select(DailyPrice.ticker).distinct().order_by(DailyPrice.ticker)  # type: ignore[arg-type]
            ).all()
            return len(result)

    def get_total_records(self) -> int:
        """Get total number of price records.

        Returns:
            Total number of records
        """
        with self.db.get_session() as session:
            result = session.exec(  # type: ignore[arg-type]
                select(func.count()).select_from(DailyPrice)  # type: ignore[arg-type]
            ).first()
            return int(result[0]) if result and result[0] is not None else 0
