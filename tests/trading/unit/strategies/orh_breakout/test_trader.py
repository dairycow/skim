"""Unit tests for Trader using event-driven architecture"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from skim.trading.strategies.orh_breakout.trader import TradeEvent, Trader


@pytest.fixture
def trader():
    """Create Trader with async dependencies."""
    market_data = AsyncMock()
    orders = AsyncMock()
    event_bus = AsyncMock()
    event_bus.publish = AsyncMock()
    return (
        Trader(market_data, orders, event_bus),
        market_data,
        orders,
        event_bus,
    )


@pytest.mark.asyncio
class TestTraderExecuteBreakouts:
    """Tests for execute_breakouts method."""

    async def test_execute_breakouts_places_order_when_price_above_orh(
        self, trader
    ):
        """Should place BUY order when current price exceeds ORH."""
        trader_instance, market_data, orders, event_bus = trader

        candidate = MagicMock()
        candidate.ticker.symbol = "BHP"
        candidate.orh_data = MagicMock()
        candidate.orh_data.or_high = 10.0
        candidate.orh_data.or_low = 9.5
        candidate.gap_percent = 5.0
        candidate.headline = None

        market_data.get_market_data.return_value = MagicMock(last_price=10.5)
        orders.place_order.return_value = MagicMock(filled_price=10.5)

        events = await trader_instance.execute_breakouts([candidate])

        assert len(events) == 1
        assert isinstance(events[0], TradeEvent)
        assert events[0].action == "BUY"
        assert events[0].ticker == "BHP"

        assert orders.place_order.awaited
        event_bus.publish.assert_called_once()

        event = event_bus.publish.call_args[0][0]
        assert event.type.value == "trade_executed"
        assert event.data["trade"]["ticker"] == "BHP"
        assert event.data["trade"]["action"] == "BUY"

    async def test_execute_breakouts_skips_when_price_not_above_orh(
        self, trader
    ):
        """Should skip when current price is below ORH."""
        trader_instance, market_data, orders, event_bus = trader

        candidate = MagicMock()
        candidate.ticker.symbol = "RIO"
        candidate.orh_data = MagicMock()
        candidate.orh_data.or_high = 20.0
        candidate.orh_data.or_low = 19.0

        market_data.get_market_data.return_value = MagicMock(last_price=19.5)

        events = await trader_instance.execute_breakouts([candidate])

        assert len(events) == 0
        orders.place_order.assert_not_awaited()
        event_bus.publish.assert_not_called()

    async def test_execute_breakouts_skips_without_orh_data(self, trader):
        """Should skip when ORH data is missing."""
        trader_instance, market_data, orders, event_bus = trader

        candidate = MagicMock()
        candidate.ticker.symbol = "BHP"
        candidate.orh_data = None

        events = await trader_instance.execute_breakouts([candidate])

        assert len(events) == 0
        market_data.get_market_data.assert_not_awaited()
        orders.place_order.assert_not_awaited()

    async def test_execute_breakouts_handles_order_failure(self, trader):
        """Should handle order placement failures gracefully."""
        trader_instance, market_data, orders, event_bus = trader

        candidate = MagicMock()
        candidate.ticker.symbol = "BHP"
        candidate.orh_data = MagicMock()
        candidate.orh_data.or_high = 10.0
        candidate.orh_data.or_low = 9.5
        candidate.gap_percent = 5.0
        candidate.headline = None

        market_data.get_market_data.return_value = MagicMock(last_price=10.5)
        orders.place_order.return_value = None

        events = await trader_instance.execute_breakouts([candidate])

        assert len(events) == 0
        event_bus.publish.assert_not_called()

    async def test_execute_breakouts_handles_multiple_candidates(self, trader):
        """Should process multiple candidates."""
        trader_instance, market_data, orders, event_bus = trader

        candidate1 = MagicMock()
        candidate1.ticker.symbol = "BHP"
        candidate1.orh_data = MagicMock()
        candidate1.orh_data.or_high = 10.0
        candidate1.orh_data.or_low = 9.5
        candidate1.gap_percent = 5.0
        candidate1.headline = None

        candidate2 = MagicMock()
        candidate2.ticker.symbol = "RIO"
        candidate2.orh_data = MagicMock()
        candidate2.orh_data.or_high = 20.0
        candidate2.orh_data.or_low = 19.5
        candidate2.gap_percent = 4.0
        candidate2.headline = None

        market_data.get_market_data.side_effect = [
            MagicMock(last_price=10.5),
            MagicMock(last_price=20.5),
        ]
        orders.place_order.side_effect = [
            MagicMock(filled_price=10.5),
            MagicMock(filled_price=20.5),
        ]

        events = await trader_instance.execute_breakouts(
            [candidate1, candidate2]
        )

        assert len(events) == 2
        assert orders.place_order.await_count == 2
        assert event_bus.publish.await_count == 2


@pytest.mark.asyncio
class TestTraderExecuteStops:
    """Tests for execute_stops method."""

    async def test_execute_stops_closes_position_when_price_below_stop(
        self, trader
    ):
        """Should place SELL order when current price is below stop loss."""
        trader_instance, market_data, orders, event_bus = trader

        position = MagicMock()
        position.ticker.symbol = "BHP"
        position.quantity = 10
        position.stop_loss.value = 9.5
        position.entry_price.value = 10.0

        market_data.get_market_data.return_value = MagicMock(last_price=9.0)
        orders.place_order.return_value = MagicMock(filled_price=9.0)

        events = await trader_instance.execute_stops([position])

        assert len(events) == 1
        assert isinstance(events[0], TradeEvent)
        assert events[0].action == "SELL"
        assert events[0].ticker == "BHP"
        assert events[0].pnl == -10.0

        orders.place_order.assert_awaited_once_with("BHP", "SELL", 10)
        event_bus.publish.assert_called_once()

        event = event_bus.publish.call_args[0][0]
        assert event.type.value == "stop_hit"
        assert event.data["position"]["ticker"] == "BHP"
        assert event.data["position"]["quantity"] == 10

    async def test_execute_stops_ignores_when_price_above_stop(self, trader):
        """Should skip when current price is above stop loss."""
        trader_instance, market_data, orders, event_bus = trader

        position = MagicMock()
        position.ticker.symbol = "RIO"
        position.quantity = 5
        position.stop_loss.value = 19.0
        position.entry_price.value = 20.0

        market_data.get_market_data.return_value = MagicMock(last_price=19.1)

        events = await trader_instance.execute_stops([position])

        assert len(events) == 0
        orders.place_order.assert_not_awaited()
        event_bus.publish.assert_not_called()

    async def test_execute_stops_handles_multiple_positions(self, trader):
        """Should process multiple positions."""
        trader_instance, market_data, orders, event_bus = trader

        position1 = MagicMock()
        position1.ticker.symbol = "BHP"
        position1.quantity = 10
        position1.stop_loss.value = 9.5
        position1.entry_price.value = 10.0

        position2 = MagicMock()
        position2.ticker.symbol = "RIO"
        position2.quantity = 5
        position2.stop_loss.value = 19.0
        position2.entry_price.value = 20.0

        market_data.get_market_data.side_effect = [
            MagicMock(last_price=9.0),
            MagicMock(last_price=18.9),
        ]
        orders.place_order.side_effect = [
            MagicMock(filled_price=9.0),
            MagicMock(filled_price=18.9),
        ]

        events = await trader_instance.execute_stops([position1, position2])

        assert len(events) == 2
        assert orders.place_order.await_count == 2
        assert event_bus.publish.await_count == 2

    async def test_execute_stops_handles_order_failure(self, trader):
        """Should handle order placement failures gracefully."""
        trader_instance, market_data, orders, event_bus = trader

        position = MagicMock()
        position.ticker.symbol = "BHP"
        position.quantity = 10
        position.stop_loss.value = 9.5
        position.entry_price.value = 10.0

        market_data.get_market_data.return_value = MagicMock(last_price=9.0)
        orders.place_order.return_value = None

        events = await trader_instance.execute_stops([position])

        assert len(events) == 0
        event_bus.publish.assert_not_called()

    async def test_execute_stops_calculates_pnl(self, trader):
        """Should correctly calculate PnL for winning and losing trades."""
        trader_instance, market_data, orders, event_bus = trader

        losing_position1 = MagicMock()
        losing_position1.ticker.symbol = "BHP"
        losing_position1.quantity = 10
        losing_position1.stop_loss.value = 9.5
        losing_position1.entry_price.value = 10.0

        losing_position2 = MagicMock()
        losing_position2.ticker.symbol = "RIO"
        losing_position2.quantity = 5
        losing_position2.stop_loss.value = 19.0
        losing_position2.entry_price.value = 20.0

        market_data.get_market_data.side_effect = [
            MagicMock(last_price=9.0),
            MagicMock(last_price=18.5),
        ]
        orders.place_order.side_effect = [
            MagicMock(filled_price=9.0),
            MagicMock(filled_price=18.5),
        ]

        events = await trader_instance.execute_stops(
            [losing_position1, losing_position2]
        )

        assert len(events) == 2
        assert events[0].pnl == -10.0  # (9.0 - 10.0) * 10
        assert events[1].pnl == -7.5  # (18.5 - 20.0) * 5
