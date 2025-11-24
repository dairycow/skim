"""Range Tracker - Establishes opening range high/low for candidates

Responsibility:
- Sample market data at 10:10 AM (10 minutes after market open)
- Extract high/low values as ORH/ORL
- Update candidates table with opening range values
"""

import asyncio
from datetime import datetime, time

from loguru import logger

from .brokers.protocols import MarketDataProvider
from .data.database import Database


class RangeTracker:
    """Tracks and stores opening range values for candidates"""

    def __init__(
        self,
        market_data_service: MarketDataProvider,
        db: Database,
        market_open_time: time = time(10, 0),  # 10:00 AM
        range_duration_minutes: int = 10,
    ):
        """Initialize range tracker

        Args:
            market_data_service: Service for fetching market data
            db: Database for updating candidates
            market_open_time: Market opening time (default 10:00 AM)
            range_duration_minutes: Duration of opening range in minutes (default 10)
        """
        self.market_data = market_data_service
        self.db = db
        self.market_open_time = market_open_time
        self.range_duration_minutes = range_duration_minutes

    def _calculate_target_time(self) -> datetime:
        """Calculate the target time for sampling (market open + range duration)

        Returns:
            Datetime representing when to sample opening range
        """
        now = datetime.now()
        target_time = datetime.combine(
            now.date(),
            time(
                self.market_open_time.hour,
                self.market_open_time.minute + self.range_duration_minutes,
            ),
        )
        return target_time

    async def _wait_until_target_time(self) -> None:
        """Wait until the opening range window has elapsed"""
        target_time = self._calculate_target_time()
        now = datetime.now()

        if now < target_time:
            wait_seconds = (target_time - now).total_seconds()
            logger.info(
                f"Waiting {wait_seconds:.0f}s until {target_time.strftime('%H:%M:%S')} to sample opening ranges"
            )
            await asyncio.sleep(wait_seconds)
        else:
            logger.info(
                f"Target time {target_time.strftime('%H:%M:%S')} has passed, sampling now"
            )

    async def track_opening_ranges(self) -> int:
        """Track opening ranges for candidates without ORH/ORL values

        Workflow:
        1. Wait until opening range window has elapsed (10:10 AM)
        2. Get candidates with NULL or_high/or_low
        3. Fetch market data for each candidate
        4. Extract high/low from snapshot
        5. Update database with ORH/ORL values

        Returns:
            Number of candidates updated with opening range data
        """
        logger.info("Starting opening range tracking...")

        # Step 1: Wait until target time
        await self._wait_until_target_time()

        # Step 2: Get candidates without ranges
        candidates = self.db.get_candidates_without_ranges()
        if not candidates:
            logger.info("No candidates need opening range tracking")
            return 0

        logger.info(f"Tracking opening ranges for {len(candidates)} candidates")

        # Step 3-5: Fetch data and update for each candidate
        updated = 0
        tickers = [c.ticker for c in candidates]

        # Fetch market data for all candidates at once
        market_data_batch = await self.market_data.get_market_data(tickers)

        if not isinstance(market_data_batch, dict):
            logger.error(
                "Expected dict from batch market data request, cannot proceed"
            )
            return 0

        for candidate in candidates:
            try:
                market_data = market_data_batch.get(candidate.ticker)

                if not market_data:
                    logger.warning(
                        f"{candidate.ticker}: No market data available, will retry next run"
                    )
                    continue

                # Extract high/low from snapshot
                or_high = market_data.high
                or_low = market_data.low

                if or_high <= 0 or or_low <= 0:
                    logger.warning(
                        f"{candidate.ticker}: Invalid price data (high={or_high}, low={or_low}), will retry"
                    )
                    continue

                # Update database
                self.db.update_candidate_ranges(
                    candidate.ticker, or_high, or_low
                )

                logger.info(
                    f"{candidate.ticker}: Opening range set - ORH=${or_high:.2f}, ORL=${or_low:.2f}"
                )
                updated += 1

            except Exception as e:
                logger.error(
                    f"Failed to track opening range for {candidate.ticker}: {e}"
                )
                continue

        logger.info(
            f"Opening range tracking complete. Updated {updated}/{len(candidates)} candidates"
        )
        return updated
