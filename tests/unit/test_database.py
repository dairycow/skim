"""Unit tests for Database class with SQLModel"""

from datetime import UTC, date, datetime

import pytest
from sqlmodel import select

from skim.data.database import Database


@pytest.fixture
def db():
    """Create in-memory SQLite database for each test"""
    database = Database(":memory:")
    yield database
    database.close()


def test_update_candidate_status(db):
    """Status updates should persist"""
    from skim.data.models import Candidate, GapStockInPlay

    gap_candidate = GapStockInPlay(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    orh_repo = db.__class__.__dict__.get("orh_repo")
    if orh_repo:
        orh_repo.save_gap_candidate(gap_candidate)
    else:
        from skim.data.repositories.orh_repository import (
            ORHCandidateRepository,
        )

        orh_repo = ORHCandidateRepository(db)
        orh_repo.save_gap_candidate(gap_candidate)

    db.update_candidate_status(gap_candidate.ticker, "entered")

    session = db.get_session()
    updated = session.exec(
        select(Candidate).where(Candidate.ticker == gap_candidate.ticker)
    ).first()
    session.close()

    assert updated is not None
    assert updated.status == "entered"


def test_purge_candidates_all(db):
    """purge_candidates should remove all candidates when no filter"""
    from skim.data.models import Candidate, GapStockInPlay
    from skim.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )

    orh_repo = ORHCandidateRepository(db)

    orh_repo.save_gap_candidate(
        GapStockInPlay(
            ticker="BHP",
            scan_date="2025-11-03",
            status="watching",
            gap_percent=5.0,
            conid=8644,
        )
    )
    orh_repo.save_gap_candidate(
        GapStockInPlay(
            ticker="RIO",
            scan_date=datetime(2024, 1, 1, 23, tzinfo=UTC).isoformat(),
            status="entered",
            gap_percent=4.0,
            conid=8645,
        )
    )

    deleted = db.purge_candidates(strategy_name="orh_breakout")

    assert deleted >= 2

    session = db.get_session()
    result = session.exec(select(Candidate)).all()
    session.close()

    assert len(result) == 0


def test_purge_candidates_filters_by_scan_date(db):
    """purge_candidates should only delete rows before the provided UTC date"""
    from skim.data.models import Candidate, GapStockInPlay
    from skim.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )

    orh_repo = ORHCandidateRepository(db)

    january_first = datetime(2024, 1, 1, 23, tzinfo=UTC).isoformat()
    january_second = datetime(2024, 1, 2, 23, tzinfo=UTC).isoformat()

    orh_repo.save_gap_candidate(
        GapStockInPlay(
            ticker="BHP",
            scan_date=january_first,
            status="watching",
            gap_percent=5.0,
            conid=8644,
        )
    )
    orh_repo.save_gap_candidate(
        GapStockInPlay(
            ticker="CBA",
            scan_date=january_second,
            status="watching",
            gap_percent=3.5,
            conid=8646,
        )
    )

    deleted = db.purge_candidates(
        only_before_utc_date=date(2024, 1, 2), strategy_name="orh_breakout"
    )

    assert deleted == 1

    session = db.get_session()
    result = session.exec(select(Candidate)).all()
    session.close()

    assert len(result) == 1
    assert result[0].ticker == "CBA"


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
