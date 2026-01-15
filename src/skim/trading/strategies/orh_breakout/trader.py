"""Trader module - executes breakout entries and stop loss exits"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger

from skim.domain.models import Candidate, Position
from skim.domain.models.event import Event, EventType

if TYPE_CHECKING:
    from skim.application.events.event_bus import EventBus
    from skim.infrastructure.brokers.protocols import (
        MarketDataProvider,
        OrderManager,
    )


@dataclass
class TradeEvent:
    """Trade execution summary."""

    action: str
    ticker: str
    quantity: int
    price: float
    pnl: float | None = None


class Trader:
    """Executes trading orders for entries and exits"""

    def __init__(
        self,
        market_data_provider: MarketDataProvider,
        order_manager: OrderManager,
        event_bus: EventBus,
    ):
        """Initialise trader

        Args:
            market_data_provider: Provider for market data
            order_manager: Manager for placing orders
            event_bus: EventBus for publishing trade events
        """
        self.market_data_provider = market_data_provider
        self.order_manager = order_manager
        self.event_bus = event_bus

    async def execute_breakouts(
        self, candidates: list[Candidate]
    ) -> list[TradeEvent]:
        """Execute breakout entries when price > or_high

        Args:
            candidates: List of candidates to check

        Returns:
            List of trade events executed
        """

        events: list[TradeEvent] = []

        for candidate in candidates:
            try:
                if (
                    candidate.orh_data is None
                    or candidate.orh_data.or_high is None
                ):
                    logger.debug(f"{candidate.ticker.symbol}: No ORH data")
                    continue

                or_high = candidate.orh_data.or_high
                or_low = candidate.orh_data.or_low

                result = await self.market_data_provider.get_market_data(
                    candidate.ticker.symbol
                )
                if result is None or isinstance(result, dict):
                    logger.warning(
                        f"{candidate.ticker.symbol}: No valid market data"
                    )
                    continue

                if not result or not result.last_price:
                    logger.warning(
                        f"{candidate.ticker.symbol}: No valid market data"
                    )
                    continue

                current_price = result.last_price

                if current_price <= or_high:
                    logger.debug(
                        f"{candidate.ticker.symbol}: Price ${current_price:.2f} not above ORH ${or_high:.2f}"
                    )
                    continue

                logger.info(
                    f"{candidate.ticker.symbol}: ORH breakout detected! ${current_price:.2f} > ${or_high:.2f}"
                )

                position_value = 5000.0
                max_position_size = 1000
                quantity = min(
                    int(position_value / current_price),
                    max_position_size,
                )

                if quantity < 1:
                    logger.warning(
                        f"{candidate.ticker.symbol}: Calculated quantity too small"
                    )
                    continue

                order_result = await self.order_manager.place_order(
                    candidate.ticker.symbol, "BUY", quantity
                )

                if not order_result:
                    logger.warning(
                        f"{candidate.ticker.symbol}: Order placement failed"
                    )
                    continue

                fill_price = (
                    order_result.filled_price
                    if order_result.filled_price
                    else current_price
                )

                logger.info(
                    f"Entry order: BUY {quantity} {candidate.ticker.symbol} @ ${fill_price:.2f}"
                )

                events.append(
                    TradeEvent(
                        action="BUY",
                        ticker=candidate.ticker.symbol,
                        quantity=quantity,
                        price=fill_price,
                        pnl=None,
                    )
                )

                await self.event_bus.publish(
                    Event(
                        type=EventType.TRADE_EXECUTED,
                        data={
                            "trade": {
                                "action": "BUY",
                                "ticker": candidate.ticker.symbol,
                                "quantity": quantity,
                                "price": fill_price,
                                "stop_loss": or_low
                                if or_low
                                else fill_price * 0.95,
                            },
                            "candidate": {
                                "ticker": candidate.ticker.symbol,
                                "gap_percent": getattr(
                                    candidate, "gap_percent", None
                                ),
                                "headline": getattr(
                                    candidate, "headline", None
                                ),
                            },
                        },
                    )
                )

            except Exception as e:
                logger.error(
                    f"Error executing breakout for {candidate.ticker.symbol}: {e}"
                )
                continue

        logger.info(f"Executed {len(events)} breakout entries")
        return events

    async def execute_stops(
        self, positions: list[Position]
    ) -> list[TradeEvent]:
        """Execute stop loss exits when price < stop_loss

        Args:
            positions: List of open positions to check

        Returns:
            List of stop exit events executed
        """
        events: list[TradeEvent] = []

        for position in positions:
            try:
                result = await self.market_data_provider.get_market_data(
                    position.ticker.symbol
                )
                if result is None or isinstance(result, dict):
                    logger.warning(
                        f"{position.ticker.symbol}: No valid market data"
                    )
                    continue

                if not result or not result.last_price:
                    logger.warning(
                        f"{position.ticker.symbol}: No valid market data"
                    )
                    continue

                current_price = result.last_price
                stop_loss = position.stop_loss.value

                if current_price >= stop_loss:
                    logger.debug(
                        f"{position.ticker.symbol}: Price ${current_price:.2f} above stop ${stop_loss:.2f}"
                    )
                    continue

                logger.warning(
                    f"{position.ticker.symbol}: STOP HIT! ${current_price:.2f} < ${stop_loss:.2f}"
                )

                order_result = await self.order_manager.place_order(
                    position.ticker.symbol, "SELL", position.quantity
                )

                if not order_result:
                    logger.warning(
                        f"{position.ticker.symbol}: Stop order placement failed"
                    )
                    continue

                fill_price = (
                    order_result.filled_price
                    if order_result.filled_price
                    else current_price
                )

                pnl = (
                    fill_price - position.entry_price.value
                ) * position.quantity

                logger.info(
                    f"Stop exit: SELL {position.quantity} {position.ticker.symbol} @ ${fill_price:.2f}, PnL: ${pnl:.2f}"
                )

                events.append(
                    TradeEvent(
                        action="SELL",
                        ticker=position.ticker.symbol,
                        quantity=position.quantity,
                        price=fill_price,
                        pnl=pnl,
                    )
                )

                await self.event_bus.publish(
                    Event(
                        type=EventType.STOP_HIT,
                        data={
                            "position": {
                                "ticker": position.ticker.symbol,
                                "quantity": position.quantity,
                                "entry_price": float(
                                    position.entry_price.value
                                ),
                                "exit_price": fill_price,
                                "pnl": pnl,
                            }
                        },
                    )
                )

            except Exception as e:
                logger.error(
                    f"Error executing stop for {position.ticker.symbol}: {e}"
                )
                continue

        logger.info(f"Executed {len(events)} stop loss exits")
        return events
