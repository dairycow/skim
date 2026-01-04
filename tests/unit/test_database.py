"""Unit tests for Database class with SQLModel"""

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
    """Create in-memory SQLite database for each test"""
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


def test_save_and_get_gap_candidate(db, sample_gap_candidate):
    """Saving then fetching a gap candidate round-trips key fields"""
    db.save_stock_in_play(sample_gap_candidate)

    retrieved = db.get_stock_in_play(sample_gap_candidate.ticker)

    assert retrieved is not None
    assert retrieved.ticker == sample_gap_candidate.ticker
    assert retrieved.scan_date == sample_gap_candidate.scan_date
    assert retrieved.status == sample_gap_candidate.status
    assert isinstance(retrieved, GapStockInPlay)
    assert retrieved.gap_percent == sample_gap_candidate.gap_percent
    assert retrieved.conid == sample_gap_candidate.conid


def test_save_and_get_news_candidate(db, sample_news_candidate):
    """Saving then fetching a news candidate round-trips key fields"""
    db.save_stock_in_play(sample_news_candidate)

    retrieved = db.get_stock_in_play(sample_news_candidate.ticker)

    assert retrieved is not None
    assert retrieved.ticker == sample_news_candidate.ticker
    assert retrieved.scan_date == sample_news_candidate.scan_date
    assert retrieved.status == sample_news_candidate.status
    assert isinstance(retrieved, NewsStockInPlay)
    assert retrieved.headline == sample_news_candidate.headline


def test_get_gap_candidates(db):
    """get_gap_candidates should return only gap candidates"""
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
    assert isinstance(gap_candidates[0], GapStockInPlay)


def test_get_news_candidates(db):
    """get_news_candidates should return only news candidates"""
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
    assert isinstance(news_candidates[0], NewsStockInPlay)


def test_get_watching_candidates_filters_by_status(db):
    """Only watching candidates should be returned"""
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
    """Status updates should persist"""
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
    """Saving then fetching an opening range round-trips key fields"""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    db.save_stock_in_play(gap_candidate)

    ticker = "BHP"
    opening_range = OpeningRange(
        ticker=ticker,
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )
    db.save_opening_range(opening_range)

    retrieved = db.get_opening_range(ticker)

    assert retrieved is not None
    assert retrieved.ticker == ticker
    assert retrieved.or_high == 47.80
    assert retrieved.or_low == 45.90


def test_save_opening_range_updates_existing(db):
    """Saving opening range for existing ticker should update it"""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    db.save_stock_in_play(gap_candidate)

    opening_range1 = OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )
    db.save_opening_range(opening_range1)

    opening_range2 = OpeningRange(
        ticker="BHP",
        or_high=48.50,
        or_low=46.00,
        sample_date="2025-11-03T10:15:00",
    )
    db.save_opening_range(opening_range2)

    retrieved = db.get_opening_range("BHP")
    assert retrieved is not None
    assert retrieved.or_high == 48.50
    assert retrieved.or_low == 46.00


def test_create_and_close_position(db):
    """Positions can be created, retrieved, and closed"""
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
    """Open position count reflects closes"""
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


def test_tradeable_candidates_requires_gap_news_and_range(db):
    """Tradeable candidates need gap, news, and opening range"""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    news_candidate = NewsStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )
    opening_range = OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )

    db.save_stock_in_play(gap_candidate)
    db.save_stock_in_play(news_candidate)
    db.save_opening_range(opening_range)

    tradeable = db.get_tradeable_candidates()

    assert len(tradeable) == 1
    assert tradeable[0].ticker == "BHP"
    assert tradeable[0].gap_percent == 5.0
    assert tradeable[0].headline == "Results Released"
    assert tradeable[0].or_high == 47.80
    assert tradeable[0].or_low == 45.90


def test_candidates_needing_ranges(db):
    """Candidates with gap and news but no opening ranges"""
    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    news_candidate = NewsStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        headline="Results Released",
    )

    db.save_stock_in_play(gap_candidate)
    db.save_stock_in_play(news_candidate)

    needing_ranges = db.get_candidates_needing_ranges()

    assert len(needing_ranges) == 1
    assert needing_ranges[0].ticker == "BHP"


def test_purge_candidates_deletes_all_rows(db):
    """purge_candidates should remove all stored candidates when no filter is provided"""
    db.save_stock_in_play(
        GapStockInPlay(
            ticker="BHP",
            scan_date="2025-11-03",
            status="watching",
            gap_percent=5.0,
            conid=8644,
        )
    )
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


def test_purge_candidates_filters_by_scan_date(db):
    """purge_candidates should only delete rows before the provided UTC date"""
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


def test_purge_opening_ranges(db):
    """purge_opening_ranges should delete all opening ranges"""
    db.save_stock_in_play(
        GapStockInPlay(
            ticker="BHP",
            scan_date="2025-11-03",
            status="watching",
            gap_percent=5.0,
            conid=8644,
        )
    )

    opening_range = OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )
    db.save_opening_range(opening_range)

    assert db.get_opening_range("BHP") is not None

    deleted = db.purge_opening_ranges()

    assert deleted == 1
    assert db.get_opening_range("BHP") is None
