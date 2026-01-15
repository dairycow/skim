"""Base strategy interface and event types"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from skim.domain.models.event import Event, EventSignal, EventType


class Strategy(ABC):
    """Base trading strategy interface

    All trading strategies must implement this interface.
    A strategy is responsible for:
    - Signal generation (entry/exit logic)
    - Candidate identification and scanning
    - Position management
    - Strategy-specific lifecycle management
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name identifier"""

    @abstractmethod
    async def scan(self) -> int:
        """Scan for candidates

        Returns:
            Number of candidates found/created
        """

    @abstractmethod
    async def trade(self) -> int:
        """Execute trade entries

        Returns:
            Number of trades executed
        """

    @abstractmethod
    async def manage(self) -> int:
        """Manage open positions

        Returns:
            Number of positions managed/exited
        """

    async def on_event(self, event: Event) -> list[EventSignal]:
        """Handle an event and return signals.

        Default implementation dispatches to specific methods.
        Override this for event-driven strategies.

        Args:
            event: Event to handle

        Returns:
            List of signals generated
        """
        if event.type == EventType.SCAN:
            count = await self.scan()
            return [
                EventSignal(
                    ticker="", action="scan_complete", metadata={"count": count}
                )
            ]
        elif event.type == EventType.TRADE:
            count = await self.trade()
            return [
                EventSignal(
                    ticker="",
                    action="trade_complete",
                    metadata={"count": count},
                )
            ]
        elif event.type == EventType.MANAGE:
            count = await self.manage()
            return [
                EventSignal(
                    ticker="",
                    action="manage_complete",
                    metadata={"count": count},
                )
            ]
        elif event.type == EventType.ALERT:
            count = await self.alert()
            return [
                EventSignal(
                    ticker="",
                    action="alert_complete",
                    metadata={"count": count},
                )
            ]
        elif event.type == EventType.TRACK_RANGES:
            count = await self.track_ranges()
            return [
                EventSignal(
                    ticker="",
                    action="track_complete",
                    metadata={"count": count},
                )
            ]
        elif event.type == EventType.HEALTH_CHECK:
            healthy = await self.health_check()
            return [
                EventSignal(
                    ticker="",
                    action="health_check",
                    metadata={"healthy": healthy},
                )
            ]
        elif event.type == EventType.SETUP:
            await self.setup()
            return [EventSignal(ticker="", action="setup_complete")]
        return []

    async def health_check(self) -> bool:
        """Optional health check

        Returns:
            True if strategy is healthy
        """
        return True

    async def alert(self) -> int:
        """Send notifications for tradeable candidates

        Strategies can override this to send Discord alerts.
        Called after track_ranges completes and before trade execution.

        Returns:
            Number of candidates alerted
        """
        return 0

    async def track_ranges(self) -> int:
        """Track opening ranges for candidates

        Strategies can override this to track opening ranges.
        Some strategies (like ORH breakout) need to track opening ranges
        before executing trades.

        Returns:
            Number of candidates updated with opening ranges
        """
        return 0

    async def setup(self) -> None:
        """Setup strategy before scanning

        Strategies can override this for initialization tasks.
        Called once before the first scan.
        """
        pass

    async def scan_gaps(self) -> int:
        """Scan for gap candidates

        Trading-specific method for gap scanning.

        Returns:
            Number of gap candidates found
        """
        return 0

    async def scan_news(self) -> int:
        """Scan for news candidates

        Trading-specific method for news scanning.

        Returns:
            Number of news candidates found
        """
        return 0

    async def get_pending_signals(self) -> list[dict[str, Any]]:
        """Get pending signals for execution

        Trading-specific method to retrieve pending signals.

        Returns:
            List of pending signal dicts with ticker, action, price, quantity
        """
        return []
