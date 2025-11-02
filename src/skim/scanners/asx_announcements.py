"""ASX price-sensitive announcements scraper"""

import requests
from bs4 import BeautifulSoup
from loguru import logger


class ASXAnnouncementScanner:
    """Scanner for ASX price-sensitive announcements"""

    ASX_URL = "https://www.asx.com.au/asx/v2/statistics/todayAnns.do"

    def fetch_price_sensitive_tickers(self) -> set[str]:
        """Fetch today's price-sensitive announcements from ASX

        Returns:
            Set of ticker symbols with price-sensitive announcements today
        """
        try:
            logger.info("Fetching price-sensitive announcements from ASX...")

            response = requests.get(self.ASX_URL, timeout=10)
            response.raise_for_status()

            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, "lxml")

            # Find all table rows
            rows = soup.find_all("tr")

            price_sensitive_tickers = set()

            for row in rows:
                # Check if row contains "pricesens" indicator
                if "pricesens" in str(row):
                    # Extract ticker from first <td> element
                    cells = row.find_all("td")
                    if cells:
                        ticker = cells[0].get_text(strip=True)
                        if ticker:
                            price_sensitive_tickers.add(ticker)

            logger.info(
                f"Found {len(price_sensitive_tickers)} price-sensitive announcements today"
            )
            return price_sensitive_tickers

        except requests.exceptions.Timeout:
            logger.warning(
                "ASX announcement fetch timed out, continuing without filter"
            )
            return set()
        except requests.exceptions.RequestException as e:
            logger.warning(
                f"Error fetching ASX announcements: {e}, continuing without filter"
            )
            return set()
        except Exception as e:
            logger.warning(
                f"Unexpected error parsing ASX announcements: {e}, continuing without filter"
            )
            return set()
