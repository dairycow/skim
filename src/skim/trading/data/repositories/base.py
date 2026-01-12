"""Repository protocols for strategy-specific candidate management"""

from typing import Protocol


class CandidateRepository(Protocol):
    """Generic protocol for candidate repository implementations

    Each strategy should implement this protocol to provide
    strategy-specific candidate storage and retrieval.
    """

    @property
    def strategy_name(self) -> str:  # type: ignore[empty-body]
        """Strategy identifier"""

    def save_candidate(self, candidate) -> None:  # type: ignore[empty-body]
        """Save or update a candidate

        Args:
            candidate: Candidate object (type varies by strategy)
        """

    def get_tradeable_candidates(self) -> list:  # type: ignore[empty-body]
        """Get candidates ready for trading

        Returns:
            List of candidate objects ready for trading (type varies by strategy)
        """

    def purge(self) -> int:  # type: ignore[empty-body]
        """Purge all candidates for this strategy

        Returns:
            Number of candidates deleted
        """
