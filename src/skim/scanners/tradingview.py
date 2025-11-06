"""TradingView scanner API client"""

from typing import NamedTuple

import requests
from loguru import logger


class GapStock(NamedTuple):
    """Stock with gap data from TradingView"""

    ticker: str
    gap_percent: float
    close_price: float


class TradingViewScanner:
    """Client for TradingView scanner API"""

    API_URL = "https://scanner.tradingview.com/australia/scan"

    def scan_for_gaps(self, min_gap: float) -> list[GapStock]:
        """Query TradingView scanner API for ASX stocks with gaps

        Args:
            min_gap: Minimum gap percentage (change_from_open)

        Returns:
            List of GapStock objects sorted by gap percentage (descending)
        """
        try:
            payload = self._build_payload(min_gap)
            headers = self._build_headers()

            logger.info(f"Querying TradingView for gaps > {min_gap}%")

            response = requests.post(
                self.API_URL, json=payload, headers=headers, timeout=10
            )
            response.raise_for_status()

            data = response.json()
            results = self._parse_response(data)

            logger.info(
                f"TradingView returned {len(results)} stocks with gaps > {min_gap}%"
            )
            return results

        except requests.exceptions.RequestException as e:
            logger.error(f"Error querying TradingView API: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error querying TradingView: {e}")
            return []

    def _build_payload(self, min_gap: float) -> dict:
        """Build TradingView API request payload

        Args:
            min_gap: Minimum gap percentage

        Returns:
            API payload dictionary
        """
        return {
            "markets": ["australia"],
            "symbols": {"query": {"types": []}, "tickers": []},
            "options": {"lang": "en"},
            "columns": ["name", "close", "change_from_open"],
            "sort": {"sortBy": "change_from_open", "sortOrder": "desc"},
            "range": [0, 100],
            "filter": [
                {
                    "left": "change_from_open",
                    "operation": "greater",
                    "right": min_gap,
                }
            ],
        }

    def _build_headers(self) -> dict:
        """Build HTTP headers to mimic browser request

        Returns:
            Headers dictionary
        """
        return {
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "origin": "https://www.tradingview.com",
            "referer": "https://www.tradingview.com/",
            "accept": "text/plain, */*; q=0.01",
            "sec-fetch-site": "same-site",
            "sec-fetch-mode": "cors",
            "sec-fetch-dest": "empty",
        }

    def _parse_response(self, data: dict) -> list[GapStock]:
        """Parse TradingView API response into GapStock objects

        Args:
            data: JSON response from TradingView API

        Returns:
            List of GapStock objects
        """
        results = []

        for item in data.get("data", []):
            ticker = item.get("s", "")  # Symbol like "ASX:BHP"
            values = item.get("d")

            if values is not None and len(values) >= 3:
                # Extract ticker name (remove ASX: prefix)
                ticker_name = ticker.replace("ASX:", "")
                close_price = float(values[1]) if values[1] else 0.0
                gap_percent = float(values[2]) if values[2] else 0.0

                results.append(
                    GapStock(
                        ticker=ticker_name,
                        gap_percent=gap_percent,
                        close_price=close_price,
                    )
                )

        return results
