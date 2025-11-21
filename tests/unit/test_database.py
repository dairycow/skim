"""Unit tests for database operations"""

import pytest

from skim.data.models import Candidate


def test_database_init(test_db):
    """Test database initialization creates schema"""
    # Should not raise any exceptions
    assert test_db.db is not None


def test_save_and_get_candidate(test_db, sample_candidate):
    """Test saving and retrieving a candidate"""
    test_db.save_candidate(sample_candidate)

    retrieved = test_db.get_candidate("BHP")
    assert retrieved is not None
    assert retrieved.ticker == "BHP"
    assert retrieved.gap_percent == 3.5
    assert retrieved.status == "watching"
    # Test enhanced market data fields
    assert retrieved.open_price == 46.50
    assert retrieved.session_high == 47.80
    assert retrieved.session_low == 45.90
    assert retrieved.volume == 1500000
    assert retrieved.bid == 46.95
    assert retrieved.ask == 47.05
    assert retrieved.market_data_timestamp == "2025-11-03T10:15:30"


def test_get_nonexistent_candidate(test_db):
    """Test getting a candidate that doesn't exist"""
    result = test_db.get_candidate("NONEXISTENT")
    assert result is None


@pytest.mark.parametrize(
    "target_status,method_name,expected_tickers",
    [
        ("watching", "get_watching_candidates", {"BHP", "FMG"}),
        ("triggered", "get_triggered_candidates", {"RIO"}),
    ],
)
def test_get_candidates_by_status(
    test_db, target_status, method_name, expected_tickers
):
    """Test retrieving candidates by status (parameterized)"""
    # Create multiple candidates with different statuses
    cand1 = Candidate(
        ticker="BHP",
        headline="Test 1",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=3.5,
        prev_close=45.20,
    )
    cand2 = Candidate(
        ticker="RIO",
        headline="Test 2",
        scan_date="2025-11-03",
        status="triggered",
        gap_percent=4.2,
        prev_close=120.50,
    )
    cand3 = Candidate(
        ticker="FMG",
        headline="Test 3",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=3.8,
        prev_close=18.90,
    )

    test_db.save_candidate(cand1)
    test_db.save_candidate(cand2)
    test_db.save_candidate(cand3)

    # Call the appropriate method dynamically
    method = getattr(test_db, method_name)
    results = method()

    assert len(results) == len(expected_tickers)
    assert all(c.status == target_status for c in results)
    assert {c.ticker for c in results} == expected_tickers


def test_update_candidate_status(test_db, sample_candidate):
    """Test updating candidate status"""
    test_db.save_candidate(sample_candidate)

    test_db.update_candidate_status("BHP", "triggered", gap_percent=4.0)

    updated = test_db.get_candidate("BHP")
    assert updated.status == "triggered"
    assert updated.gap_percent == 4.0


def test_update_candidate_status_without_gap(test_db, sample_candidate):
    """Test updating candidate status without changing gap percent"""
    test_db.save_candidate(sample_candidate)

    test_db.update_candidate_status("BHP", "entered")

    updated = test_db.get_candidate("BHP")
    assert updated.status == "entered"
    assert updated.gap_percent == 3.5  # Unchanged


def test_count_watching_candidates(test_db):
    """Test counting watching candidates"""
    cand1 = Candidate(
        ticker="BHP",
        headline="Test",
        scan_date="2025-11-03",
        status="watching",
    )
    cand2 = Candidate(
        ticker="RIO",
        headline="Test",
        scan_date="2025-11-03",
        status="watching",
    )
    cand3 = Candidate(
        ticker="FMG",
        headline="Test",
        scan_date="2025-11-03",
        status="triggered",
    )

    test_db.save_candidate(cand1)
    test_db.save_candidate(cand2)
    test_db.save_candidate(cand3)

    count = test_db.count_watching_candidates()
    assert count == 2


def test_create_position(test_db):
    """Test creating a new position"""
    position_id = test_db.create_position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
    )

    assert position_id > 0

    # Verify it was saved
    positions = test_db.get_open_positions()
    assert len(positions) == 1
    assert positions[0].ticker == "BHP"
    assert positions[0].quantity == 100


def test_get_open_positions(test_db):
    """Test retrieving open and half-exited positions"""
    test_db.create_position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
    )

    pos_id = test_db.create_position(
        ticker="RIO",
        quantity=50,
        entry_price=120.00,
        stop_loss=115.00,
        entry_date="2025-11-03T10:20:00",
    )

    # Close one position
    test_db.update_position_exit(
        pos_id, "closed", 125.00, "2025-11-03T15:00:00"
    )

    open_positions = test_db.get_open_positions()
    assert len(open_positions) == 1
    assert open_positions[0].ticker == "BHP"


def test_count_open_positions(test_db):
    """Test counting open positions"""
    test_db.create_position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
    )

    test_db.create_position(
        ticker="RIO",
        quantity=50,
        entry_price=120.00,
        stop_loss=115.00,
        entry_date="2025-11-03T10:20:00",
    )

    count = test_db.count_open_positions()
    assert count == 2


def test_save_candidate_with_enhanced_market_data(test_db):
    """Test saving candidate with enhanced market data fields"""
    candidate = Candidate(
        ticker="RIO",
        headline="Gap detected: 4.20%",
        scan_date="2025-11-03T10:00:00",
        status="watching",
        gap_percent=4.2,
        prev_close=120.50,
        conid=8645,
        source="ibkr",
        # Enhanced market data fields
        open_price=122.00,
        session_high=124.50,
        session_low=119.80,
        volume=980000,
        bid=123.95,
        ask=124.05,
        market_data_timestamp="2025-11-03T10:20:15",
    )

    test_db.save_candidate(candidate)

    retrieved = test_db.get_candidate("RIO")
    assert retrieved is not None
    assert retrieved.ticker == "RIO"
    assert retrieved.open_price == 122.00
    assert retrieved.session_high == 124.50
    assert retrieved.session_low == 119.80
    assert retrieved.volume == 980000
    assert retrieved.bid == 123.95
    assert retrieved.ask == 124.05
    assert retrieved.market_data_timestamp == "2025-11-03T10:20:15"


def test_save_candidate_without_enhanced_market_data(test_db):
    """Test saving candidate without enhanced market data fields (backward compatibility)"""
    candidate = Candidate(
        ticker="FMG",
        headline="Gap detected: 2.80%",
        scan_date="2025-11-03T10:00:00",
        status="watching",
        gap_percent=2.8,
        prev_close=18.90,
        # No enhanced market data fields
    )

    test_db.save_candidate(candidate)

    retrieved = test_db.get_candidate("FMG")
    assert retrieved is not None
    assert retrieved.ticker == "FMG"
    # Enhanced fields should be None
    assert retrieved.open_price is None
    assert retrieved.session_high is None
    assert retrieved.session_low is None
    assert retrieved.volume is None
    assert retrieved.bid is None
    assert retrieved.ask is None
    assert retrieved.market_data_timestamp is None


def test_update_position_exit(test_db):
    """Test updating position with exit information"""
    pos_id = test_db.create_position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
    )

    test_db.update_position_exit(pos_id, "closed", 48.00, "2025-11-03T15:00:00")

    # Should not be in open positions anymore
    open_positions = test_db.get_open_positions()
    assert len(open_positions) == 0


def test_update_position_half_sold(test_db):
    """Test updating position half_sold flag"""
    pos_id = test_db.create_position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
    )

    test_db.update_position_half_sold(pos_id, True)

    positions = test_db.get_open_positions()
    assert positions[0].half_sold is True


def test_create_trade(test_db):
    """Test creating a trade record"""
    trade_id = test_db.create_trade(
        ticker="BHP",
        action="BUY",
        quantity=100,
        price=46.50,
        position_id=1,
        pnl=None,
        notes="Entry trade",
    )

    assert trade_id > 0


def test_create_trade_with_pnl(test_db):
    """Test creating a trade with PnL"""
    trade_id = test_db.create_trade(
        ticker="BHP",
        action="SELL",
        quantity=50,
        price=48.00,
        position_id=1,
        pnl=75.00,
        notes="Half exit",
    )

    assert trade_id > 0


def test_get_total_pnl_empty(test_db):
    """Test getting total PnL with no trades"""
    total = test_db.get_total_pnl()
    assert total == 0.0


def test_get_total_pnl_with_trades(test_db):
    """Test getting total PnL with multiple trades"""
    test_db.create_trade(
        ticker="BHP", action="SELL", quantity=50, price=48.00, pnl=75.00
    )

    test_db.create_trade(
        ticker="RIO", action="SELL", quantity=20, price=125.00, pnl=100.00
    )

    test_db.create_trade(
        ticker="FMG", action="SELL", quantity=100, price=17.50, pnl=-50.00
    )

    total = test_db.get_total_pnl()
    assert total == 125.00  # 75 + 100 - 50


@pytest.mark.parametrize(
    "target_status,method_name,expected_tickers",
    [
        ("or_tracking", "get_or_tracking_candidates", {"BHP", "FMG"}),
        ("orh_breakout", "get_orh_breakout_candidates", {"RIO"}),
    ],
)
def test_get_or_candidates_by_status(
    test_db, target_status, method_name, expected_tickers
):
    """Test retrieving OR-related candidates by status (parameterized)"""
    # Create candidates with different statuses
    cand1 = Candidate(
        ticker="BHP",
        headline="Test 1",
        scan_date="2025-11-03",
        status="or_tracking",
        gap_percent=3.5,
        prev_close=45.20,
    )
    cand2 = Candidate(
        ticker="RIO",
        headline="Test 2",
        scan_date="2025-11-03",
        status="orh_breakout",
        gap_percent=4.2,
        prev_close=120.50,
    )
    cand3 = Candidate(
        ticker="FMG",
        headline="Test 3",
        scan_date="2025-11-03",
        status="or_tracking",
        gap_percent=3.8,
        prev_close=18.90,
    )

    test_db.save_candidate(cand1)
    test_db.save_candidate(cand2)
    test_db.save_candidate(cand3)

    # Call the appropriate method dynamically
    method = getattr(test_db, method_name)
    results = method()

    assert len(results) == len(expected_tickers)
    assert all(c.status == target_status for c in results)
    assert {c.ticker for c in results} == expected_tickers


def test_update_candidate_or_data(test_db, sample_candidate):
    """Test updating candidate OR tracking data"""
    test_db.save_candidate(sample_candidate)

    test_db.update_candidate_or_data(
        "BHP", or_high=47.50, or_low=44.80, or_timestamp="2025-11-03T10:30:00"
    )

    updated = test_db.get_candidate("BHP")
    assert updated.or_high == 47.50
    assert updated.or_low == 44.80
    assert updated.or_timestamp == "2025-11-03T10:30:00"


def test_update_candidate_or_data_nonexistent(test_db):
    """Test updating OR data for non-existent candidate"""
    # Should not raise an exception
    test_db.update_candidate_or_data(
        "NONEXISTENT",
        or_high=47.50,
        or_low=44.80,
        or_timestamp="2025-11-03T10:30:00",
    )


def test_get_or_tracking_candidates_empty(test_db):
    """Test getting OR tracking candidates when none exist"""
    or_tracking = test_db.get_or_tracking_candidates()
    assert or_tracking == []


def test_get_orh_breakout_candidates_empty(test_db):
    """Test getting ORH breakout candidates when none exist"""
    breakout = test_db.get_orh_breakout_candidates()
    assert breakout == []


def test_update_candidate_or_data_validation(test_db, sample_candidate):
    """Test validation in update_candidate_or_data"""
    test_db.save_candidate(sample_candidate)

    # Test or_high <= or_low validation
    import pytest

    with pytest.raises(
        ValueError, match="or_high .* must be greater than or_low"
    ):
        test_db.update_candidate_or_data(
            "BHP",
            or_high=45.00,
            or_low=45.00,  # Equal to or_high
            or_timestamp="2025-11-03T10:30:00",
        )

    with pytest.raises(
        ValueError, match="or_high .* must be greater than or_low"
    ):
        test_db.update_candidate_or_data(
            "BHP",
            or_high=44.00,
            or_low=45.00,  # Greater than or_high
            or_timestamp="2025-11-03T10:30:00",
        )

    # Test empty timestamp validation
    with pytest.raises(ValueError, match="or_timestamp cannot be empty"):
        test_db.update_candidate_or_data(
            "BHP",
            or_high=47.50,
            or_low=44.80,
            or_timestamp="",  # Empty
        )
