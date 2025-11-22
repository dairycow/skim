"""Unit tests for the Scanner workflow."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from skim.scanner import Scanner
from skim.validation.scanners import (
    BreakoutSignal,
    GapStock,
    OpeningRangeData,
)


@pytest.mark.asyncio
async def test_find_candidates_returns_breakouts_when_gaps_and_announcements_align():
    scanner_service = AsyncMock()
    market_data_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.0, conid=123)
    ]
    scanner = Scanner(scanner_service, market_data_service, gap_threshold=3.0)

    scanner.asx_scanner.fetch_price_sensitive_tickers = lambda: {"BHP"}
    scanner.track_opening_range = AsyncMock(
        return_value=[
            OpeningRangeData(
                ticker="BHP",
                conid=123,
                or_high=11.0,
                or_low=10.0,
                open_price=10.5,
                prev_close=9.5,
                current_price=11.2,
                gap_holding=True,
            )
        ]
    )
    scanner.filter_breakouts = lambda data: [
        BreakoutSignal(
            ticker="BHP",
            conid=123,
            gap_pct=7.4,
            or_high=11.0,
            or_low=10.0,
            or_size_pct=10.0,
            current_price=11.2,
            entry_signal="ORB_HIGH_BREAKOUT",
            timestamp=datetime.now(),
        )
    ]

    candidates = await scanner.find_candidates()

    assert len(candidates) == 1
    assert candidates[0].ticker == "BHP"
    assert candidates[0].or_high == 11.0
    assert candidates[0].status == "watching"


@pytest.mark.asyncio
async def test_find_candidates_returns_empty_when_no_announcements():
    scanner_service = AsyncMock()
    market_data_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.0, conid=123)
    ]
    scanner = Scanner(scanner_service, market_data_service, gap_threshold=3.0)

    scanner.asx_scanner.fetch_price_sensitive_tickers = lambda: set()
    scanner.track_opening_range = AsyncMock()

    candidates = await scanner.find_candidates()

    assert candidates == []
    scanner.track_opening_range.assert_not_awaited()


def test_filter_breakouts_requires_gap_holding_and_breakout():
    scanner = Scanner(AsyncMock(), AsyncMock(), gap_threshold=3.0)
    inputs = [
        OpeningRangeData(
            ticker="BHP",
            conid=1,
            or_high=11.0,
            or_low=10.0,
            open_price=10.5,
            prev_close=9.5,
            current_price=11.5,
            gap_holding=True,
        ),
        OpeningRangeData(
            ticker="RIO",
            conid=2,
            or_high=20.0,
            or_low=19.0,
            open_price=19.5,
            prev_close=18.0,
            current_price=19.1,
            gap_holding=False,
        ),
        OpeningRangeData(
            ticker="FMG",
            conid=3,
            or_high=8.0,
            or_low=7.5,
            open_price=7.6,
            prev_close=7.0,
            current_price=8.0,
            gap_holding=True,
        ),
    ]

    signals = scanner.filter_breakouts(inputs)

    assert [s.ticker for s in signals] == ["BHP"]
