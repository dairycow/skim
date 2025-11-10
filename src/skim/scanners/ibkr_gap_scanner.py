"""IBKR Gap Scanner for ASX stocks with opening range breakout detection

This module implements a gap scanner using IBKR's market scanner API
and real-time market data to identify opening range breakouts.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient


class GapStock(NamedTuple):
    """Stock with gap data from IBKR scanner"""

    ticker: str
    gap_percent: float
    close_price: float
    conid: int


@dataclass
class OpeningRangeData:
    """Opening range tracking data for a gap stock"""

    ticker: str
    conid: int
    or_high: float
    or_low: float
    open_price: float
    prev_close: float
    current_price: float
    gap_holding: bool


@dataclass
class BreakoutSignal:
    """Breakout signal for gap stock holding and ORH breakout"""

    ticker: str
    conid: int
    gap_pct: float
    or_high: float
    or_low: float
    or_size_pct: float
    current_price: float
    entry_signal: str  # "ORB_HIGH_BREAKOUT"
    timestamp: datetime


class IBKRGapScanner:
    """Scanner for ASX gap stocks using IBKR API with opening range breakout detection"""

    def __init__(self, paper_trading: bool = True):
        """Initialize IBKR gap scanner

        Args:
            paper_trading: If True, connect to paper trading account
        """
        self.client = IBKRClient(paper_trading=paper_trading)
        self._connected = False

    def _create_gap_scan_params(self, min_gap: float) -> dict:
        """Create scanner parameters to find ASX gap stocks

        Args:
            min_gap: Minimum gap percentage to filter

        Returns:
            Scanner parameters dictionary for IBKR API
        """
        return {
            "instrument": "STK",
            "type": "TOP_PERC_GAIN",
            "location": "STK.HK.ASX",
            "filter": [
                {
                    "code": "priceAbove",
                    "value": 1,
                },
                {
                    "code": "volumeAbove",
                    "value": 50000,
                },
            ],
        }

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
                    today_open = result.get("today_open", 0.0)
                    previous_close = result.get("previous_close", 0.0)

                    # Validate required data
                    if not symbol or not conid:
                        logger.debug(
                            f"Skipping result with missing symbol/conid: {result}"
                        )
                        continue

                    if previous_close <= 0:
                        logger.debug(
                            f"Skipping {symbol} with invalid previous close: {previous_close}"
                        )
                        continue

                    # Calculate actual gap percentage from open vs previous close
                    actual_gap_pct = (
                        (today_open - previous_close) / previous_close
                    ) * 100

                    # Filter by minimum gap requirement
                    if actual_gap_pct >= min_gap:
                        gap_stock = GapStock(
                            ticker=str(symbol),
                            gap_percent=float(actual_gap_pct),
                            close_price=float(previous_close),
                            conid=int(conid),
                        )
                        gap_stocks.append(gap_stock)
                        logger.debug(
                            f"Added gap stock: {symbol} gap={actual_gap_pct:.2f}% "
                            f"(open={today_open}, prev_close={previous_close})"
                        )
                    else:
                        logger.debug(
                            f"Filtered {symbol}: gap={actual_gap_pct:.2f}% < min_gap={min_gap}%"
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

        # Initialize tracking data
        tracking_data = {}
        for stock in candidates:
            tracking_data[stock.ticker] = {
                "conid": stock.conid,
                "prev_close": stock.close_price,
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
                    market_data = self.client.get_market_data(stock.ticker)

                    if market_data:
                        ticker_data = tracking_data[stock.ticker]
                        current_price = market_data.last_price

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

                        # Check if gap is still holding
                        prev_close = ticker_data["prev_close"]
                        if (
                            prev_close is not None
                            and current_price < prev_close
                        ):
                            ticker_data["gap_holding"] = False
                            logger.warning(
                                f"{stock.ticker} gap failed - price {current_price} < prev_close {ticker_data['prev_close']}"
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
            final_market_data = self.client.get_market_data(stock.ticker)
            current_price = (
                final_market_data.last_price
                if final_market_data
                and final_market_data.last_price is not None
                else float(ticker_data.get("first_price") or 0)
            )

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
                    f"Breakout detected: {data.ticker} @ {data.current_price} (ORH: {data.or_high})"
                )

            except Exception as e:
                logger.error(f"Error filtering {data.ticker}: {e}")
                continue

        logger.info(f"Found {len(breakouts)} valid breakouts")
        return breakouts

    def connect(
        self, host: str = "", port: int = 0, client_id: int = 0
    ) -> None:
        """Connect to IBKR

        Args:
            host: Ignored (OAuth uses api.ibkr.com)
            port: Ignored (OAuth uses HTTPS)
            client_id: Ignored (OAuth uses consumer key)
        """
        try:
            self.client.connect(host, port, client_id)
            self._connected = True
            logger.info("IBKR gap scanner connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect IBKR gap scanner: {e}")
            self._connected = False
            raise

    def disconnect(self) -> None:
        """Disconnect from IBKR"""
        try:
            self.client.disconnect()
            self._connected = False
            logger.info("IBKR gap scanner disconnected")
        except Exception as e:
            logger.error(f"Error disconnecting IBKR gap scanner: {e}")

    def is_connected(self) -> bool:
        """Check if scanner is connected"""
        return self._connected and self.client.is_connected()
