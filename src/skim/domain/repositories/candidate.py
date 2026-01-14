"""Candidate repository protocol"""

from typing import Protocol

from ..models import Candidate


class CandidateRepository(Protocol):
    """Candidate repository protocol"""

    def save(self, candidate: Candidate) -> None:
        """Save or update candidate"""
        ...

    def get_tradeable(self) -> list[Candidate]:
        """Get candidates ready for trading"""
        ...

    def get_alertable(self) -> list[Candidate]:
        """Get candidates for alerting"""
        ...

    def purge(self) -> int:
        """Purge all candidates"""
        ...
