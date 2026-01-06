"""Unit tests for RangeTracker UTC scheduling behaviour."""

from datetime import UTC, datetime, time
from unittest.mock import AsyncMock, Mock

import pytest

from skim.strategies.orh_breakout import RangeTracker


@pytest.fixture
def tracker_with_utc_clock():
    """RangeTracker with an injectable UTC clock for deterministic tests."""

    def make_tracker(now):
        return RangeTracker(
            market_data_service=AsyncMock(),
            orh_repo=Mock(),
            market_open_time=time(23, 0, tzinfo=UTC),
            range_duration_minutes=10,
            now_provider=lambda: now,
        )

    return make_tracker


def test_calculate_target_time_uses_utc_clock(tracker_with_utc_clock):
    """RangeTracker should target 23:10 UTC when market opens at 23:00 UTC."""
    now = datetime(2024, 1, 1, 23, 5, tzinfo=UTC)
    tracker = tracker_with_utc_clock(now)

    target = tracker._calculate_target_time()

    assert target == datetime(2024, 1, 1, 23, 10, tzinfo=UTC)
