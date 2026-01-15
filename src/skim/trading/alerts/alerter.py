"""Candidate alerter for Discord notifications"""

from loguru import logger

from skim.domain.models.event import Event, EventType
from skim.domain.repositories import CandidateRepository


class CandidateAlerter:
    """Alerts on tradeable candidates"""

    def __init__(self, repository: CandidateRepository, event_bus):
        """Initialize candidate alerter

        Args:
            repository: Repository for candidate queries
            event_bus: EventBus for publishing alert events
        """
        self.repository = repository
        self.event_bus = event_bus

    async def send_alerts(self) -> int:
        """Get alertable candidates and publish event

        Returns:
            Number of candidates alerted
        """
        logger.info("Sending alert for alertable candidates...")

        try:
            candidates = self.repository.get_alertable()
            count = len(candidates)

            if not candidates:
                logger.info("No alertable candidates to alert")
                return 0

            payload = [
                {
                    "ticker": c.ticker.symbol
                    if hasattr(c.ticker, "symbol")
                    else str(c.ticker),
                    "gap_percent": getattr(c, "gap_percent", None),
                    "headline": getattr(c, "headline", None),
                }
                for c in candidates
            ]

            await self.event_bus.publish(
                Event(
                    type=EventType.CANDIDATES_ALERTED,
                    data={"count": count, "candidates": payload},
                )
            )

            logger.info(
                f"Alert event published for {count} alertable candidates"
            )
            return count
        except Exception as e:
            logger.error(f"Alert failed: {e}", exc_info=True)
            return 0
