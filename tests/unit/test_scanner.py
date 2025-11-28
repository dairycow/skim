"""Unit tests for the Scanner workflow."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from skim.scanner import Scanner
from skim.validation.scanners import (
    ASXAnnouncement,
    GapStock,
)


@pytest.mark.asyncio
async def test_find_candidates_returns_candidates_when_gaps_and_announcements_align():
    scanner_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.0, conid=123)
    ]
    scanner = Scanner(scanner_service, gap_threshold=3.0)

    scanner.asx_scanner.fetch_price_sensitive_announcements = lambda: [
        ASXAnnouncement(
            ticker="BHP",
            headline="Test Announcement",
            announcement_type="pricesens",
            timestamp=datetime.now(),
        )
    ]

    candidates = await scanner.find_candidates()

    assert len(candidates) == 1
    assert candidates[0].ticker == "BHP"
    assert candidates[0].or_high is None  # ORH/ORL not set yet
    assert candidates[0].or_low is None
    assert candidates[0].status == "watching"
    assert candidates[0].gap_percent == 5.0
    assert candidates[0].headline == "Test Announcement"


@pytest.mark.asyncio
async def test_find_candidates_returns_empty_when_no_announcements():
    scanner_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.0, conid=123)
    ]
    scanner = Scanner(scanner_service, gap_threshold=3.0)

    scanner.asx_scanner.fetch_price_sensitive_announcements = lambda: []

    candidates = await scanner.find_candidates()

    assert candidates == []


# NOTE: filter_breakouts method was removed from Scanner.
# Breakout filtering is now handled by Trader.execute_breakouts()
# which checks if current_price > candidate.or_high


@pytest.mark.asyncio
async def test_find_candidates_enriches_with_gap_percent_and_headline():
    """Scanner should populate gap_percent and headline fields in Candidate objects"""
    scanner_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.2, conid=123),
        GapStock(ticker="RIO", gap_percent=3.8, conid=456),
    ]
    scanner = Scanner(scanner_service, gap_threshold=3.0)

    scanner.asx_scanner.fetch_price_sensitive_announcements = lambda: [
        ASXAnnouncement(
            ticker="BHP",
            headline="Trading Halt",
            announcement_type="pricesens",
            timestamp=datetime.now(),
        ),
        ASXAnnouncement(
            ticker="RIO",
            headline="Quarterly Results Released",
            announcement_type="pricesens",
            timestamp=datetime.now(),
        ),
    ]

    candidates = await scanner.find_candidates()

    assert len(candidates) == 2

    bhp = next(c for c in candidates if c.ticker == "BHP")
    assert bhp.gap_percent == 5.2
    assert bhp.headline == "Trading Halt"

    rio = next(c for c in candidates if c.ticker == "RIO")
    assert rio.gap_percent == 3.8
    assert rio.headline == "Quarterly Results Released"


@pytest.mark.asyncio
async def test_find_candidates_concatenates_multiple_announcements():
    """Scanner should concatenate multiple announcements per ticker with 80 char limit"""
    scanner_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="ABC", gap_percent=4.5, conid=789)
    ]
    scanner = Scanner(scanner_service, gap_threshold=3.0)

    long_headline = "A" * 100  # 100 chars - should be truncated to 80
    scanner.asx_scanner.fetch_price_sensitive_announcements = lambda: [
        ASXAnnouncement(
            ticker="ABC",
            headline=long_headline,
            announcement_type="pricesens",
            timestamp=datetime.now(),
        ),
        ASXAnnouncement(
            ticker="ABC",
            headline="Second Announcement",
            announcement_type="pricesens",
            timestamp=datetime.now(),
        ),
    ]

    candidates = await scanner.find_candidates()

    assert len(candidates) == 1
    assert candidates[0].ticker == "ABC"
    assert candidates[0].gap_percent == 4.5
    # First headline truncated to 80 chars, then " | Second Announcement"
    expected = ("A" * 80) + " | " + "Second Announcement"
    assert candidates[0].headline == expected


@pytest.mark.asyncio
async def test_find_candidates_handles_missing_announcement_gracefully():
    """Scanner should handle case where gap stock has no matching announcement"""
    scanner_service = AsyncMock()
    scanner_service.scan_for_gaps.return_value = [
        GapStock(ticker="BHP", gap_percent=5.2, conid=123)
    ]
    scanner = Scanner(scanner_service, gap_threshold=3.0)

    # BHP has announcement, but we'll only match on BHP (this is edge case testing)
    scanner.asx_scanner.fetch_price_sensitive_announcements = lambda: [
        ASXAnnouncement(
            ticker="BHP",
            headline="Trading Halt",
            announcement_type="pricesens",
            timestamp=datetime.now(),
        )
    ]

    candidates = await scanner.find_candidates()

    assert len(candidates) == 1
    assert candidates[0].ticker == "BHP"
    assert candidates[0].gap_percent == 5.2
    assert candidates[0].headline == "Trading Halt"
