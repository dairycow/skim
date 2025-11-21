"""Monitor module - checks positions and identifies stop loss triggers"""

from loguru import logger

from skim.brokers.ibkr_client import IBKRClient
from skim.data.models import Position


class Monitor:
    """Monitors open positions for stop loss triggers"""

    def __init__(self, ib_client: IBKRClient):
        """Initialise monitor

        Args:
            ib_client: IBKR client for fetching market data
        """
        self.ib_client = ib_client

    def get_current_price(self, ticker: str) -> float | None:
        """Get current price for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current last price or None if unavailable
        """
        try:
            conid = self.ib_client._get_contract_id(ticker)
            market_data = self.ib_client.get_market_data(conid)

            if (
                not market_data
                or not market_data.last_price
                or market_data.last_price <= 0
            ):
                return None

            return market_data.last_price

        except Exception as e:
            logger.warning(f"Error fetching price for {ticker}: {e}")
            return None

    def check_stops(self, positions: list[Position]) -> list[Position]:
        """Check which positions have hit stop losses

        Args:
            positions: List of open positions to check

        Returns:
            List of positions where current_price < stop_loss
        """
        stops_hit = []

        for position in positions:
            try:
                current_price = self.get_current_price(position.ticker)

                if current_price is None:
                    logger.debug(
                        f"{position.ticker}: Could not fetch current price"
                    )
                    continue

                # Check if stop is hit (price < stop_loss)
                if current_price < position.stop_loss:
                    logger.warning(
                        f"{position.ticker}: STOP HIT! Price ${current_price:.2f} < Stop ${position.stop_loss:.2f}"
                    )
                    stops_hit.append(position)
                else:
                    logger.debug(
                        f"{position.ticker}: Price ${current_price:.2f} >= Stop ${position.stop_loss:.2f}"
                    )

            except Exception as e:
                logger.error(f"Error checking stop for {position.ticker}: {e}")
                continue

        return stops_hit
