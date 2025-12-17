"""Unit tests for the simplified database layer."""

from datetime import UTC, date, datetime

import pytest

from skim.data.database import Database
from skim.data.models import Candidate


@pytest.fixture
def db():
    """Create an in-memory database for each test."""
    database = Database(":memory:")
    yield database
    database.close()


def test_save_and_get_candidate(db, sample_candidate):
    """Saving then fetching a candidate round-trips key fields."""
    db.save_candidate(sample_candidate)

    retrieved = db.get_candidate(sample_candidate.ticker)

    assert retrieved == sample_candidate
    assert retrieved.status == "watching"


def test_get_watching_candidates_filters_by_status(db, sample_candidate):
    """Only watching candidates should be returned."""
    db.save_candidate(sample_candidate)
    db.save_candidate(
        Candidate(
            ticker="RIO",
            or_high=100.0,
            or_low=95.0,
            scan_date="2025-11-03",
            status="entered",
        )
    )

    watching = db.get_watching_candidates()

    assert len(watching) == 1
    assert watching[0].ticker == sample_candidate.ticker


def test_update_candidate_status(db, sample_candidate):
    """Status updates should persist."""
    db.save_candidate(sample_candidate)

    db.update_candidate_status(sample_candidate.ticker, "entered")

    updated = db.get_candidate(sample_candidate.ticker)
    assert updated is not None
    assert updated.status == "entered"


def test_create_and_close_position(db):
    """Positions can be created, retrieved, and closed."""
    position_id = db.create_position(
        ticker="BHP",
        quantity=50,
        entry_price=10.0,
        stop_loss=9.5,
        entry_date=datetime.now().isoformat(),
    )

    open_positions = db.get_open_positions()
    assert len(open_positions) == 1
    assert open_positions[0].id == position_id

    db.close_position(position_id, exit_price=10.5, exit_date="2024-01-01")

    closed = db.get_position(position_id)
    assert closed is not None
    assert closed.status == "closed"
    assert closed.exit_price == 10.5


def test_count_open_positions(db):
    """Open position count reflects closes."""
    first_id = db.create_position(
        ticker="BHP",
        quantity=50,
        entry_price=10.0,
        stop_loss=9.5,
        entry_date="2024-01-01",
    )
    db.create_position(
        ticker="FMG",
        quantity=20,
        entry_price=5.0,
        stop_loss=4.5,
        entry_date="2024-01-01",
    )

    assert db.count_open_positions() == 2

    db.close_position(first_id, exit_price=10.2, exit_date="2024-01-02")

    assert db.count_open_positions() == 1


def test_purge_candidates_deletes_all_rows(db):
    """purge_candidates should remove all stored candidates when no filter is provided."""
    db.save_candidate(
        Candidate(
            ticker="BHP",
            or_high=None,
            or_low=None,
            scan_date=datetime(2024, 1, 1, 23, tzinfo=UTC).isoformat(),
            status="watching",
        )
    )
    db.save_candidate(
        Candidate(
            ticker="RIO",
            or_high=100.0,
            or_low=95.0,
            scan_date=datetime(2024, 1, 2, 23, tzinfo=UTC).isoformat(),
            status="entered",
        )
    )

    deleted = db.purge_candidates()

    assert deleted == 2
    assert db.get_candidate("BHP") is None
    assert db.get_candidate("RIO") is None


def test_purge_candidates_filters_by_scan_date(db):
    """purge_candidates should only delete rows before the provided UTC date."""
    january_first = datetime(2024, 1, 1, 23, tzinfo=UTC).isoformat()
    january_second = datetime(2024, 1, 2, 23, tzinfo=UTC).isoformat()
    db.save_candidate(
        Candidate(
            ticker="BHP",
            or_high=None,
            or_low=None,
            scan_date=january_first,
            status="watching",
        )
    )
    db.save_candidate(
        Candidate(
            ticker="CBA",
            or_high=None,
            or_low=None,
            scan_date=january_second,
            status="watching",
        )
    )

    deleted = db.purge_candidates(only_before_utc_date=date(2024, 1, 2))

    assert deleted == 1
    assert db.get_candidate("BHP") is None
    remaining = db.get_candidate("CBA")
    assert remaining is not None
    assert remaining.ticker == "CBA"
