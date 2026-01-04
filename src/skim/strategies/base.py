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
