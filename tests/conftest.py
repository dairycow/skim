"""Pytest fixtures for Skim trading bot tests"""

from datetime import datetime

import pytest

from skim.data.database import Database
from skim.data.models import Candidate, MarketData, Position, Trade


@pytest.fixture
def test_db():
    """In-memory SQLite database for testing"""
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture
def sample_candidate() -> Candidate:
    """Sample candidate for testing"""
    return Candidate(
        ticker="BHP",
        headline="Strong earnings report",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=3.5,
        prev_close=45.20,
    )


@pytest.fixture
def sample_position() -> Position:
    """Sample open position for testing"""
    return Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
        status="open",
        half_sold=False,
    )


@pytest.fixture
def sample_trade() -> Trade:
    """Sample trade for testing"""
    return Trade(
        ticker="BHP",
        action="BUY",
        quantity=100,
        price=46.50,
        timestamp="2025-11-03T10:15:00",
        position_id=1,
    )


@pytest.fixture
def sample_market_data() -> MarketData:
    """Sample market data for testing"""
    return MarketData(
        ticker="BHP",
        bid=46.00,
        ask=46.10,
        last=46.05,
        high=47.00,
        low=45.50,
        volume=1_000_000,
        timestamp=datetime.now(),
    )
