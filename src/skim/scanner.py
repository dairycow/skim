"""Scanner module - finds candidates with gap + price-sensitive announcements"""

import asyncio
from datetime import datetime

from loguru import logger

from .brokers.protocols import GapScannerService
from .data.models import Candidate
from .scanners.asx_announcements import ASXAnnouncementScanner


class Scanner:
    """Scans market for trading candidates"""

    def __init__(
        self,
        scanner_service: GapScannerService,
        gap_threshold: float = 3.0,
    ):
        """Initialise scanner with required services.

        Args:
            scanner_service: Service for running market scans.
            gap_threshold: Minimum gap percentage to consider.
        """
        self.scanner = scanner_service
        self.gap_threshold = gap_threshold
        self.asx_scanner = ASXAnnouncementScanner()

    async def find_candidates(self) -> list[Candidate]:
        """
        Finds candidates with gap + price-sensitive announcements.

        Workflow:
        1. Scan for gaps > threshold
        2. Fetch ASX announcements
        3. Match gap stocks to announcements
        4. Return matched tickers as candidates (ORH/ORL will be set later by RangeTracker)

        Returns:
            List of Candidate objects with ticker symbols only (ORH/ORL = None)
        """
        logger.info("Starting candidate scan...")

        # Step 1 & 2: Run scans concurrently
        logger.info(
            "Scanning for gaps and fetching ASX announcements concurrently..."
        )
        gap_scan_task = self.scanner.scan_for_gaps(self.gap_threshold)
        announcement_task = asyncio.to_thread(
            self.asx_scanner.fetch_price_sensitive_announcements
        )
        results = await asyncio.gather(
            gap_scan_task, announcement_task, return_exceptions=True
        )

        gap_stocks = results[0]
        announcements = results[1]

        if isinstance(gap_stocks, Exception):
            logger.error(f"Failed to scan for gaps: {gap_stocks}")
            return []
        if isinstance(announcements, Exception):
            logger.error(f"Failed to fetch ASX announcements: {announcements}")
            return []

        if not gap_stocks or not announcements:
            logger.warning("No gaps or announcements found. Ending scan.")
            return []

        # Build ticker -> headline mapping (concatenate multiple announcements)
        announcement_map: dict[str, str] = {}
        for ann in announcements:
            headline_truncated = ann.headline[:80]
            if ann.ticker in announcement_map:
                announcement_map[ann.ticker] += f" | {headline_truncated}"
            else:
                announcement_map[ann.ticker] = headline_truncated

        price_sensitive_tickers = set(announcement_map.keys())

        logger.info(
            f"Found {len(gap_stocks)} gaps and {len(price_sensitive_tickers)} announcements."
        )

        # Step 3: Match gap stocks to announcements
        matched_stocks = [
            stock
            for stock in gap_stocks
            if stock.ticker in price_sensitive_tickers
        ]
        if not matched_stocks:
            logger.warning(
                "No gap stocks matched with price-sensitive announcements."
            )
            return []

        logger.info(
            f"{len(matched_stocks)} stocks have both a gap and an announcement."
        )

        # Step 4: Create Candidate objects (without ORH/ORL - will be set by RangeTracker)
        candidates = [
            Candidate(
                ticker=stock.ticker,
                scan_date=datetime.now().isoformat(),
                status="watching",
                or_high=None,  # Will be set by RangeTracker
                or_low=None,  # Will be set by RangeTracker
                gap_percent=stock.gap_percent,
                headline=announcement_map.get(stock.ticker),
            )
            for stock in matched_stocks
        ]

        logger.info(f"Scan complete. Found {len(candidates)} candidates.")
        return candidates
