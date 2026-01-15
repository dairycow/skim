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


def _format_tradeable_candidate_list(candidates: list[dict]) -> str:
    """Format tradeable candidate list for Discord display

    Args:
        candidates: List of candidate dictionaries with ticker, gap_percent,
                    headline, or_high (optional), or_low (optional)

    Returns:
        Formatted string for Discord (truncated if > 1024 chars)
    """
    if not candidates:
        return "None"

    formatted_candidates = []
    for candidate in candidates:
        ticker = candidate.get("ticker", "UNKNOWN")
        gap = (
            f"{candidate.get('gap_percent', 0):.1f}%"
            if candidate.get("gap_percent")
            else "N/A"
        )
        headline_str = candidate.get("headline", "") or "No headline"
        headline = (
            (headline_str[:55] + "...")
            if len(headline_str) > 55
            else headline_str
        )
        orh = (
            f"{candidate.get('or_high', 0):.2f}"
            if candidate.get("or_high")
            else "N/A"
        )
        orl = (
            f"{candidate.get('or_low', 0):.2f}"
            if candidate.get("or_low")
            else "N/A"
        )

        formatted = f"• **{ticker}** - Gap: {gap} | ORH: {orh} | ORL: {orl}\n  {headline}"
        formatted_candidates.append(formatted)

    result = "\n".join(formatted_candidates)
    if len(result) > 1024:
        result = result[:1007] + "\n... (truncated)"

    return result


TRADEABLE_CANDIDATES_TEMPLATE = EmbedTemplate(
    title="Tradeable Candidates Ready",
    color=0x00FF00,
    empty_description="No tradeable candidates found",
    success_description=lambda count: f"{count} tradeable candidates",
    field_name="Candidates",
    formatter=_format_tradeable_candidate_list,
)


class DiscordNotifier:
    """Discord webhook notification service"""

    def __init__(self, webhook_url: str | None):
        """Initialise Discord notifier

        Args:
            webhook_url: Discord webhook URL for sending notifications
        """
        self.webhook_url = webhook_url

    def send_tradeable_candidates(
        self, candidates_found: int, candidates: list[dict[str, Any]]
    ) -> bool:
        """Send tradeable candidates notification

        Args:
            candidates_found: Number of tradeable candidates found
            candidates: List of candidate dictionaries with ticker, gap_percent,
                        headline, or_high (optional), or_low (optional)

        Returns:
            True if notification sent successfully, False otherwise
        """
        return self._send_embed_notification(
            template=TRADEABLE_CANDIDATES_TEMPLATE,
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

    def alert(self, message: str) -> None:
        """Send an alert message (protocol compliance)

        Args:
            message: Alert message to send
        """
        if not self.webhook_url:
            logger.debug("No Discord webhook URL configured, skipping alert")
            return

        try:
            payload = {
                "embeds": [
                    {
                        "title": "Alert",
                        "description": message,
                        "color": 0xFFAA00,
                        "timestamp": datetime.now().isoformat(),
                    }
                ]
            }
            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10,
            )
            response.raise_for_status()
            logger.info("Discord alert sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")

    def notify_trade(self, trade_info: dict) -> None:
        """Notify of a trade (protocol compliance)

        Args:
            trade_info: Dictionary with trade details (action, ticker, quantity, price, pnl)
        """
        self.send_trade_notification(
            action=trade_info.get("action", "UNKNOWN"),
            ticker=trade_info.get("ticker", "UNKNOWN"),
            quantity=trade_info.get("quantity", 0),
            price=trade_info.get("price", 0.0),
            pnl=trade_info.get("pnl"),
        )
