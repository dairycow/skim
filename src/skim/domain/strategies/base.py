"""Event-driven Strategy interface"""

from abc import ABC, abstractmethod

from skim.domain.models import Event, Signal


class Strategy(ABC):
    """Base strategy interface - event-driven"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Strategy name"""

    @abstractmethod
    async def on_event(self, event: Event) -> list[Signal]:
        """Process event and return trading signals"""

    async def initialize(self) -> None:  # noqa: B027
        """Optional initialization hook"""
        pass

    async def shutdown(self) -> None:  # noqa: B027
        """Optional cleanup hook"""
        pass
