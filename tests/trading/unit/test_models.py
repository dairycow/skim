"""Unit tests for data models - simplified design"""

from skim.trading.data.models import (
    GapStockInPlay,
    MarketData,
    NewsStockInPlay,
    OpeningRange,
    Position,
    TradeableCandidate,
)


def test_gap_stock_in_play_creation():
    """Test creating GapStockInPlay directly"""
    candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )

    assert candidate.ticker == "BHP"
    assert candidate.gap_percent == 5.0
    assert candidate.scan_date == "2025-11-03"
    assert candidate.status == "watching"


def test_news_stock_in_play_creation():
    """Test creating NewsStockInPlay directly"""
    candidate = NewsStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )

    assert candidate.ticker == "BHP"
    assert candidate.headline == "Results Released"
    assert candidate.scan_date == "2025-11-03"
    assert candidate.status == "watching"


def test_opening_range_creation():
    """Test creating OpeningRange directly"""
    opening_range = OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:05:00",
    )

    assert opening_range.ticker == "BHP"
    assert opening_range.or_high == 47.80
    assert opening_range.or_low == 45.90
    assert opening_range.sample_date == "2025-11-03T10:05:00"


def test_tradeable_candidate_creation():
    """Test creating TradeableCandidate directly"""
    candidate = TradeableCandidate(
        ticker="BHP",
        scan_date="2025-11-03T10:00:00",
        status="watching",
        gap_percent=5.0,
        conid=8644,
        headline="Results Released",
        or_high=47.80,
        or_low=45.90,
    )

    assert candidate.ticker == "BHP"
    assert candidate.gap_percent == 5.0
    assert candidate.headline == "Results Released"
    assert candidate.or_high == 47.80
    assert candidate.or_low == 45.90


def test_market_data_creation():
    """Test creating MarketData"""
    data = MarketData(
        ticker="BHP",
        conid="8644",
        last_price=46.05,
        high=47.00,
        low=45.50,
        bid=46.00,
        ask=46.10,
        bid_size=100,
        ask_size=200,
        volume=1_000_000,
        open=46.50,
        prior_close=45.80,
        change_percent=0.54,
    )

    assert data.ticker == "BHP"
    assert data.mid_price == 46.05  # (46.00 + 46.10) / 2


def test_position_creation():
    """Test creating Position"""
    position = Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
        status="open",
    )

    assert position.ticker == "BHP"
    assert position.quantity == 100
    assert position.entry_price == 46.50
    assert position.stop_loss == 43.00
    assert position.status == "open"


def test_position_is_open():
    """Test Position.is_open property"""
    pos_open = Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03",
        status="open",
    )

    pos_closed = Position(
        ticker="RIO",
        quantity=50,
        entry_price=120.00,
        stop_loss=115.00,
        entry_date="2025-11-03",
        status="closed",
    )

    assert pos_open.is_open is True
    assert pos_closed.is_open is False


def test_candidate_status_transitions():
    """Test candidate status transitions through workflow"""
    # Start as watching
    candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03T10:00:00",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )

    assert candidate.status == "watching"

    # Create new instance with entered status
    entered = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03T10:00:00",
        status="entered",
        gap_percent=5.0,
        conid=8644,
    )

    assert entered.status == "entered"

    # Create new instance with closed status
    closed = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03T10:00:00",
        status="closed",
        gap_percent=5.0,
        conid=8644,
    )

    assert closed.status == "closed"


def test_position_status_transitions():
    """Test position status transitions"""
    # Open position
    open_pos = Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
        status="open",
    )

    assert open_pos.status == "open"
    assert open_pos.is_open is True

    # Closed position
    closed_pos = Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
        status="closed",
        exit_price=44.00,
        exit_date="2025-11-03T11:00:00",
    )

    assert closed_pos.status == "closed"
    assert closed_pos.is_open is False
    assert closed_pos.exit_price == 44.00
    assert closed_pos.exit_date == "2025-11-03T11:00:00"
