"""Scanner module - finds candidates with gap + announcement + opening range data"""

import asyncio
import time
from datetime import datetime

from loguru import logger

from .brokers.protocols import MarketDataProvider, ScannerService
from .data.models import Candidate
from .scanners.asx_announcements import ASXAnnouncementScanner
from .validation.scanners import BreakoutSignal, GapStock, OpeningRangeData


class Scanner:
    """Scans market for trading candidates"""

    def __init__(
        self,
        scanner_service: ScannerService,
        market_data_service: MarketDataProvider,
        gap_threshold: float = 3.0,
    ):
        """Initialise scanner with required services.

        Args:
            scanner_service: Service for running market scans.
            market_data_service: Service for fetching market data.
            gap_threshold: Minimum gap percentage to consider.
        """
        self.scanner = scanner_service
        self.market_data = market_data_service
        self.gap_threshold = gap_threshold
        self.asx_scanner = ASXAnnouncementScanner()

    async def find_candidates(self) -> list[Candidate]:
        """
        Finds candidates with gap + announcement + opening range data.

        Workflow:
        1. Scan for gaps > threshold.
        2. Fetch ASX announcements.
        3. Match gap stocks to announcements.
        4. Track opening ranges for matched stocks.
        5. Filter for breakouts.
        6. Return candidates.
        """
        logger.info("Starting candidate scan...")

        # Step 1 & 2: Run scans concurrently
        logger.info(
            "Scanning for gaps and fetching ASX announcements concurrently..."
        )
        gap_scan_task = self.scanner.scan_for_gaps(self.gap_threshold)
        announcement_task = asyncio.to_thread(
            self.asx_scanner.fetch_price_sensitive_tickers
        )
        results = await asyncio.gather(
            gap_scan_task, announcement_task, return_exceptions=True
        )

        gap_stocks = results[0]
        price_sensitive_tickers = results[1]

        if isinstance(gap_stocks, Exception):
            logger.error(f"Failed to scan for gaps: {gap_stocks}")
            return []
        if isinstance(price_sensitive_tickers, Exception):
            logger.error(
                f"Failed to fetch ASX announcements: {price_sensitive_tickers}"
            )
            return []

        if not gap_stocks or not price_sensitive_tickers:
            logger.warning("No gaps or announcements found. Ending scan.")
            return []

        logger.info(
            f"Found {len(gap_stocks)} gaps and {len(price_sensitive_tickers)} announcements."
        )

        # Step 3: Match gap stocks to announcements
        matched_stocks = [
            stock
            for stock in gap_stocks
            if stock.ticker in price_sensitive_tickers
        ]
        if not matched_stocks:
            logger.warning(
                "No gap stocks matched with price-sensitive announcements."
            )
            return []

        logger.info(
            f"{len(matched_stocks)} stocks have both a gap and an announcement."
        )

        # Step 4: Track opening ranges for matched stocks
        or_data_list = await self.track_opening_range(matched_stocks)
        if not or_data_list:
            logger.warning("Opening range tracking yielded no valid data.")
            return []

        # Step 5: Filter for breakouts
        breakout_signals = self.filter_breakouts(or_data_list)
        if not breakout_signals:
            logger.warning("No breakout signals found after filtering.")
            return []

        # Step 6: Create Candidate objects
        candidates = [
            Candidate(
                ticker=signal.ticker,
                or_high=signal.or_high,
                or_low=signal.or_low,
                scan_date=signal.timestamp.isoformat(),
                status="watching",
            )
            for signal in breakout_signals
        ]

        logger.info(f"Scan complete. Found {len(candidates)} final candidates.")
        return candidates

    async def track_opening_range(
        self,
        gap_stocks: list[GapStock],
        duration_seconds: int = 600,
        poll_interval: int = 30,
    ) -> list[OpeningRangeData]:
        """Track opening range for gap candidates."""
        if not gap_stocks:
            return []

        logger.info(
            f"Tracking opening range for {len(gap_stocks)} candidates for {duration_seconds}s."
        )

        tickers = [stock.ticker for stock in gap_stocks]
        tracking_data = {
            stock.ticker: {
                "conid": stock.conid,
                "high": None,
                "low": None,
                "open": None,
                "prev_close": None,
                "gap_holding": True,
            }
            for stock in gap_stocks
        }

        end_time = time.time() + duration_seconds
        while time.time() < end_time:
            market_data_batch = await self.market_data.get_market_data(tickers)

            if not isinstance(market_data_batch, dict):
                logger.error(
                    "Expected a dict from batch market data request, got something else."
                )
                await asyncio.sleep(poll_interval)
                continue

            for ticker, market_data in market_data_batch.items():
                if not market_data or not market_data.last_price:
                    continue

                ticker_data = tracking_data[ticker]
                current_price = market_data.last_price

                if ticker_data["open"] is None:
                    ticker_data["open"] = current_price
                    ticker_data["high"] = current_price
                    ticker_data["low"] = current_price
                    ticker_data["prev_close"] = market_data.prior_close
                else:
                    ticker_data["high"] = max(
                        ticker_data["high"], current_price
                    )
                    ticker_data["low"] = min(ticker_data["low"], current_price)

                # Check if gap is holding
                if (
                    ticker_data["open"]
                    and current_price < ticker_data["open"] * 0.95
                ):
                    ticker_data["gap_holding"] = False

            await asyncio.sleep(poll_interval)

        # Compile results
        results = []
        final_market_data = await self.market_data.get_market_data(tickers)
        if not isinstance(final_market_data, dict):
            logger.error("Failed to get final market data for OR tracking.")
            return []

        for stock in gap_stocks:
            ticker_data = tracking_data[stock.ticker]
            market_data = final_market_data.get(stock.ticker)

            if not all(
                ticker_data.get(k) is not None
                for k in ["high", "low", "open", "prev_close"]
            ):
                logger.warning(
                    f"Skipping {stock.ticker} due to incomplete tracking data."
                )
                continue

            try:
                or_data = OpeningRangeData(
                    ticker=stock.ticker,
                    conid=stock.conid,
                    or_high=float(ticker_data["high"]),
                    or_low=float(ticker_data["low"]),
                    open_price=float(ticker_data["open"]),
                    prev_close=float(ticker_data["prev_close"]),
                    current_price=float(
                        market_data.last_price
                        if market_data
                        else ticker_data["open"]
                    ),
                    gap_holding=bool(ticker_data["gap_holding"]),
                )
                results.append(or_data)
            except Exception as e:
                logger.warning(
                    f"Validation failed for {stock.ticker} OR data: {e}"
                )

        logger.info(
            f"Opening range tracking complete. Compiled {len(results)} results."
        )
        return results

    def filter_breakouts(
        self, or_data_list: list[OpeningRangeData]
    ) -> list[BreakoutSignal]:
        """Filter for stocks with gap holding and ORH breakout."""
        if not or_data_list:
            return []

        logger.info(f"Filtering {len(or_data_list)} candidates for breakouts.")
        breakouts = []
        for data in or_data_list:
            try:
                if not data.gap_holding:
                    logger.debug(f"{data.ticker} excluded: gap not holding.")
                    continue

                if data.current_price <= data.or_high:
                    logger.debug(f"{data.ticker} excluded: no ORH breakout.")
                    continue

                or_size_pct = (
                    ((data.or_high - data.or_low) / data.or_low * 100)
                    if data.or_low > 0
                    else 0
                )
                gap_pct = (
                    (
                        (data.open_price - data.prev_close)
                        / data.prev_close
                        * 100
                    )
                    if data.prev_close > 0
                    else 0
                )

                signal = BreakoutSignal(
                    ticker=data.ticker,
                    conid=data.conid,
                    gap_pct=gap_pct,
                    or_high=data.or_high,
                    or_low=data.or_low,
                    or_size_pct=or_size_pct,
                    current_price=data.current_price,
                    entry_signal="ORB_HIGH_BREAKOUT",
                    timestamp=datetime.now(),
                )
                breakouts.append(signal)
                logger.info(
                    f"Breakout detected: {data.ticker} @ {data.current_price}"
                )

            except Exception as e:
                logger.error(f"Error filtering {data.ticker} for breakout: {e}")

        logger.info(f"Found {len(breakouts)} valid breakouts.")
        return breakouts
