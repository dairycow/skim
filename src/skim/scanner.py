"""Scanner module - finds candidates with gap + announcement + opening range data"""

from datetime import datetime

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient
from skim.data.models import Candidate
from skim.scanners.asx_announcements import ASXAnnouncementScanner
from skim.scanners.ibkr_gap_scanner import IBKRGapScanner


class Scanner:
    """Scans market for trading candidates"""

    def __init__(self, paper_trading: bool = True, gap_threshold: float = 3.0):
        """Initialise scanner

        Args:
            paper_trading: Whether to use paper trading
            gap_threshold: Minimum gap percentage to consider
        """
        self.gap_threshold = gap_threshold
        self.paper_trading = paper_trading

        # Initialize clients
        self.ib_client = IBKRClient(paper_trading=paper_trading)
        self.gap_scanner = IBKRGapScanner(paper_trading=paper_trading)
        self.asx_scanner = ASXAnnouncementScanner()

    def find_candidates(self) -> list[Candidate]:
        """Find candidates with gap + announcement + opening range data

        Workflow:
        1. Get gaps from IBKR
        2. Filter by price-sensitive announcements
        3. Get market data for opening range
        4. Return candidates

        Returns:
            List of Candidate objects with or_high, or_low set
        """
        candidates = []

        try:
            # Fetch price-sensitive announcements first
            logger.info("Fetching price-sensitive announcements...")
            price_sensitive_tickers = (
                self.asx_scanner.fetch_price_sensitive_tickers()
            )

            if not price_sensitive_tickers:
                logger.warning("No price-sensitive announcements found")
                return []

            logger.info(
                f"Found {len(price_sensitive_tickers)} stocks with announcements"
            )

            # Connect to IBKR if needed
            if not self.ib_client.is_connected():
                logger.info("Connecting to IBKR...")
                self.ib_client.connect(timeout=20)

            # Connect gap scanner if needed
            if not self.gap_scanner.is_connected():
                logger.info("Connecting gap scanner to IBKR...")
                self.gap_scanner.connect()

            # Scan for gaps
            logger.info(
                f"Scanning for gaps (threshold >= {self.gap_threshold}%)..."
            )
            gap_stocks = self.gap_scanner.scan_for_gaps(
                min_gap=self.gap_threshold
            )

            if not gap_stocks:
                logger.warning("No gaps found")
                return []

            logger.info(f"Found {len(gap_stocks)} stocks with gaps")

            # Filter by announcement + get market data
            for gap_stock in gap_stocks:
                # Skip if gap is below threshold
                if gap_stock.gap_percent < self.gap_threshold:
                    logger.debug(
                        f"Skipping {gap_stock.ticker} - gap {gap_stock.gap_percent:.2f}% below threshold {self.gap_threshold}%"
                    )
                    continue

                if gap_stock.ticker not in price_sensitive_tickers:
                    logger.debug(
                        f"Skipping {gap_stock.ticker} - no announcement"
                    )
                    continue

                # Skip negative gaps
                if gap_stock.gap_percent <= 0:
                    logger.debug(f"Skipping {gap_stock.ticker} - negative gap")
                    continue

                # Skip negative gaps
                if gap_stock.gap_percent <= 0:
                    logger.debug(f"Skipping {gap_stock.ticker} - negative gap")
                    continue

                try:
                    # Get market data for opening range
                    logger.debug(
                        f"Fetching market data for {gap_stock.ticker}..."
                    )
                    market_data = self.gap_scanner.get_market_data(
                        str(gap_stock.conid)
                    )

                    if not market_data:
                        logger.warning(
                            f"Could not fetch market data for {gap_stock.ticker}"
                        )
                        continue

                    # Create candidate with opening range data
                    candidate = Candidate(
                        ticker=gap_stock.ticker,
                        or_high=market_data.high,
                        or_low=market_data.low,
                        scan_date=datetime.now().isoformat(),
                        status="watching",
                    )

                    candidates.append(candidate)
                    logger.info(
                        f"Added candidate: {gap_stock.ticker} (gap: {gap_stock.gap_percent:.2f}%, ORH: ${market_data.high:.2f}, ORL: ${market_data.low:.2f})"
                    )

                except Exception as e:
                    logger.error(f"Error processing {gap_stock.ticker}: {e}")
                    continue

            logger.info(f"Scan complete. Found {len(candidates)} candidates")
            return candidates

        except Exception as e:
            logger.error(f"Error during scan: {e}")
            return []
