"""Position repository protocol"""

from typing import Protocol

from ..models import Position


class PositionRepository(Protocol):
    """Position repository protocol"""

    def create(self, position: Position) -> int:
        """Create position, return ID"""
        ...

    def get_open(self) -> list[Position]:
        """Get all open positions"""
        ...

    def close(
        self, position_id: int, exit_price: float, exit_date: str
    ) -> None:
        """Close position"""
        ...
