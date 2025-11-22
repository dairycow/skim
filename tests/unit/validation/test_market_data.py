"""Unit tests for simplified market data validation utilities."""

from datetime import datetime, timedelta

from skim.data.models import Candidate
from skim.validation.market_data import (
    filter_candidates_by_market_data_quality,
    get_candidate_market_data_age_minutes,
    validate_candidate_for_or_tracking,
    validate_candidate_market_data_completeness,
    validate_candidate_market_data_freshness,
)


def make_candidate(
    scan_date: datetime | None = None,
    or_high: float = 10.0,
    or_low: float = 9.0,
) -> Candidate:
    return Candidate(
        ticker="BHP",
        or_high=or_high,
        or_low=or_low,
        scan_date=(scan_date or datetime.now()).isoformat(),
        status="watching",
    )


def test_validate_candidate_market_data_completeness():
    assert validate_candidate_market_data_completeness(make_candidate()) is True
    assert (
        validate_candidate_market_data_completeness(
            make_candidate(or_high=9.0, or_low=9.0)
        )
        is False
    )
    assert (
        validate_candidate_market_data_completeness(
            make_candidate(or_high=-1.0, or_low=1.0)
        )
        is False
    )


def test_validate_candidate_market_data_freshness():
    recent = make_candidate(scan_date=datetime.now())
    stale = make_candidate(scan_date=datetime.now() - timedelta(minutes=45))

    assert validate_candidate_market_data_freshness(recent) is True
    assert validate_candidate_market_data_freshness(stale) is False


def test_validate_candidate_for_or_tracking_requires_both_checks():
    assert validate_candidate_for_or_tracking(make_candidate()) is True
    assert (
        validate_candidate_for_or_tracking(
            make_candidate(or_high=8.0, or_low=9.0)
        )
        is False
    )


def test_filter_candidates_by_market_data_quality():
    good = make_candidate()
    bad = make_candidate(or_high=8.0, or_low=9.0)

    valid, invalid = filter_candidates_by_market_data_quality([good, bad])

    assert valid == [good]
    assert invalid == [bad]


def test_get_candidate_market_data_age_minutes():
    candidate = make_candidate(scan_date=datetime.now() - timedelta(minutes=10))
    age = get_candidate_market_data_age_minutes(candidate)
    assert age is not None
    assert 9 <= age <= 11
