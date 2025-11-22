"""Trader module - executes breakout entries and stop loss exits"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

from skim.data.database import Database
from skim.data.models import Candidate, Position

if TYPE_CHECKING:
    from skim.brokers.protocols import MarketDataProvider, OrderManager


class Trader:
    """Executes trading orders for entries and exits"""

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        order_manager: OrderManager,
        db: Database,
    ):
        """Initialise trader

        Args:
            market_data_provider: Provider for market data
            order_manager: Manager for placing orders
            db: Database for recording positions
        """
        self.market_data_provider = market_data_provider
        self.order_manager = order_manager
        self.db = db

    async def execute_breakouts(self, candidates: list[Candidate]) -> int:
        """Execute breakout entries when price > or_high

        Args:
            candidates: List of candidates to check

        Returns:
            Number of entries executed
        """
        entries = 0

        for candidate in candidates:
            try:
                # Get current market data
                market_data = await self.market_data_provider.get_market_data(
                    candidate.ticker
                )

                if not market_data or not market_data.last_price:
                    logger.warning(f"{candidate.ticker}: No valid market data")
                    continue

                current_price = market_data.last_price

                # Check if price has broken above or_high
                if current_price <= candidate.or_high:
                    logger.debug(
                        f"{candidate.ticker}: Price ${current_price:.2f} not above ORH ${candidate.or_high:.2f}"
                    )
                    continue

                logger.info(
                    f"{candidate.ticker}: ORH breakout detected! ${current_price:.2f} > ${candidate.or_high:.2f}"
                )

                # Calculate quantity based on position value
                position_value = 5000.0  # Fixed position size
                max_position_size = 1000
                quantity = min(
                    int(position_value / current_price),
                    max_position_size,
                )

                if quantity < 1:
                    logger.warning(
                        f"{candidate.ticker}: Calculated quantity too small"
                    )
                    continue

                # Place buy order
                order_result = await self.order_manager.place_order(
                    candidate.ticker, "BUY", quantity
                )

                if not order_result:
                    logger.warning(
                        f"{candidate.ticker}: Order placement failed"
                    )
                    continue

                # Use filled price or current price
                fill_price = (
                    order_result.filled_price
                    if order_result.filled_price
                    else current_price
                )

                logger.info(
                    f"Entry order: BUY {quantity} {candidate.ticker} @ ${fill_price:.2f}"
                )

                # Create position with or_low as stop loss
                self.db.create_position(
                    ticker=candidate.ticker,
                    quantity=quantity,
                    entry_price=fill_price,
                    stop_loss=candidate.or_low,
                    entry_date=datetime.now().isoformat(),
                )

                # Update candidate status
                self.db.update_candidate_status(candidate.ticker, "entered")

                entries += 1

            except Exception as e:
                logger.error(
                    f"Error executing breakout for {candidate.ticker}: {e}"
                )
                continue

        logger.info(f"Executed {entries} breakout entries")
        return entries

    async def execute_stops(self, positions: list[Position]) -> int:
        """Execute stop loss exits when price < stop_loss

        Args:
            positions: List of open positions to check

        Returns:
            Number of stops executed
        """
        stops_executed = 0

        for position in positions:
            try:
                # Get current market data
                market_data = await self.market_data_provider.get_market_data(
                    position.ticker
                )

                if not market_data or not market_data.last_price:
                    logger.warning(f"{position.ticker}: No valid market data")
                    continue

                current_price = market_data.last_price

                # Check if stop loss is hit
                if current_price >= position.stop_loss:
                    logger.debug(
                        f"{position.ticker}: Price ${current_price:.2f} above stop ${position.stop_loss:.2f}"
                    )
                    continue

                logger.warning(
                    f"{position.ticker}: STOP HIT! ${current_price:.2f} < ${position.stop_loss:.2f}"
                )

                # Place sell order for entire position
                order_result = await self.order_manager.place_order(
                    position.ticker, "SELL", position.quantity
                )

                if not order_result:
                    logger.warning(
                        f"{position.ticker}: Stop order placement failed"
                    )
                    continue

                # Use filled price or current price
                fill_price = (
                    order_result.filled_price
                    if order_result.filled_price
                    else current_price
                )

                # Calculate PnL
                pnl = (fill_price - position.entry_price) * position.quantity

                logger.info(
                    f"Stop exit: SELL {position.quantity} {position.ticker} @ ${fill_price:.2f}, PnL: ${pnl:.2f}"
                )

                # Close position
                if position.id:
                    self.db.close_position(
                        position_id=position.id,
                        exit_price=fill_price,
                        exit_date=datetime.now().isoformat(),
                    )

                stops_executed += 1

            except Exception as e:
                logger.error(f"Error executing stop for {position.ticker}: {e}")
                continue

        logger.info(f"Executed {stops_executed} stop loss exits")
        return stops_executed
