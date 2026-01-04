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

    def send_gap_candidates(
        self, candidates_found: int, candidates: list[dict[str, Any]]
    ) -> bool:
        """Send gap-only candidates notification

        Args:
            candidates_found: Number of candidates found
            candidates: List of candidate dictionaries with ticker, gap_percent

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.debug(
                "No Discord webhook URL configured, skipping notification"
            )
            return False

        try:
            embed = self._build_gap_embed(candidates_found, candidates)
            payload = {"embeds": [embed]}

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()

            logger.info("Discord gap notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord gap notification: {e}")
            return False

    def send_news_candidates(
        self, candidates_found: int, candidates: list[dict[str, Any]]
    ) -> bool:
        """Send news-only candidates notification

        Args:
            candidates_found: Number of candidates found
            candidates: List of candidate dictionaries with ticker, headline

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.debug(
                "No Discord webhook URL configured, skipping notification"
            )
            return False

        try:
            embed = self._build_news_embed(candidates_found, candidates)
            payload = {"embeds": [embed]}

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()

            logger.info("Discord news notification sent successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to send Discord news notification: {e}")
            return False

    def send_trade_notification(
        self,
        action: str,
        ticker: str,
        quantity: int,
        price: float,
        pnl: float | None = None,
    ) -> bool:
        """Send trade execution notification (entries and exits)."""
        if not self.webhook_url:
            logger.debug(
                "No Discord webhook URL configured, skipping notification"
            )
            return False

        try:
            embed = self._build_trade_embed(
                action=action,
                ticker=ticker,
                quantity=quantity,
                price=price,
                pnl=pnl,
            )
            payload = {"embeds": [embed]}

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Discord trade notification sent successfully")
            return True

        except requests.exceptions.ConnectionError as e:
            logger.error(
                f"Failed to send trade notification (connection error): {e}"
            )
            return False
        except requests.exceptions.Timeout as e:
            logger.error(f"Failed to send trade notification (timeout): {e}")
            return False
        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to send trade notification (HTTP error): {e}")
            return False
        except Exception as e:
            logger.error(
                f"Failed to send trade notification (unexpected error): {e}"
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
            headline = candidate.get("headline")

            gap_str = (
                f"{gap_percent:.1f}%" if gap_percent is not None else "N/A"
            )
            headline_str = headline if headline else "No announcement"

            formatted_candidates.append(
                f"• **{ticker}** - Gap: {gap_str}\n  {headline_str}"
            )

        return "\n".join(formatted_candidates)

    def _build_trade_embed(
        self,
        action: str,
        ticker: str,
        quantity: int,
        price: float,
        pnl: float | None = None,
    ) -> dict[str, Any]:
        """Build Discord embed for trade events."""
        color = 0x00FF00 if action.upper() == "BUY" else 0xFF0000
        fields = [
            {"name": "Ticker", "value": ticker, "inline": True},
            {"name": "Action", "value": action.upper(), "inline": True},
            {"name": "Quantity", "value": str(quantity), "inline": True},
            {"name": "Price", "value": f"${price:.4f}", "inline": True},
        ]
        if pnl is not None:
            fields.append(
                {"name": "PnL", "value": f"${pnl:.2f}", "inline": True}
            )

        return {
            "title": "Trade Executed",
            "description": f"{action.upper()} {ticker}",
            "color": color,
            "fields": fields,
            "timestamp": datetime.now().isoformat(),
        }

    def _build_gap_embed(
        self, candidates_found: int, candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build Discord embed for gap candidates

        Args:
            candidates_found: Number of candidates found
            candidates: List of candidate dictionaries

        Returns:
            Discord embed dictionary
        """
        if candidates_found == 0:
            return {
                "title": "Gap Scan Complete",
                "description": "No gap candidates found",
                "color": 0xFFFF00,  # Yellow
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "title": "Gap Scan Complete",
                "description": f"{candidates_found} gap candidates found",
                "color": 0xFF6600,  # Orange
                "fields": [
                    {
                        "name": "Gap Candidates",
                        "value": self._format_gap_candidate_list(candidates),
                        "inline": False,
                    }
                ],
                "timestamp": datetime.now().isoformat(),
            }

    def _build_news_embed(
        self, candidates_found: int, candidates: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build Discord embed for news candidates

        Args:
            candidates_found: Number of candidates found
            candidates: List of candidate dictionaries

        Returns:
            Discord embed dictionary
        """
        if candidates_found == 0:
            return {
                "title": "News Scan Complete",
                "description": "No news candidates found",
                "color": 0xFFFF00,  # Yellow
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "title": "News Scan Complete",
                "description": f"{candidates_found} news candidates found",
                "color": 0x0099FF,  # Blue
                "fields": [
                    {
                        "name": "News Candidates",
                        "value": self._format_news_candidate_list(candidates),
                        "inline": False,
                    }
                ],
                "timestamp": datetime.now().isoformat(),
            }

    def _format_gap_candidate_list(
        self, candidates: list[dict[str, Any]]
    ) -> str:
        """Format gap candidate list for Discord display

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

            gap_str = (
                f"{gap_percent:.1f}%" if gap_percent is not None else "N/A"
            )

            formatted_candidates.append(f"• **{ticker}** - Gap: {gap_str}")

        return "\n".join(formatted_candidates)

    def _format_news_candidate_list(
        self, candidates: list[dict[str, Any]]
    ) -> str:
        """Format news candidate list for Discord display

        Args:
            candidates: List of candidate dictionaries

        Returns:
            Formatted string for Discord
        """
        if not candidates:
            return "None"

        formatted_candidates = []
        for candidate in candidates[:10]:
            ticker = candidate.get("ticker", "UNKNOWN")
            headline = candidate.get("headline", "No announcement")

            headline_truncated = headline[:80]

            formatted_candidates.append(
                f"• **{ticker}**\n  {headline_truncated}"
            )

        if len(candidates) > 10:
            formatted_candidates.append(
                f"\n... and {len(candidates) - 10} more"
            )

        return "\n".join(formatted_candidates)
