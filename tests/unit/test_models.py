"""Unit tests for data models"""

from datetime import datetime

from skim.data.models import Candidate, MarketData, Position, Trade


def test_candidate_from_db_row():
    """Test creating Candidate from database row"""
    row = {
        "ticker": "BHP",
        "headline": "Strong earnings",
        "scan_date": "2025-11-03",
        "status": "watching",
        "gap_percent": 3.5,
        "prev_close": 45.20,
        "created_at": "2025-11-03T09:00:00",
    }

    candidate = Candidate.from_db_row(row)

    assert candidate.ticker == "BHP"
    assert candidate.headline == "Strong earnings"
    assert candidate.gap_percent == 3.5
    assert candidate.status == "watching"


def test_position_from_db_row():
    """Test creating Position from database row"""
    row = {
        "id": 1,
        "ticker": "BHP",
        "quantity": 100,
        "entry_price": 46.50,
        "stop_loss": 43.00,
        "entry_date": "2025-11-03T10:15:00",
        "status": "open",
        "half_sold": 0,
        "exit_date": None,
        "exit_price": None,
        "created_at": "2025-11-03T10:15:00",
    }

    position = Position.from_db_row(row)

    assert position.id == 1
    assert position.ticker == "BHP"
    assert position.quantity == 100
    assert position.status == "open"
    assert position.half_sold is False


def test_position_is_open():
    """Test Position.is_open property"""
    pos1 = Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03",
        status="open",
    )

    pos2 = Position(
        ticker="RIO",
        quantity=50,
        entry_price=120.00,
        stop_loss=115.00,
        entry_date="2025-11-03",
        status="half_exited",
    )

    pos3 = Position(
        ticker="FMG",
        quantity=200,
        entry_price=18.00,
        stop_loss=16.50,
        entry_date="2025-11-03",
        status="closed",
    )

    assert pos1.is_open is True
    assert pos2.is_open is True
    assert pos3.is_open is False


def test_position_days_held():
    """Test Position.days_held calculation"""
    # Create position from 5 days ago
    five_days_ago = datetime.now().replace(
        hour=10, minute=0, second=0, microsecond=0
    )
    five_days_ago = five_days_ago.replace(
        day=five_days_ago.day - 5
    ).isoformat()

    position = Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date=five_days_ago,
        status="open",
    )

    # Should be approximately 5 days (may be 4 or 5 depending on time of day)
    assert position.days_held >= 4
    assert position.days_held <= 5


def test_trade_from_db_row():
    """Test creating Trade from database row"""
    row = {
        "id": 1,
        "ticker": "BHP",
        "action": "BUY",
        "quantity": 100,
        "price": 46.50,
        "timestamp": "2025-11-03T10:15:00",
        "position_id": 1,
        "pnl": None,
        "notes": "Entry trade",
    }

    trade = Trade.from_db_row(row)

    assert trade.id == 1
    assert trade.ticker == "BHP"
    assert trade.action == "BUY"
    assert trade.quantity == 100
    assert trade.price == 46.50


def test_market_data_mid_price():
    """Test MarketData.mid_price calculation"""
    data = MarketData(
        ticker="BHP",
        bid=46.00,
        ask=46.10,
        last=46.05,
        high=47.00,
        low=45.50,
        volume=1_000_000,
        timestamp=datetime.now(),
    )

    assert data.mid_price == 46.05  # (46.00 + 46.10) / 2
