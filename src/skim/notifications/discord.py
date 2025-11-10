"""Discord webhook notification service for Skim trading bot"""

from datetime import datetime
from typing import Any

import requests
from loguru import logger


class DiscordNotifier:
    """Discord webhook notification service"""

    def __init__(self, webhook_url: str | None):
        """Initialise Discord notifier

        Args:
            webhook_url: Discord webhook URL for sending notifications
        """
        self.webhook_url = webhook_url

    def send_scan_results(
        self, candidates_found: int, candidates: list[dict[str, Any]]
    ) -> bool:
        """Send scan results notification to Discord

        Args:
            candidates_found: Number of candidates found
            candidates: List of candidate dictionaries with ticker, gap_percent, price

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.debug(
                "No Discord webhook URL configured, skipping notification"
            )
            return False

        try:
            embed = self._build_embed(candidates_found, candidates)
            payload = {"embeds": [embed]}

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()

            logger.info("Discord notification sent successfully")
            return True

        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Failed to send Discord notification (connection error): {e}"
            )
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Failed to send Discord notification (timeout): {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(
                f"Failed to send Discord notification (HTTP error): {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Failed to send Discord notification (unexpected error): {e}"
            )
            return False

    def _build_embed(
        self, candidates_found: int, candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build Discord embed for scan results

        Args:
            candidates_found: Number of candidates found
            candidates: List of candidate dictionaries

        Returns:
            Discord embed dictionary
        """
        if candidates_found < 0:
            # Error case
            return {
                "title": "ASX Market Scan Error",
                "description": "An error occurred during market scanning",
                "color": 0xFF0000,  # Red
                "timestamp": datetime.now().isoformat(),
            }
        elif candidates_found == 0:
            # No candidates found
            return {
                "title": "ASX Market Scan Complete",
                "description": "No new candidates found with price-sensitive announcements",
                "color": 0xFFFF00,  # Yellow
                "timestamp": datetime.now().isoformat(),
            }
        else:
            # Success case
            return {
                "title": "ASX Market Scan Complete",
                "description": f"{candidates_found} new candidates found",
                "color": 0x00FF00,  # Green
                "fields": [
                    {
                        "name": "New Candidates",
                        "value": self._format_candidate_list(candidates),
                        "inline": False,
                    }
                ],
                "timestamp": datetime.now().isoformat(),
            }

    def _format_candidate_list(self, candidates: list[dict[str, Any]]) -> str:
        """Format candidate list for Discord display

        Args:
            candidates: List of candidate dictionaries

        Returns:
            Formatted string for Discord
        """
        if not candidates:
            return "None"

        formatted_candidates = []
        for candidate in candidates:
            ticker = candidate.get("ticker", "UNKNOWN")
            gap_percent = candidate.get("gap_percent")
            price = candidate.get("price")

            gap_str = (
                f"{gap_percent:.1f}%" if gap_percent is not None else "N/A"
            )
            price_str = f"${price:.2f}" if price is not None else "N/A"

            formatted_candidates.append(
                f"• {ticker} - Gap: {gap_str}, Price: {price_str}"
            )

        return "\n".join(formatted_candidates)
