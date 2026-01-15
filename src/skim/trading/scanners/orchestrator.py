"""Scanner orchestrator for managing multiple scanners"""

from loguru import logger

from skim.domain.models.event import Event, EventType
from skim.domain.repositories import CandidateRepository


class ScannerOrchestrator:
    """Manages multiple scanners and publishes events"""

    def __init__(self, event_bus, repository: CandidateRepository):
        """Initialize scanner orchestrator

        Args:
            event_bus: EventBus for publishing scan results
            repository: Repository for persisting candidates
        """
        self.event_bus = event_bus
        self.repository = repository
        self.scanners: list = []

    def register_scanner(self, scanner) -> None:
        """Add a scanner to the orchestrator

        Args:
            scanner: Scanner instance implementing Scanner protocol
        """
        self.scanners.append(scanner)
        logger.info(f"Registered scanner: {scanner.name}")

    async def run_all(self) -> dict[str, int]:
        """Run all scanners and publish events

        Returns:
            Dictionary mapping scanner names to candidate counts
        """
        logger.info("Running all scanners...")
        results = {}

        for scanner in sorted(self.scanners, key=lambda s: s.priority):
            logger.info(f"Running scanner: {scanner.name}")
            candidates = await scanner.scan()
            count = len(candidates)
            results[scanner.name] = count

            for candidate in candidates:
                self.repository.save(candidate)

            logger.info(f"{scanner.name} scanner found {count} candidates")

            await self.event_bus.publish(
                Event(
                    type=EventType.CANDIDATES_SCANNED,
                    data={
                        "scanner_name": scanner.name,
                        "candidates": [
                            _candidate_to_dict(c) for c in candidates
                        ],
                        "count": count,
                    },
                )
            )

        total = sum(results.values())
        logger.info(f"All scanners completed. Total candidates: {total}")
        return results


def _candidate_to_dict(candidate) -> dict:
    """Convert candidate to dictionary

    Args:
        candidate: Candidate instance

    Returns:
        Dictionary representation of candidate
    """
    from dataclasses import asdict

    if hasattr(candidate, "to_dict"):
        return candidate.to_dict()
    return asdict(candidate)
