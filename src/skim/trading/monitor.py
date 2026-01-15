"""Monitor module - checks positions and identifies stop loss triggers"""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from skim.trading.data.models import Position

if TYPE_CHECKING:
    from skim.infrastructure.brokers.protocols import MarketDataProvider


class Monitor:
    """Monitors open positions for stop loss triggers"""

    def __init__(self, market_data_provider: MarketDataProvider):
        """Initialise monitor

        Args:
            market_data_provider: Provider for market data
        """
        self.market_data_provider = market_data_provider

    async def get_current_price(self, ticker: str) -> float | None:
        """Get current price for a ticker

        Args:
            ticker: Stock ticker symbol

        Returns:
            Current last price or None if unavailable
        """
        try:
            result = await self.market_data_provider.get_market_data(ticker)
            if result is None or isinstance(result, dict):
                return None

            if not result or not result.last_price or result.last_price <= 0:
                return None

            return result.last_price

        except Exception as e:
            logger.warning(f"Error fetching price for {ticker}: {e}")
            return None

    async def check_stops(self, positions: list[Position]) -> list[Position]:
        """Check which positions have hit stop losses

        Args:
            positions: List of open positions to check

        Returns:
            List of positions where current_price < stop_loss
        """
        stops_hit = []

        for position in positions:
            try:
                current_price = await self.get_current_price(position.ticker)

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
