"""Pytest fixtures for Skim trading bot tests"""

from datetime import datetime
from unittest.mock import Mock

import pytest

from skim.data.database import Database
from skim.data.models import Candidate, MarketData, Position, Trade
from skim.brokers.ib_interface import OrderResult


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


@pytest.fixture
def mock_ibind_client(mocker):
    """Mock IBIndClient for testing

    Returns a mock IBIndClient with common success scenarios configured.
    Tests can override specific methods as needed.
    """
    mock_client = mocker.MagicMock()

    # Configure default successful behaviors
    mock_client.is_connected.return_value = True
    mock_client.get_account.return_value = "DU12345"

    # Mock successful market data response
    mock_market_data = Mock(
        ticker="BHP",
        last_price=46.50,
        bid=46.45,
        ask=46.55,
        volume=1_000_000,
    )
    mock_client.get_market_data.return_value = mock_market_data

    # Mock successful order placement
    mock_order_result = OrderResult(
        order_id="order_123",
        ticker="BHP",
        action="BUY",
        quantity=100,
        filled_price=46.50,
        status="filled",
    )
    mock_client.place_order.return_value = mock_order_result

    return mock_client
