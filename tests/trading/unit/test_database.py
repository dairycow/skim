"""Unit tests for Database class with SQLModel"""

from datetime import date, datetime

import pytest
from sqlmodel import select

from skim.trading.data.database import Database


@pytest.fixture
def db():
    """Create in-memory SQLite database for each test"""
    database = Database(":memory:")
    yield database
    database.close()


def test_update_candidate_status(db):
    """Status updates should persist"""
    from skim.trading.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )
    from tests.factories import CandidateFactory

    orh_repo = ORHCandidateRepository(db)

    gap_candidate = CandidateFactory.gap_candidate(
        scan_date=datetime.now(),
    )
    orh_repo.save_gap_candidate(gap_candidate)

    db.update_candidate_status(gap_candidate.ticker.symbol, "entered")

    from skim.infrastructure.database.trading.models import CandidateTable

    session = db.get_session()
    updated = session.exec(
        select(CandidateTable).where(
            CandidateTable.ticker == gap_candidate.ticker.symbol
        )
    ).first()
    session.close()

    assert updated is not None
    assert updated.status == "entered"


def test_purge_candidates_all(db):
    """purge_candidates should remove all candidates when no filter"""
    from skim.trading.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )
    from tests.factories import CandidateFactory

    orh_repo = ORHCandidateRepository(db)

    # Use different tickers to ensure 2 separate candidates
    orh_repo.save_gap_candidate(
        CandidateFactory.gap_candidate(
            ticker="BHP",
            scan_date=datetime(2024, 1, 1, 23),
        )
    )
    orh_repo.save_gap_candidate(
        CandidateFactory.gap_candidate(
            ticker="RIO",
            scan_date=datetime(2024, 1, 1, 23),
            gap_percent=4.0,
            status="entered",
        )
    )

    deleted = db.purge_candidates(strategy_name="orh_breakout")

    assert deleted >= 2

    from skim.infrastructure.database.trading.models import CandidateTable

    session = db.get_session()
    result = session.exec(select(CandidateTable)).all()
    session.close()

    assert len(result) == 0


def test_purge_candidates_filters_by_scan_date(db):
    """purge_candidates should only delete rows before the provided UTC date"""
    from skim.trading.data.repositories.orh_repository import (
        ORHCandidateRepository,
    )
    from tests.factories import CandidateFactory

    orh_repo = ORHCandidateRepository(db)

    january_first = datetime(2024, 1, 1, 23)
    january_second = datetime(2024, 1, 2, 23)

    orh_repo.save_gap_candidate(
        CandidateFactory.gap_candidate(
            ticker="BHP",
            scan_date=january_first,
        )
    )
    orh_repo.save_gap_candidate(
        CandidateFactory.gap_candidate(
            ticker="CBA",
            scan_date=january_second,
            gap_percent=3.5,
            conid=8646,
        )
    )

    deleted = db.purge_candidates(
        only_before_utc_date=date(2024, 1, 2), strategy_name="orh_breakout"
    )

    assert deleted == 1

    from skim.infrastructure.database.trading.models import CandidateTable

    session = db.get_session()
    result = session.exec(select(CandidateTable)).all()
    session.close()

    assert len(result) == 1
    assert result[0].ticker == "CBA"


def test_create_and_close_position(db):
    """Positions can be created, retrieved, and closed"""
    position = db.create_position(
        ticker="BHP",
        quantity=50,
        entry_price=10.0,
        stop_loss=9.5,
        entry_date=datetime.now(),
    )

    open_positions = db.get_open_positions()
    assert len(open_positions) == 1
    assert open_positions[0].id == position.id
    assert open_positions[0].ticker.symbol == "BHP"

    db.close_position(position.id, exit_price=10.5, exit_date="2024-01-01")

    closed = db.get_position(position.id)
    assert closed is not None
    assert closed.status == "closed"
    assert closed.exit_price.value == 10.5


def test_count_open_positions(db):
    """Open position count reflects closes"""
    first_position = db.create_position(
        ticker="BHP",
        quantity=50,
        entry_price=10.0,
        stop_loss=9.5,
        entry_date=datetime.now(),
    )
    db.create_position(
        ticker="FMG",
        quantity=20,
        entry_price=5.0,
        stop_loss=4.5,
        entry_date=datetime.now(),
    )

    assert db.count_open_positions() == 2

    db.close_position(
        first_position.id, exit_price=10.2, exit_date="2024-01-02"
    )

    assert db.count_open_positions() == 1
