"""Candidate repository protocol"""

from typing import Protocol

from ..models import Candidate


class CandidateRepository(Protocol):
    """Candidate repository protocol"""

    def save(self, candidate: Candidate) -> None:
        """Save or update candidate"""
        ...

    def get_tradeable(self) -> list[Candidate]:
        """Get candidates ready for trading (gap + news + OR complete)"""
        ...

    def get_alertable(self) -> list[Candidate]:
        """Get candidates for alerting (gap + news, no OR required)"""
        ...

    def get_gap_candidates(self) -> list[Candidate]:
        """Get all gap candidates with status='watching'"""
        ...

    def get_news_candidates(self) -> list[Candidate]:
        """Get all news candidates with status='watching'"""
        ...

    def get_candidates_needing_ranges(self) -> list[Candidate]:
        """Get gap+news candidates without opening ranges"""
        ...

    def save_opening_range(
        self, ticker: str, or_high: float, or_low: float
    ) -> None:
        """Save or update opening range for a candidate"""
        ...

    def purge(self) -> int:
        """Purge all candidates for this repository's strategy"""
        ...
