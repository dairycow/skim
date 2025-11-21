"""Unit tests for market data validation utilities"""

from datetime import datetime, timedelta

import pytest

from skim.data.models import Candidate
from skim.validation.market_data import (
    filter_candidates_by_market_data_quality,
    get_candidate_market_data_age_minutes,
    validate_candidate_for_or_tracking,
    validate_candidate_market_data_completeness,
    validate_candidate_market_data_freshness,
)


class TestMarketDataValidation:
    """Test market data validation functions"""

    @pytest.fixture
    def valid_candidate(self):
        """Create a candidate with valid market data"""
        return Candidate(
            ticker="BHP",
            headline="Gap detected: 3.50%",
            scan_date="2025-11-03T10:00:00",
            status="watching",
            gap_percent=3.5,
            prev_close=45.20,
            conid=8644,
            source="ibkr",
            open_price=46.50,
            session_high=47.80,
            session_low=45.90,
            volume=1500000,
            bid=46.95,
            ask=47.05,
            market_data_timestamp=datetime.now().isoformat(),
        )

    @pytest.fixture
    def incomplete_candidate(self):
        """Create a candidate with incomplete market data"""
        return Candidate(
            ticker="RIO",
            headline="Gap detected: 4.20%",
            scan_date="2025-11-03T10:00:00",
            status="watching",
            gap_percent=4.2,
            prev_close=120.50,
            conid=8653,
            source="ibkr",
            # Missing enhanced market data fields
        )

    @pytest.fixture
    def stale_candidate(self):
        """Create a candidate with stale market data"""
        return Candidate(
            ticker="FMG",
            headline="Gap detected: 2.80%",
            scan_date="2025-11-03T10:00:00",
            status="watching",
            gap_percent=2.8,
            prev_close=18.90,
            conid=8662,
            source="ibkr",
            open_price=19.50,
            session_high=20.20,
            session_low=19.10,
            volume=980000,
            bid=20.05,
            ask=20.15,
            market_data_timestamp=(
                datetime.now() - timedelta(hours=2)
            ).isoformat(),
        )

    def test_validate_market_data_completeness_valid(self, valid_candidate):
        """Test validation of candidate with complete market data"""
        assert (
            validate_candidate_market_data_completeness(valid_candidate) is True
        )

    def test_validate_market_data_completeness_incomplete(
        self, incomplete_candidate
    ):
        """Test validation of candidate with incomplete market data"""
        assert (
            validate_candidate_market_data_completeness(incomplete_candidate)
            is False
        )

    def test_validate_market_data_completeness_invalid_prices(self):
        """Test validation fails with invalid price relationships"""
        # High <= Low
        candidate = Candidate(
            ticker="BHP",
            headline="Test",
            scan_date="2025-11-03",
            status="watching",
            conid=8644,
            open_price=46.50,
            session_high=45.00,  # Invalid: high <= low
            session_low=47.00,
            volume=1000000,
            bid=46.00,
            ask=47.00,
            market_data_timestamp=datetime.now().isoformat(),
        )
        assert validate_candidate_market_data_completeness(candidate) is False

    def test_validate_market_data_completeness_invalid_bid_ask(self):
        """Test validation fails with invalid bid-ask spread"""
        candidate = Candidate(
            ticker="BHP",
            headline="Test",
            scan_date="2025-11-03",
            status="watching",
            conid=8644,
            open_price=46.50,
            session_high=47.80,
            session_low=45.90,
            volume=1000000,
            bid=47.00,  # Invalid: bid > ask
            ask=46.00,
            market_data_timestamp=datetime.now().isoformat(),
        )
        assert validate_candidate_market_data_completeness(candidate) is False

    def test_validate_market_data_freshness_fresh(self, valid_candidate):
        """Test validation of fresh market data"""
        assert validate_candidate_market_data_freshness(valid_candidate) is True

    def test_validate_market_data_freshness_stale(self, stale_candidate):
        """Test validation of stale market data"""
        assert (
            validate_candidate_market_data_freshness(stale_candidate) is False
        )

    def test_validate_market_data_freshness_no_timestamp(
        self, incomplete_candidate
    ):
        """Test validation of candidate with no timestamp"""
        assert (
            validate_candidate_market_data_freshness(incomplete_candidate)
            is False
        )

    def test_validate_market_data_freshness_invalid_timestamp(self):
        """Test validation of candidate with invalid timestamp"""
        candidate = Candidate(
            ticker="BHP",
            headline="Test",
            scan_date="2025-11-03",
            status="watching",
            conid=8644,
            open_price=46.50,
            session_high=47.80,
            session_low=45.90,
            volume=1000000,
            bid=46.00,
            ask=47.00,
            market_data_timestamp="invalid-timestamp",
        )
        assert validate_candidate_market_data_freshness(candidate) is False

    def test_validate_candidate_for_or_tracking_valid(self, valid_candidate):
        """Test candidate validation for OR tracking - valid case"""
        assert validate_candidate_for_or_tracking(valid_candidate) is True

    def test_validate_candidate_for_or_tracking_no_conid(
        self, incomplete_candidate
    ):
        """Test candidate validation for OR tracking - no conid"""
        assert validate_candidate_for_or_tracking(incomplete_candidate) is False

    def test_validate_candidate_for_or_tracking_incomplete_data(
        self, incomplete_candidate
    ):
        """Test candidate validation for OR tracking - incomplete data"""
        # Add conid but still missing other fields
        incomplete_candidate.conid = 8644
        assert validate_candidate_for_or_tracking(incomplete_candidate) is False

    def test_validate_candidate_for_or_tracking_stale_data(
        self, stale_candidate
    ):
        """Test candidate validation for OR tracking - stale data"""
        assert validate_candidate_for_or_tracking(stale_candidate) is False

    def test_filter_candidates_by_market_data_quality(
        self, valid_candidate, incomplete_candidate, stale_candidate
    ):
        """Test filtering candidates by market data quality"""
        candidates = [valid_candidate, incomplete_candidate, stale_candidate]

        valid, invalid = filter_candidates_by_market_data_quality(candidates)

        assert len(valid) == 1
        assert len(invalid) == 2
        assert valid[0].ticker == "BHP"
        assert {c.ticker for c in invalid} == {"RIO", "FMG"}

    def test_filter_candidates_by_market_data_quality_empty(self):
        """Test filtering empty candidate list"""
        valid, invalid = filter_candidates_by_market_data_quality([])
        assert valid == []
        assert invalid == []

    def test_get_market_data_age_minutes_valid(self, valid_candidate):
        """Test getting market data age for valid candidate"""
        age = get_candidate_market_data_age_minutes(valid_candidate)
        assert age is not None
        assert 0 <= age <= 1  # Should be very recent

    def test_get_market_data_age_minutes_stale(self, stale_candidate):
        """Test getting market data age for stale candidate"""
        age = get_candidate_market_data_age_minutes(stale_candidate)
        assert age is not None
        assert (
            age >= 119
        )  # Should be at least 2 hours old (120 minutes minus 1 minute tolerance)

    def test_get_market_data_age_minutes_no_timestamp(
        self, incomplete_candidate
    ):
        """Test getting market data age for candidate with no timestamp"""
        age = get_candidate_market_data_age_minutes(incomplete_candidate)
        assert age is None

    def test_get_market_data_age_minutes_invalid_timestamp(self):
        """Test getting market data age for candidate with invalid timestamp"""
        candidate = Candidate(
            ticker="BHP",
            headline="Test",
            scan_date="2025-11-03",
            status="watching",
            conid=8644,
            market_data_timestamp="invalid-timestamp",
        )
        age = get_candidate_market_data_age_minutes(candidate)
        assert age is None

    @pytest.mark.parametrize("max_age_minutes", [15, 30, 60, 120])
    def test_validate_market_data_freshness_different_thresholds(
        self, valid_candidate, max_age_minutes
    ):
        """Test freshness validation with different age thresholds"""
        assert (
            validate_candidate_market_data_freshness(
                valid_candidate, max_age_minutes
            )
            is True
        )

    def test_validate_market_data_freshness_custom_threshold(
        self, stale_candidate
    ):
        """Test freshness validation with custom threshold that should pass"""
        # Use a threshold longer than the stale data age
        assert (
            validate_candidate_market_data_freshness(
                stale_candidate, max_age_minutes=180
            )
            is True
        )
