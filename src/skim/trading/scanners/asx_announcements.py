"""ASX price-sensitive announcements scraper"""

from datetime import datetime

import requests
from bs4 import BeautifulSoup
from loguru import logger

from skim.trading.validation.scanners import (
    ASXAnnouncement,
    PriceSensitiveFilter,
)


class ASXAnnouncementScanner:
    """Scanner for ASX price-sensitive announcements"""

    ASX_URL = "https://www.asx.com.au/asx/v2/statistics/todayAnns.do"

    def fetch_price_sensitive_announcements(
        self, filter_config: PriceSensitiveFilter | None = None
    ) -> list[ASXAnnouncement]:
        """Fetch detailed price-sensitive announcements from ASX

        Args:
            filter_config: Optional filter configuration for announcements

        Returns:
            List of validated ASXAnnouncement objects
        """
        if filter_config is None:
            filter_config = PriceSensitiveFilter()

        try:
            logger.info(
                "Fetching detailed price-sensitive announcements from ASX..."
            )

            response = requests.get(self.ASX_URL, timeout=10)
            response.raise_for_status()

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, "lxml")

            # Find all table rows
            rows = soup.find_all("tr")

            announcements = []

            for row in rows:
                # Check if row contains "pricesens" indicator
                if "pricesens" in str(row):
                    # Extract data from table cells
                    cells = row.find_all("td")
                    if len(cells) >= 3:
                        try:
                            ticker = cells[0].get_text(strip=True)
                            headline = cells[1].get_text(strip=True)

                            # Apply ticker length filter
                            if not (
                                filter_config.min_ticker_length
                                <= len(ticker)
                                <= filter_config.max_ticker_length
                            ):
                                continue

                            # Apply headline length filter
                            if not (
                                filter_config.min_headline_length
                                <= len(headline)
                                <= filter_config.max_headline_length
                            ):
                                continue

                            # Apply include/exclude filters
                            if (
                                filter_config.include_only_tickers
                                and ticker
                                not in filter_config.include_only_tickers
                            ):
                                continue

                            if (
                                filter_config.exclude_tickers
                                and ticker in filter_config.exclude_tickers
                            ):
                                continue

                            # Parse timestamp (basic parsing - could be enhanced)
                            timestamp = datetime.now()  # Simplified for now

                            # Create validated announcement
                            announcement = ASXAnnouncement(
                                ticker=ticker,
                                headline=headline,
                                announcement_type="pricesens",
                                timestamp=timestamp,
                                pdf_url=None,
                            )
                            announcements.append(announcement)

                        except Exception as validation_error:
                            logger.warning(
                                f"Announcement validation failed: {validation_error}"
                            )
                            continue

            logger.info(
                f"Found {len(announcements)} valid price-sensitive announcements"
            )
            return announcements

        except requests.exceptions.Timeout:
            logger.warning(
                "ASX announcement fetch timed out, returning empty list"
            )
            return []
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Error fetching ASX announcements: {e}, returning empty list"
            )
            return []
        except Exception as e:
            logger.warning(
                f"Unexpected error parsing ASX announcements: {e}, returning empty list"
            )
            return []
