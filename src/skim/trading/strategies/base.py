"""Base strategy interface"""

from __future__ import annotations

from abc import ABC, abstractmethod


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
