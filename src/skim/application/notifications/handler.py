"""Notification handler for Discord notifications"""

from loguru import logger

from skim.domain.models.event import Event
from skim.trading.notifications.discord import DiscordNotifier


class NotificationHandler:
    """Handles all Discord notifications via events"""

    def __init__(self, notifier: "DiscordNotifier"):
        """Initialize notification handler

        Args:
            notifier: Discord webhook service
        """
        self.notifier = notifier

    async def handle_trade_executed(self, event: Event) -> None:
        """Send trade execution notification

        Args:
            event: Event containing trade execution details
        """
        try:
            data = event.data or {}
            trade_data = data.get("trade", {})
            self.notifier.send_trade_notification(
                action=trade_data.get("action"),
                ticker=trade_data.get("ticker"),
                quantity=trade_data.get("quantity", 0),
                price=trade_data.get("price", 0.0),
                pnl=trade_data.get("pnl"),
            )
        except Exception as e:
            logger.error(f"Failed to handle trade executed event: {e}")

    async def handle_stop_hit(self, event: Event) -> None:
        """Send stop hit notification

        Args:
            event: Event containing stop hit details
        """
        try:
            data = event.data or {}
            position_data = data.get("position", {})
            self.notifier.send_trade_notification(
                action="SELL",
                ticker=position_data.get("ticker"),
                quantity=position_data.get("quantity", 0),
                price=position_data.get("exit_price", 0.0),
                pnl=position_data.get("pnl"),
            )
        except Exception as e:
            logger.error(f"Failed to handle stop hit event: {e}")

    async def handle_candidates_alerted(self, event: Event) -> None:
        """Send candidates alert notification

        Args:
            event: Event containing candidates alert details
        """
        try:
            data = event.data or {}
            candidates = data.get("candidates", [])
            count = data.get("count", len(candidates))
            self.notifier.send_tradeable_candidates(count, candidates)
        except Exception as e:
            logger.error(f"Failed to handle candidates alerted event: {e}")

    async def handle_scan_complete(self, event: Event) -> None:
        """Send scan summary notification (optional)

        Args:
            event: Event containing scan results
        """
        logger.debug("Scan complete notification not implemented")
        pass
