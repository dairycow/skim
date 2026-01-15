"""Test data factories for creating domain models with proper value objects"""

from datetime import datetime

from skim.domain.models import (
    GapCandidate,
    MarketData,
    NewsCandidate,
    Position,
    Price,
    Ticker,
)


class CandidateFactory:
    """Factory for creating test candidates"""

    @staticmethod
    def gap_candidate(
        ticker: str = "BHP",
        scan_date: datetime | None = None,
        gap_percent: float = 5.0,
        conid: int | None = 8644,
        status: str = "watching",
        strategy_name: str = "",
    ) -> GapCandidate:
        return GapCandidate(
            ticker=Ticker(ticker),
            scan_date=scan_date or datetime(2025, 11, 3),
            gap_percent=gap_percent,
            conid=conid,
            status=status,
            strategy_name=strategy_name,
        )

    @staticmethod
    def news_candidate(
        ticker: str = "BHP",
        scan_date: datetime | None = None,
        headline: str = "Results Released",
        announcement_type: str = "pricesens",
        announcement_timestamp: datetime | None = None,
        status: str = "watching",
        strategy_name: str = "",
    ) -> NewsCandidate:
        return NewsCandidate(
            ticker=Ticker(ticker),
            scan_date=scan_date or datetime(2025, 11, 3),
            headline=headline,
            announcement_type=announcement_type,
            announcement_timestamp=announcement_timestamp
            or datetime(2025, 11, 3),
            status=status,
            strategy_name=strategy_name,
        )


class PositionFactory:
    """Factory for creating test positions"""

    @staticmethod
    def position(
        ticker: str = "BHP",
        quantity: int = 100,
        entry_price: float = 46.50,
        stop_loss: float = 43.00,
        entry_date: datetime | None = None,
        status: str = "open",
        exit_price: float | None = None,
        exit_date: datetime | None = None,
        id: int | None = None,
    ) -> Position:
        now = entry_date or datetime(2025, 11, 3, 10, 15)
        return Position(
            ticker=Ticker(ticker),
            quantity=quantity,
            entry_price=Price(value=entry_price, timestamp=now),
            stop_loss=Price(value=stop_loss, timestamp=now),
            entry_date=now,
            status=status,
            exit_price=Price(value=exit_price, timestamp=exit_date or now)
            if exit_price
            else None,
            exit_date=exit_date,
            id=id,
        )


class MarketDataFactory:
    """Factory for creating test market data"""

    @staticmethod
    def market_data(
        ticker: str = "BHP",
        conid: str = "8644",
        last_price: float = 46.05,
        high: float = 47.00,
        low: float = 45.50,
        bid: float = 46.00,
        ask: float = 46.10,
        bid_size: int = 100,
        ask_size: int = 200,
        volume: int = 1_000_000,
        open_price: float = 46.50,
        prior_close: float = 45.80,
        change_percent: float = 0.54,
    ) -> MarketData:
        return MarketData(
            ticker=ticker,
            conid=conid,
            last_price=last_price,
            high=high,
            low=low,
            bid=bid,
            ask=ask,
            bid_size=bid_size,
            ask_size=ask_size,
            volume=volume,
            open=open_price,
            prior_close=prior_close,
            change_percent=change_percent,
        )
