"""Unit tests for database operations"""

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


def test_get_nonexistent_candidate(test_db):
    """Test getting a candidate that doesn't exist"""
    result = test_db.get_candidate("NONEXISTENT")
    assert result is None


def test_get_watching_candidates(test_db):
    """Test retrieving candidates with status='watching'"""
    # Create multiple candidates
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

    watching = test_db.get_watching_candidates()
    assert len(watching) == 2
    assert all(c.status == "watching" for c in watching)
    assert {c.ticker for c in watching} == {"BHP", "FMG"}


def test_get_triggered_candidates(test_db):
    """Test retrieving candidates with status='triggered'"""
    cand1 = Candidate(
        ticker="BHP",
        headline="Test",
        scan_date="2025-11-03",
        status="triggered",
        gap_percent=3.5,
        prev_close=45.20,
    )
    test_db.save_candidate(cand1)

    triggered = test_db.get_triggered_candidates()
    assert len(triggered) == 1
    assert triggered[0].ticker == "BHP"
    assert triggered[0].status == "triggered"


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
