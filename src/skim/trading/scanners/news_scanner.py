"""News-only scanner - finds stocks with price-sensitive announcements"""

import asyncio
from datetime import datetime

from loguru import logger

from skim.domain.models import NewsCandidate
from skim.domain.models.ticker import Ticker

from .asx_announcements import ASXAnnouncementScanner


class NewsScanner:
    """Scanner for news-only stocks in play"""

    def __init__(self):
        """Initialise news scanner"""
        self.asx_scanner = ASXAnnouncementScanner()

    async def find_news_candidates(self) -> list[NewsCandidate]:
        """Find stocks with price-sensitive announcements

        Returns:
            List of NewsCandidate objects
        """
        logger.info("Scanning for news-only candidates...")

        announcements = await asyncio.to_thread(
            self.asx_scanner.fetch_price_sensitive_announcements
        )

        if not announcements:
            logger.info("No price-sensitive announcements found")
            return []

        logger.info(f"Found {len(announcements)} price-sensitive announcements")

        candidates = [
            NewsCandidate(
                ticker=Ticker(symbol=ann.ticker),
                scan_date=datetime.now(),
                status="watching",
                headline=ann.headline,
                announcement_type=ann.announcement_type,
                announcement_timestamp=ann.timestamp,
            )
            for ann in announcements
        ]

        logger.info(f"Scan complete. Found {len(candidates)} news candidates")
        return candidates
