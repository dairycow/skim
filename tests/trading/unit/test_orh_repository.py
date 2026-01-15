"""Unit tests for ORHCandidateRepository"""

from datetime import datetime

import pytest

from skim.domain.models import GapCandidate, NewsCandidate, Ticker
from skim.trading.data.database import Database
from skim.trading.data.repositories.orh_repository import ORHCandidateRepository


@pytest.fixture
def db():
    """Create in-memory SQLite database for each test"""
    database = Database(":memory:")
    yield database
    database.close()


@pytest.fixture
def orh_repo(db):
    """Create ORH repository for each test"""
    return ORHCandidateRepository(db)


@pytest.fixture
def sample_gap_candidate():
    """Sample gap candidate for testing"""
    return GapCandidate(
        ticker=Ticker("BHP"),
        scan_date=datetime(2025, 11, 3),
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )


@pytest.fixture
def sample_news_candidate():
    """Sample news candidate for testing"""
    return NewsCandidate(
        ticker=Ticker("BHP"),
        scan_date=datetime(2025, 11, 3),
        status="watching",
        headline="Results Released",
    )


def test_save_and_get_gap_candidate(orh_repo, sample_gap_candidate):
    """Saving then fetching a gap candidate round-trips key fields"""
    orh_repo.save_gap_candidate(sample_gap_candidate)

    retrieved = orh_repo.get_gap_candidates()

    assert len(retrieved) == 1
    assert retrieved[0].ticker.symbol == sample_gap_candidate.ticker.symbol
    assert retrieved[0].gap_percent == sample_gap_candidate.gap_percent
    assert retrieved[0].conid == sample_gap_candidate.conid
    assert retrieved[0].status == "watching"


def test_save_and_get_news_candidate(orh_repo, sample_news_candidate):
    """Saving then fetching a news candidate round-trips key fields"""
    orh_repo.save_news_candidate(sample_news_candidate)

    retrieved = orh_repo.get_news_candidates()

    assert len(retrieved) == 1
    assert retrieved[0].ticker.symbol == sample_news_candidate.ticker.symbol
    assert retrieved[0].headline == sample_news_candidate.headline
    assert retrieved[0].status == "watching"


def test_save_and_get_gap_news_candidate(
    orh_repo, sample_gap_candidate, sample_news_candidate
):
    """Saving both gap and news for same ticker combines them"""
    orh_repo.save_gap_candidate(sample_gap_candidate)
    orh_repo.save_news_candidate(sample_news_candidate)

    gap_candidates = orh_repo.get_gap_candidates()
    news_candidates = orh_repo.get_news_candidates()

    assert len(gap_candidates) == 1
    assert len(news_candidates) == 1
    assert gap_candidates[0].ticker.symbol == news_candidates[0].ticker.symbol


def test_save_opening_range(
    orh_repo, sample_gap_candidate, sample_news_candidate
):
    """Saving opening range for a candidate"""
    orh_repo.save_gap_candidate(sample_gap_candidate)
    orh_repo.save_news_candidate(sample_news_candidate)

    orh_repo.save_opening_range("BHP", 47.80, 45.90)

    tradeable = orh_repo.get_tradeable_candidates()

    assert len(tradeable) == 1
    assert tradeable[0].ticker.symbol == "BHP"
    assert tradeable[0].orh_data.or_high == 47.80
    assert tradeable[0].orh_data.or_low == 45.90


def test_get_tradeable_candidates_requires_all_data(
    orh_repo, sample_gap_candidate, sample_news_candidate
):
    """Tradeable candidates need gap, news, and opening range"""
    orh_repo.save_gap_candidate(sample_gap_candidate)
    orh_repo.save_news_candidate(sample_news_candidate)

    tradeable = orh_repo.get_tradeable_candidates()
    assert len(tradeable) == 0

    orh_repo.save_opening_range("BHP", 47.80, 45.90)

    tradeable = orh_repo.get_tradeable_candidates()
    assert len(tradeable) == 1


def test_get_alertable_candidates_no_range_required(
    orh_repo, sample_gap_candidate, sample_news_candidate
):
    """Alertable candidates only need gap and news"""
    orh_repo.save_gap_candidate(sample_gap_candidate)
    orh_repo.save_news_candidate(sample_news_candidate)

    alertable = orh_repo.get_alertable_candidates()

    assert len(alertable) == 1
    assert alertable[0].ticker.symbol == "BHP"
    assert alertable[0].orh_data.gap_percent == 5.0
    assert alertable[0].orh_data.headline == "Results Released"
    assert alertable[0].orh_data.or_high == 0.0
    assert alertable[0].orh_data.or_low == 0.0


def test_get_alertable_candidates_requires_gap_and_news(
    orh_repo, sample_gap_candidate, sample_news_candidate
):
    """Alertable candidates need both gap and news"""
    orh_repo.save_gap_candidate(sample_gap_candidate)

    alertable = orh_repo.get_alertable_candidates()
    assert len(alertable) == 0

    orh_repo.save_news_candidate(sample_news_candidate)

    alertable = orh_repo.get_alertable_candidates()
    assert len(alertable) == 1


def test_get_candidates_needing_ranges(
    orh_repo, sample_gap_candidate, sample_news_candidate
):
    """Candidates with gap and news but no opening ranges"""
    orh_repo.save_gap_candidate(sample_gap_candidate)
    orh_repo.save_news_candidate(sample_news_candidate)

    needing = orh_repo.get_candidates_needing_ranges()

    assert len(needing) == 1
    assert needing[0].ticker.symbol == "BHP"

    orh_repo.save_opening_range("BHP", 47.80, 45.90)

    needing = orh_repo.get_candidates_needing_ranges()
    assert len(needing) == 0


def test_purge(orh_repo, sample_gap_candidate, sample_news_candidate):
    """Purge removes all ORH candidates"""
    # Use different tickers to ensure 2 separate candidates
    gap_candidate = GapCandidate(
        ticker=Ticker("BHP"),
        scan_date=datetime(2025, 11, 3),
        status="watching",
        gap_percent=5.0,
        conid=8644,
    )
    news_candidate = NewsCandidate(
        ticker=Ticker("RIO"),
        scan_date=datetime(2025, 11, 3),
        status="watching",
        headline="Results Released",
    )
    orh_repo.save_gap_candidate(gap_candidate)
    orh_repo.save_news_candidate(news_candidate)

    assert len(orh_repo.get_gap_candidates()) == 1
    assert len(orh_repo.get_news_candidates()) == 1

    deleted = orh_repo.purge()

    assert deleted >= 2
    assert len(orh_repo.get_gap_candidates()) == 0
    assert len(orh_repo.get_news_candidates()) == 0


def test_gap_candidate_has_strategy_name():
    """GapCandidate has correct strategy name"""
    candidate = GapCandidate(
        ticker=Ticker("BHP"),
        scan_date=datetime(2025, 11, 3),
        gap_percent=5.0,
        conid=8644,
    )
    assert candidate.strategy_name == "orh_breakout"


def test_news_candidate_has_strategy_name():
    """NewsCandidate has correct strategy name"""
    candidate = NewsCandidate(
        ticker=Ticker("CBA"),
        scan_date=datetime(2025, 11, 3),
        headline="Results",
    )
    assert candidate.strategy_name == "orh_breakout"


def test_strategy_name_persisted_to_db(orh_repo, sample_gap_candidate):
    """Strategy name is correctly persisted to database"""
    orh_repo.save_gap_candidate(sample_gap_candidate)

    retrieved = orh_repo.get_gap_candidates()
    assert len(retrieved) == 1
    assert retrieved[0].strategy_name == "orh_breakout"


def test_purge_respects_strategy_name(orh_repo, sample_gap_candidate):
    """Purge only deletes candidates with matching strategy name"""
    orh_repo.save_gap_candidate(sample_gap_candidate)

    # Verify candidate exists
    assert len(orh_repo.get_gap_candidates()) == 1

    # Purge by strategy name
    deleted = orh_repo.purge()
    assert deleted >= 1

    # Verify all ORH candidates deleted
    assert len(orh_repo.get_gap_candidates()) == 0
