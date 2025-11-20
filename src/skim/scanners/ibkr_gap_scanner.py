"""IBKR Gap Scanner for ASX stocks with opening range breakout detection

This module implements a gap scanner using IBKR's market scanner API
and real-time market data to identify opening range breakouts.
"""

import time
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from skim.brokers.ib_interface import MarketData
from skim.brokers.ibkr_client import IBKRClient
from skim.core.config import ScannerConfig
from skim.validation.scanners import (
    BreakoutSignal,
    GapStock,
    OpeningRangeData,
    ScannerValidationError,
)

if TYPE_CHECKING:
    from skim.data.database import Database
    from skim.data.models import Candidate


class IBKRGapScanner:
    """Scanner for ASX gap stocks using IBKR API with opening range breakout detection"""

    def __init__(
        self,
        paper_trading: bool = True,
        scanner_config: ScannerConfig | None = None,
    ):
        """Initialise IBKR gap scanner

        Args:
            paper_trading: If True, connect to paper trading account
            scanner_config: Scanner configuration parameters
        """
        self.client = IBKRClient(paper_trading=paper_trading)
        self._connected = False
        self.scanner_config = scanner_config or ScannerConfig()

    def _create_gap_scan_params(self, min_gap: float) -> dict:
        """Create scanner parameters to find ASX gap stocks

        Args:
            min_gap: Minimum gap percentage to filter

        Returns:
            Scanner parameters dictionary for IBKR API
        """
        try:
            # IBKR API parameters for ASX gap scanning
            scan_params = {
                "instrument": "STOCK.HK",  # Asian stocks (includes ASX)
                "type": "HIGH_OPEN_GAP",  # Top Close-to-Open % Gainers
                "filter": [
                    {
                        "code": "price",
                        "value": self.scanner_config.price_filter,
                    },
                    {
                        "code": "volume",
                        "value": self.scanner_config.volume_filter,
                    },
                ],
                "location": "STK.HK.ASX",  # Target ASX specifically
            }
            logger.debug(f"Created ASX gap scan parameters: {scan_params}")
            return scan_params
        except Exception as e:
            logger.error(f"Failed to create scanner parameters: {e}")
            raise ScannerValidationError(
                f"Invalid scanner parameters: {e}"
            ) from e

    def scan_for_gaps(self, min_gap: float) -> list[GapStock]:
        """Scan for ASX stocks with gaps using IBKR market scanner

        Args:
            min_gap: Minimum gap percentage to filter

        Returns:
            List of GapStock objects sorted by gap percentage (descending)
        """
        if not self._connected:
            logger.error("Scanner not connected - call connect() first")
            return []

        try:
            logger.info(f"Scanning for ASX gaps > {min_gap}%")

            # Create gap scan parameters
            scan_params = self._create_gap_scan_params(min_gap)
            logger.debug(f"Scanner parameters: {scan_params}")

            # Run IBKR scanner
            scanner_results = self.client.run_scanner(scan_params)
            logger.info(f"IBKR scanner returned {len(scanner_results)} results")

            gap_stocks = []
            for result in scanner_results:
                try:
                    # Extract required fields from scanner result
                    symbol = result.get("symbol")
                    conid = result.get("conid")
                    gap_percent = result.get("change_percent", 0.0)

                    # Validate required data
                    if not symbol or not conid:
                        logger.debug(
                            f"Skipping result with missing symbol/conid: {result}"
                        )
                        continue

                    # Filter by minimum gap requirement
                    if gap_percent >= min_gap:
                        try:
                            gap_stock = GapStock(
                                ticker=str(symbol),
                                gap_percent=float(gap_percent),
                                conid=int(conid),
                            )
                            gap_stocks.append(gap_stock)
                        except Exception as validation_error:
                            logger.warning(
                                f"Gap stock validation failed for {symbol}: {validation_error}"
                            )
                            continue
                        logger.debug(
                            f"Added gap stock: {symbol} gap={gap_percent:.2f}%"
                        )
                    else:
                        logger.debug(
                            f"Filtered {symbol}: gap={gap_percent:.2f}% < min_gap={min_gap}%"
                        )

                except (KeyError, ValueError, TypeError) as e:
                    logger.warning(
                        f"Invalid scanner result: {result}, error: {e}"
                    )
                    continue

            # Sort by gap percentage descending
            gap_stocks.sort(key=lambda x: x.gap_percent, reverse=True)

            logger.info(f"Found {len(gap_stocks)} gap stocks > {min_gap}%")
            return gap_stocks

        except Exception as e:
            logger.error(f"Error scanning for gaps: {e}")
            return []

    def track_opening_range(
        self,
        candidates: list[GapStock],
        duration_seconds: int = 600,
        poll_interval: int = 30,
    ) -> list[OpeningRangeData]:
        """Track opening range for gap candidates

        Args:
            candidates: List of gap stocks to track
            duration_seconds: Total tracking duration (default 10 minutes)
            poll_interval: Polling interval in seconds (default 30 seconds)

        Returns:
            List of OpeningRangeData objects with tracking results
        """
        if not self._connected or not self.client.is_connected():
            logger.error("Scanner not connected - call connect() first")
            return []

        if not candidates:
            logger.warning("No candidates to track")
            return []

        logger.info(
            f"Tracking opening range for {len(candidates)} candidates for {duration_seconds}s"
        )

        # Initialise tracking data
        tracking_data = {}
        for stock in candidates:
            tracking_data[stock.ticker] = {
                "conid": stock.conid,
                "prev_close": None,  # Will be fetched during tracking
                "high": None,
                "low": None,
                "gap_holding": True,
                "first_price": None,
            }

        start_time = time.time()
        end_time = start_time + duration_seconds

        # Track opening range
        while time.time() < end_time:
            try:
                # Get market data for all candidates
                for stock in candidates:
                    market_data = self.client.get_market_data(str(stock.conid))

                    if market_data:
                        ticker_data = tracking_data[stock.ticker]
                        current_price = market_data.last_price

                        # Fetch previous close if we don't have it yet
                        if (
                            ticker_data["prev_close"] is None
                            and market_data.prior_close
                        ):
                            ticker_data["prev_close"] = market_data.prior_close

                        # Set first price (opening price)
                        if ticker_data["first_price"] is None:
                            ticker_data["first_price"] = current_price
                            ticker_data["high"] = current_price
                            ticker_data["low"] = current_price
                        else:
                            # Update high/low
                            ticker_data["high"] = max(
                                ticker_data["high"] or 0.0, current_price
                            )
                            ticker_data["low"] = min(
                                ticker_data["low"] or float("inf"),
                                current_price,
                            )

                        # Check if gap is still holding (using placeholder logic)
                        # In real implementation, we'd compare with actual previous close
                        if (
                            ticker_data["first_price"]
                            and current_price
                            < ticker_data["first_price"] * 0.95
                        ):
                            ticker_data["gap_holding"] = False
                            logger.warning(
                                f"{stock.ticker} gap failed - price {current_price} significantly below opening {ticker_data['first_price']}"
                            )

                # Sleep until next poll
                time.sleep(poll_interval)

            except Exception as e:
                logger.error(f"Error during opening range tracking: {e}")
                time.sleep(poll_interval)
                continue

        # Compile results
        results = []
        for stock in candidates:
            ticker_data = tracking_data[stock.ticker]

            # Get final market data for current price
            final_market_data = self.client.get_market_data(str(stock.conid))
            current_price = (
                final_market_data.last_price
                if final_market_data
                and final_market_data.last_price is not None
                else float(ticker_data.get("first_price") or 0)
            )

            try:
                or_data = OpeningRangeData(
                    ticker=stock.ticker,
                    conid=stock.conid,
                    or_high=float(ticker_data["high"] or 0),
                    or_low=float(ticker_data["low"] or 0),
                    open_price=float(ticker_data["first_price"] or 0),
                    prev_close=float(ticker_data["prev_close"] or 0),
                    current_price=float(current_price),
                    gap_holding=bool(ticker_data["gap_holding"]),
                )
                results.append(or_data)
            except Exception as validation_error:
                logger.warning(
                    f"Opening range data validation failed for {stock.ticker}: {validation_error}"
                )
                continue

        gap_holding_count = sum(1 for r in results if r.gap_holding)
        logger.info(
            f"Opening range tracking complete: {gap_holding_count}/{len(results)} gaps holding"
        )

        return results

    def filter_breakouts(
        self, or_data: list[OpeningRangeData]
    ) -> list[BreakoutSignal]:
        """Filter for stocks with gap holding and ORH breakout

        Args:
            or_data: List of opening range data to filter

        Returns:
            List of BreakoutSignal objects for valid breakouts
        """
        if not or_data:
            logger.warning("No opening range data to filter")
            return []

        logger.info(
            f"Filtering {len(or_data)} opening range candidates for breakouts"
        )

        breakouts = []
        for data in or_data:
            try:
                # Check gap holding criteria
                if not data.gap_holding:
                    logger.debug(f"{data.ticker} excluded - gap not holding")
                    continue

                # Check ORH breakout criteria
                if data.current_price <= data.or_high:
                    logger.debug(
                        f"{data.ticker} excluded - no ORH breakout (price {data.current_price} <= ORH {data.or_high})"
                    )
                    continue

                # Calculate opening range size as percentage
                if data.or_low > 0:
                    or_size_pct = (
                        (data.or_high - data.or_low) / data.or_low
                    ) * 100
                else:
                    or_size_pct = 0

                # Calculate gap percentage
                if data.prev_close > 0:
                    gap_pct = (
                        (data.open_price - data.prev_close) / data.prev_close
                    ) * 100
                else:
                    gap_pct = 0

                # Create breakout signal
                try:
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
                except Exception as validation_error:
                    logger.warning(
                        f"Breakout signal validation failed for {data.ticker}: {validation_error}"
                    )
                    continue
                logger.info(
                    f"Breakout detected: {data.ticker} @ {data.current_price} (ORH: {data.or_high})"
                )

            except Exception as e:
                logger.error(f"Error filtering {data.ticker}: {e}")
                continue

        logger.info(f"Found {len(breakouts)} valid breakouts")
        return breakouts

    def connect(self, timeout: int = 20) -> None:
        """Connect to IBKR

        Args:
            timeout: Connection timeout in seconds
        """
        try:
            self.client.connect(timeout)
            self._connected = True
            logger.info("IBKR gap scanner connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect IBKR gap scanner: {e}")
            self._connected = False
            raise ConnectionError(
                f"Failed to connect IBKR gap scanner: {e}"
            ) from e

    def disconnect(self) -> None:
        """Disconnect from IBKR"""
        try:
            self.client.disconnect()
            self._connected = False
            logger.info("IBKR gap scanner disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting IBKR gap scanner: {e}")

    def get_market_data(self, conid: str) -> MarketData | None:
        """Get market data for a contract using the underlying client

        Args:
            conid: IBKR contract ID

        Returns:
            MarketData object if successful, None on failure
        """
        if not self._connected or not self.client.is_connected():
            logger.error("Scanner not connected - call connect() first")
            return None

        return self.client.get_market_data(conid)

    def scan_gaps_with_announcements(
        self, price_sensitive_tickers: set[str], db: "Database | None" = None
    ) -> tuple[list[GapStock], list[dict]]:
        """Scan for gaps and filter by price-sensitive announcements

        Args:
            price_sensitive_tickers: Set of tickers with price-sensitive announcements
            db: Database instance for persistence (optional)

        Returns:
            Tuple of (gap_stocks, new_candidates) where:
            - gap_stocks: List of GapStock objects with announcements
            - new_candidates: List of candidate dicts for notifications
        """
        logger.info("Scanning for gaps with announcement filtering...")

        # Scan for gaps
        gap_stocks = self.scan_for_gaps(
            min_gap=self.scanner_config.gap_threshold
        )

        if not gap_stocks:
            logger.info("No gap stocks found in scan")
            return [], []

        filtered_stocks = []
        new_candidates = []

        for stock in gap_stocks:
            # Only process if ticker has price-sensitive announcement
            if str(stock.conid) not in price_sensitive_tickers:
                logger.debug(
                    f"{str(stock.conid)}: Skipped (no price-sensitive announcement)"
                )
                continue

            # Get current price for display and database
            current_price = None
            try:
                market_data = self.get_market_data(str(stock.conid))
                if market_data and market_data.last_price:
                    current_price = float(market_data.last_price)
            except Exception as e:
                logger.debug(
                    f"Could not fetch market data for {str(stock.conid)}: {e}"
                )

            price_display = (
                f"${current_price:.4f}"
                if current_price
                else "Price unavailable"
            )
            logger.info(
                f"{str(stock.conid)}: Gap {stock.gap_percent:.2f}% @ {price_display}"
            )

            # Check if already in database and persist if needed
            existing = None
            if db:
                existing = db.get_candidate(str(stock.conid))

            if not existing or existing.status != "watching":
                # Create candidate for notification
                candidate_dict = {
                    "ticker": str(stock.conid),
                    "gap_percent": stock.gap_percent,
                    "price": current_price,
                }
                new_candidates.append(candidate_dict)

                # Persist to database if provided
                if db:
                    from skim.data.models import Candidate

                    candidate = Candidate(
                        ticker=str(stock.conid),
                        headline=f"Gap detected: {stock.gap_percent:.2f}%",
                        scan_date=datetime.now().isoformat(),
                        status="watching",
                        gap_percent=stock.gap_percent,
                        prev_close=current_price,  # Use current price as fallback
                    )
                    db.save_candidate(candidate)
                    logger.info(
                        f"Added {str(stock.conid)} to candidates (gap: {stock.gap_percent:.2f}%, price-sensitive announcement)"
                    )

            filtered_stocks.append(stock)

        logger.info(
            f"Gap scan with announcements complete. Found {len(filtered_stocks)} gap stocks with announcements"
        )
        return filtered_stocks, new_candidates

    def scan_and_monitor_gaps(
        self,
        existing_candidates: list["Candidate"],
        db: "Database | None" = None,
    ) -> tuple[list[GapStock], int]:
        """Scan for gaps and check against existing candidates for triggering

        Args:
            existing_candidates: List of existing candidates to check against
            db: Database instance for persistence (optional)

        Returns:
            Tuple of (gap_stocks, gaps_triggered) where:
            - gap_stocks: List of GapStock objects
            - gaps_triggered: Number of candidates triggered
        """
        logger.info("Scanning and monitoring gaps for triggering...")

        # Scan for gaps
        gap_stocks = self.scan_for_gaps(
            min_gap=self.scanner_config.gap_threshold
        )

        if not gap_stocks:
            logger.info("No stocks meeting gap threshold")
            return [], 0

        candidate_tickers = {c.ticker for c in existing_candidates}
        gaps_triggered = 0

        for stock in gap_stocks:
            # Get current price for display and database
            current_price = None
            try:
                market_data = self.get_market_data(str(stock.conid))
                if market_data and market_data.last_price:
                    current_price = float(market_data.last_price)
            except Exception as e:
                logger.debug(
                    f"Could not fetch market data for {str(stock.conid)}: {e}"
                )

            price_display = (
                f"${current_price:.4f}"
                if current_price
                else "Price unavailable"
            )
            logger.info(
                f"{str(stock.conid)}: Gap {stock.gap_percent:.2f}% @ {price_display}"
            )

            # Check if this ticker is in our candidates
            if str(stock.conid) in candidate_tickers:
                # Trigger existing candidate
                logger.warning(
                    f"{str(stock.conid)}: CANDIDATE TRIGGERED! Gap: {stock.gap_percent:.2f}%"
                )

                if db:
                    db.update_candidate_status(
                        str(stock.conid), "triggered", stock.gap_percent
                    )
                gaps_triggered += 1
            else:
                # New stock meeting threshold - add directly as triggered
                logger.warning(
                    f"{str(stock.conid)}: NEW STOCK TRIGGERED! Gap: {stock.gap_percent:.2f}%"
                )

                if db:
                    from skim.data.models import Candidate

                    candidate = Candidate(
                        ticker=str(stock.conid),
                        headline=f"Gap triggered: {stock.gap_percent:.2f}%",
                        scan_date=datetime.now().isoformat(),
                        status="triggered",
                        gap_percent=stock.gap_percent,
                        prev_close=current_price,  # Use current price as fallback
                    )
                    db.save_candidate(candidate)
                gaps_triggered += 1

        logger.info(
            f"Gap monitoring complete. Found {gaps_triggered} triggered stocks"
        )
        return gap_stocks, gaps_triggered

    def scan_for_or_tracking(self, db: "Database | None" = None) -> int:
        """Scan for gaps and store candidates with OR tracking status

        Args:
            db: Database instance for persistence (optional)

        Returns:
            Number of new candidates found and stored for OR tracking
        """
        logger.info("Scanning for OR tracking candidates...")

        # Scan for gaps
        gap_stocks = self.scan_for_gaps(
            min_gap=self.scanner_config.gap_threshold
        )

        if not gap_stocks:
            logger.info("No gap stocks found in IBKR scan")
            return 0

        candidates_found = 0

        for stock in gap_stocks:
            # Get current price for display and database
            current_price = None
            try:
                market_data = self.get_market_data(str(stock.conid))
                if market_data and market_data.last_price:
                    current_price = float(market_data.last_price)
            except Exception as e:
                logger.debug(
                    f"Could not fetch market data for {str(stock.conid)}: {e}"
                )

            price_display = (
                f"${current_price:.4f}"
                if current_price
                else "Price unavailable"
            )
            logger.info(
                f"{str(stock.conid)}: Gap {stock.gap_percent:.2f}% @ {price_display}"
            )

            # Check if already exists
            existing = None
            if db:
                existing = db.get_candidate(str(stock.conid))

            if db and (
                not existing
                or existing.status
                not in (
                    "or_tracking",
                    "orh_breakout",
                )
            ):
                # Create candidate with OR tracking status
                from skim.data.models import Candidate

                candidate = Candidate(
                    ticker=str(stock.conid),
                    headline=f"Gap detected: {stock.gap_percent:.2f}%",
                    scan_date=datetime.now().isoformat(),
                    status="or_tracking",
                    gap_percent=stock.gap_percent,
                    prev_close=current_price,  # Use current price as fallback
                    conid=stock.conid,
                    source="ibkr",
                )
                db.save_candidate(candidate)
                candidates_found += 1
                logger.info(
                    f"Added {str(stock.conid)} to OR tracking (gap: {stock.gap_percent:.2f}%)"
                )

        logger.info(
            f"OR tracking scan complete. Found {candidates_found} OR tracking candidates"
        )
        return candidates_found

    def is_connected(self) -> bool:
        """Check if scanner is connected"""
        return self._connected and self.client.is_connected()
