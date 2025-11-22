from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from skim.data.models import Candidate, Position


class Trader(Protocol):
    """Executes trading orders for entries and exits"""

    async def execute_breakouts(self, candidates: list[Candidate]) -> int:
        """Execute breakout entries when price > or_high"""
        ...

    async def execute_stops(self, positions: list[Position]) -> int:
        """Execute stop loss exits when price < stop_loss"""
        ...
