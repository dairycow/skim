"""Filter protocol for candidate filtering"""

from typing import Protocol

from ..models import Candidate


class CandidateFilter(Protocol):
    """Protocol for candidate filters

    Filters are responsible for selecting which candidates should be traded
    based on specific criteria.
    """

    @property
    def name(self) -> str:
        """Filter identifier"""
        ...

    def filter(self, candidates: list[Candidate]) -> list[Candidate]:
        """Filter candidates based on criteria

        Args:
            candidates: List of candidates to filter

        Returns:
            Filtered list of candidates
        """
        ...
