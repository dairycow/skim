"""Discord webhook notification service for Skim trading bot"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from typing import Any

import requests
from loguru import logger


@dataclass
class EmbedTemplate:
    """Template for Discord embed notifications"""

    title: str
    color: int
    empty_description: str
    success_description: Callable[[int], str]
    field_name: str
    formatter: Callable[[list[dict]], str]


def _handle_discord_errors(func: Callable) -> Callable:
    """Decorator to handle Discord webhook errors"""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> bool:
        try:
            return func(*args, **kwargs)
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

    return wrapper


def _format_gap_candidate_list(candidates: list[dict]) -> str:
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

        gap_str = f"{gap_percent:.1f}%" if gap_percent is not None else "N/A"

        formatted_candidates.append(f"• **{ticker}** - Gap: {gap_str}")

    return "\n".join(formatted_candidates)


def _format_news_candidate_list(candidates: list[dict]) -> str:
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

        formatted_candidates.append(f"• **{ticker}**\n  {headline_truncated}")

    if len(candidates) > 10:
        formatted_candidates.append(f"\n... and {len(candidates) - 10} more")

    return "\n".join(formatted_candidates)


def _format_candidate_list(candidates: list[dict]) -> str:
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

        gap_str = f"{gap_percent:.1f}%" if gap_percent is not None else "N/A"
        headline_str = headline if headline else "No announcement"

        formatted_candidates.append(
            f"• **{ticker}** - Gap: {gap_str}\n  {headline_str}"
        )

    return "\n".join(formatted_candidates)


SCAN_RESULTS_TEMPLATE = EmbedTemplate(
    title="ASX Market Scan Complete",
    color=0x00FF00,
    empty_description="No new candidates found with price-sensitive announcements",
    success_description=lambda count: f"{count} new candidates found",
    field_name="New Candidates",
    formatter=_format_candidate_list,
)

GAP_CANDIDATES_TEMPLATE = EmbedTemplate(
    title="Gap Scan Complete",
    color=0xFF6600,
    empty_description="No gap candidates found",
    success_description=lambda count: f"{count} gap candidates found",
    field_name="Gap Candidates",
    formatter=_format_gap_candidate_list,
)

NEWS_CANDIDATES_TEMPLATE = EmbedTemplate(
    title="News Scan Complete",
    color=0x0099FF,
    empty_description="No news candidates found",
    success_description=lambda count: f"{count} news candidates found",
    field_name="News Candidates",
    formatter=_format_news_candidate_list,
)


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
        if candidates_found < 0:
            return self._send_embed_notification(
                template=SCAN_RESULTS_TEMPLATE,
                candidates_found=candidates_found,
                candidates=candidates,
                is_error=True,
            )
        return self._send_embed_notification(
            template=SCAN_RESULTS_TEMPLATE,
            candidates_found=candidates_found,
            candidates=candidates,
        )

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
        return self._send_embed_notification(
            template=GAP_CANDIDATES_TEMPLATE,
            candidates_found=candidates_found,
            candidates=candidates,
        )

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
        return self._send_embed_notification(
            template=NEWS_CANDIDATES_TEMPLATE,
            candidates_found=candidates_found,
            candidates=candidates,
        )

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

    @_handle_discord_errors
    def _send_embed_notification(
        self,
        template: EmbedTemplate,
        candidates_found: int,
        candidates: list[dict[str, Any]],
        is_error: bool = False,
    ) -> bool:
        """Send Discord embed notification using template

        Args:
            template: EmbedTemplate with formatting configuration
            candidates_found: Number of candidates found
            candidates: List of candidate dictionaries
            is_error: Whether this is an error notification

        Returns:
            True if notification sent successfully, False otherwise
        """
        if not self.webhook_url:
            logger.debug(
                "No Discord webhook URL configured, skipping notification"
            )
            return False

        if is_error:
            embed = {
                "title": "ASX Market Scan Error",
                "description": "An error occurred during market scanning",
                "color": 0xFF0000,
                "timestamp": datetime.now().isoformat(),
            }
        elif candidates_found == 0:
            embed = {
                "title": template.title,
                "description": template.empty_description,
                "color": 0xFFFF00,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            embed = {
                "title": template.title,
                "description": template.success_description(candidates_found),
                "color": template.color,
                "fields": [
                    {
                        "name": template.field_name,
                        "value": template.formatter(candidates),
                        "inline": False,
                    }
                ],
                "timestamp": datetime.now().isoformat(),
            }

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
