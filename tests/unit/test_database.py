"""Unit tests for the simplified database layer."""

from datetime import UTC, date, datetime

import pytest

from skim.data.database import Database
from skim.data.models import (
    GapStockInPlay,
    NewsStockInPlay,
    OpeningRange,
)


@pytest.fixture
def db():
    """Create an in-memory database for each test."""
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def sample_gap_candidate():
    """Sample gap-only candidate for testing"""
    return GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )


@pytest.fixture
def sample_news_candidate():
    """Sample news-only candidate for testing"""
    return NewsStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )


@pytest.fixture
def sample_opening_range():
    """Sample opening range for testing"""
    return OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )


def test_save_and_get_gap_candidate(db, sample_gap_candidate):
    """Saving then fetching a gap candidate round-trips key fields."""
    db.save_stock_in_play(sample_gap_candidate)

    retrieved = db.get_stock_in_play(sample_gap_candidate.ticker)

    assert retrieved == sample_gap_candidate
    assert retrieved.status == "watching"


def test_save_and_get_news_candidate(db, sample_news_candidate):
    """Saving then fetching a news candidate round-trips key fields."""
    db.save_stock_in_play(sample_news_candidate)

    retrieved = db.get_stock_in_play(sample_news_candidate.ticker)

    assert retrieved == sample_news_candidate
    assert retrieved.status == "watching"


def test_get_gap_candidates(db):
    """get_gap_candidates should return only gap candidates."""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    news_candidate = NewsStockInPlay(
        ticker="RIO",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )
    db.save_stock_in_play(gap_candidate)
    db.save_stock_in_play(news_candidate)

    gap_candidates = db.get_gap_candidates()

    assert len(gap_candidates) == 1
    assert gap_candidates[0].ticker == gap_candidate.ticker


def test_get_news_candidates(db):
    """get_news_candidates should return only news candidates."""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    news_candidate = NewsStockInPlay(
        ticker="RIO",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )
    db.save_stock_in_play(gap_candidate)
    db.save_stock_in_play(news_candidate)

    news_candidates = db.get_news_candidates()

    assert len(news_candidates) == 1
    assert news_candidates[0].ticker == news_candidate.ticker


def test_get_watching_candidates_filters_by_status(db):
    """Only watching candidates should be returned."""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )

    db.save_stock_in_play(gap_candidate)

    db.save_stock_in_play(
        GapStockInPlay(
            ticker="RIO",
            scan_date="2025-11-03",
            status="entered",
            gap_percent=4.0,
            conid=8645,
        )
    )

    watching = db.get_watching_candidates()

    assert len(watching) == 1
    assert watching[0].ticker == gap_candidate.ticker


def test_update_candidate_status(db):
    """Status updates should persist."""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )

    db.save_stock_in_play(gap_candidate)

    db.update_candidate_status(gap_candidate.ticker, "entered")

    updated = db.get_stock_in_play(gap_candidate.ticker)
    assert updated is not None
    assert updated.status == "entered"


def test_save_and_get_opening_range(db):
    """Saving then fetching an opening range round-trips key fields."""
    # First save a candidate so foreign key is satisfied
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    db.save_stock_in_play(gap_candidate)

    opening_range = OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )
    db.save_opening_range(opening_range)

    retrieved = db.get_opening_range(opening_range.ticker)

    assert retrieved == opening_range
    assert retrieved.or_high == 47.80
    assert retrieved.or_low == 45.90


def test_get_tradeable_candidates(db):
    """get_tradeable_candidates should return candidates with gap, news, and opening ranges."""
    # Save gap and news candidates for same ticker
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    db.save_stock_in_play(gap_candidate)

    news_candidate = NewsStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )
    db.save_stock_in_play(news_candidate)

    # Save opening range
    opening_range = OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )
    db.save_opening_range(opening_range)

    # Get tradeable candidates
    tradeable = db.get_tradeable_candidates()

    assert len(tradeable) == 1
    assert tradeable[0].ticker == gap_candidate.ticker
    assert tradeable[0].gap_percent == gap_candidate.gap_percent
    assert tradeable[0].headline == news_candidate.headline
    assert tradeable[0].or_high == opening_range.or_high
    assert tradeable[0].or_low == opening_range.or_low


def test_get_candidates_needing_ranges(db):
    """get_candidates_needing_ranges should return gap+news candidates without ranges."""
    # Save gap and news candidates for same ticker (no opening range yet)
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    db.save_stock_in_play(gap_candidate)

    news_candidate = NewsStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )
    db.save_stock_in_play(news_candidate)

    # Save another ticker with only gap (shouldn't appear)
    db.save_stock_in_play(
        GapStockInPlay(
            ticker="RIO",
            scan_date="2025-11-03",
            status="watching",
            gap_percent=4.0,
            conid=8645,
        )
    )

    # Get candidates needing ranges
    needing_ranges = db.get_candidates_needing_ranges()

    assert len(needing_ranges) == 1
    assert needing_ranges[0].ticker == gap_candidate.ticker


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


def test_purge_candidates_deletes_all_rows(db, sample_gap_candidate):
    """purge_candidates should remove all stored candidates when no filter is provided."""
    db.save_stock_in_play(sample_gap_candidate)
    db.save_stock_in_play(
        GapStockInPlay(
            ticker="RIO",
            scan_date=datetime(2024, 1, 1, 23, tzinfo=UTC).isoformat(),
            status="entered",
            gap_percent=4.0,
            conid=8645,
        )
    )

    deleted = db.purge_candidates()

    assert deleted == 2
    assert db.get_stock_in_play("RIO") is None


def test_purge_candidates_filters_by_scan_date(db, sample_gap_candidate):
    """purge_candidates should only delete rows before the provided UTC date."""
    january_first = datetime(2024, 1, 1, 23, tzinfo=UTC).isoformat()
    january_second = datetime(2024, 1, 2, 23, tzinfo=UTC).isoformat()

    db.save_stock_in_play(
        GapStockInPlay(
            ticker="BHP",
            scan_date=january_first,
            status="watching",
            gap_percent=5.0,
            conid=8644,
        )
    )
    db.save_stock_in_play(
        GapStockInPlay(
            ticker="CBA",
            scan_date=january_second,
            status="watching",
            gap_percent=3.5,
            conid=8646,
        )
    )

    deleted = db.purge_candidates(only_before_utc_date=date(2024, 1, 2))

    assert deleted == 1
    assert db.get_stock_in_play("BHP") is None
    remaining = db.get_stock_in_play("CBA")
    assert remaining is not None
    assert remaining.ticker == "CBA"


def test_purge_opening_ranges(db, sample_opening_range):
    """purge_opening_ranges should delete all opening ranges."""
    # First save a candidate to satisfy foreign key
    db.save_stock_in_play(
        GapStockInPlay(
            ticker=sample_opening_range.ticker,
            scan_date="2025-11-03",
            status="watching",
            gap_percent=5.0,
            conid=8644,
        )
    )

    db.save_opening_range(sample_opening_range)

    assert db.get_opening_range(sample_opening_range.ticker) is not None

    deleted = db.purge_opening_ranges()

    assert deleted == 1
    assert db.get_opening_range(sample_opening_range.ticker) is None
