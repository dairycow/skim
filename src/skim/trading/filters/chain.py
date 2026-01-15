"""Filter chain for applying multiple filters"""

from loguru import logger

from skim.domain.models import Candidate


class FilterChain:
    """Applies multiple filters in sequence"""

    def __init__(self, filters: list):
        """Initialize filter chain

        Args:
            filters: List of filter instances
        """
        self.filters = filters

    def apply(self, candidates: list[Candidate]) -> list[Candidate]:
        """Apply all filters in sequence

        Args:
            candidates: List of candidates to filter

        Returns:
            Filtered list of candidates
        """
        result = candidates
        initial_count = len(candidates)

        for filter_obj in self.filters:
            previous_count = len(result)
            result = filter_obj.filter(result)
            rejected = previous_count - len(result)

            filter_name = getattr(filter_obj, "name", type(filter_obj).__name__)

            if rejected > 0:
                logger.info(
                    f"{filter_name} filter: rejected {rejected} candidates"
                )
            else:
                logger.debug(f"{filter_name} filter: all candidates passed")

        total_rejected = initial_count - len(result)
        logger.info(
            f"Filter chain complete: {initial_count} -> {len(result)} "
            f"(rejected {total_rejected})"
        )

        return result
