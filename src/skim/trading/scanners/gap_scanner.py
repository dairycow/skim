"""Gap-only scanner - finds stocks with gaps"""

from datetime import datetime

from loguru import logger

from ..brokers.protocols import GapScannerService
from ..data.models import GapStockInPlay


class GapScanner:
    """Scanner for gap-only stocks in play"""

    def __init__(
        self,
        scanner_service: GapScannerService,
        gap_threshold: float = 3.0,
    ):
        """Initialise gap scanner

        Args:
            scanner_service: Service for running market scans
            gap_threshold: Minimum gap percentage to consider
        """
        self.scanner = scanner_service
        self.gap_threshold = gap_threshold

    async def find_gap_candidates(self) -> list[GapStockInPlay]:
        """Find stocks with gaps > threshold

        Returns:
            List of GapStockInPlay objects
        """
        logger.info("Scanning for gap-only candidates...")

        gap_stocks = await self.scanner.scan_for_gaps(self.gap_threshold)

        if not gap_stocks:
            logger.info("No gap stocks found")
            return []

        logger.info(
            f"Found {len(gap_stocks)} gap stocks > {self.gap_threshold}%"
        )

        candidates = [
            GapStockInPlay(
                ticker=stock.ticker,
                scan_date=datetime.now().isoformat(),
                status="watching",
                gap_percent=stock.gap_percent,
                conid=stock.conid,
            )
            for stock in gap_stocks
        ]

        logger.info(f"Scan complete. Found {len(candidates)} gap candidates")
        return candidates
