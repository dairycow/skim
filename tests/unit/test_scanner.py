"""Unit tests for the Scanner workflow."""

from unittest.mock import AsyncMock

import pytest

from skim.scanner import Scanner
from skim.validation.scanners import (
    GapStock,
)


@pytest.mark.asyncio
async def test_find_candidates_returns_candidates_when_gaps_and_announcements_align():
    scanner_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.0, conid=123)
    ]
    scanner = Scanner(scanner_service, gap_threshold=3.0)

    scanner.asx_scanner.fetch_price_sensitive_tickers = lambda: {"BHP"}

    candidates = await scanner.find_candidates()

    assert len(candidates) == 1
    assert candidates[0].ticker == "BHP"
    assert candidates[0].or_high is None  # ORH/ORL not set yet
    assert candidates[0].or_low is None
    assert candidates[0].status == "watching"


@pytest.mark.asyncio
async def test_find_candidates_returns_empty_when_no_announcements():
    scanner_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.0, conid=123)
    ]
    scanner = Scanner(scanner_service, gap_threshold=3.0)

    scanner.asx_scanner.fetch_price_sensitive_tickers = lambda: set()

    candidates = await scanner.find_candidates()

    assert candidates == []


# NOTE: filter_breakouts method was removed from Scanner.
# Breakout filtering is now handled by Trader.execute_breakouts()
# which checks if current_price > candidate.or_high
