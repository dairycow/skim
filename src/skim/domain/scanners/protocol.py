"""Scanner protocol for candidate scanning"""

from typing import Protocol

from ..models import Candidate


class Scanner(Protocol):
    """Protocol for candidate scanners

    Scanners are responsible for finding candidates based on specific criteria.
    Each scanner should have a name and priority for ordered execution.
    """

    @property
    def name(self) -> str:
        """Scanner identifier"""
        ...

    @property
    def priority(self) -> int:
        """Priority for execution order (lower = higher priority)"""
        ...

    async def scan(self) -> list[Candidate]:
        """Scan for candidates

        Returns:
            List of candidates found
        """
        ...
