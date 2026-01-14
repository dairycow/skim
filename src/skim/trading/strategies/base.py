"""Base strategy interface"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


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

    async def scan_gaps(self) -> int:
        """Scan for gap candidates

        Returns:
            Number of gap candidates found
        """
        return 0

    async def scan_news(self) -> int:
        """Scan for news candidates

        Returns:
            Number of news candidates found
        """
        return 0

    async def on_event(self, event) -> list:
        """Process event and return signals (event-driven interface)

        Args:
            event: Event to process

        Returns:
            List of signals generated
        """
        return []

    async def get_pending_signals(self) -> list:
        """Get pending signals for execution

        Returns:
            List of pending signals
        """
        return []
