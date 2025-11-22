"""Unit tests for Trader using async provider and order manager."""

from unittest.mock import AsyncMock, Mock

import pytest

from skim.data.models import Candidate, Position
from skim.trader import Trader


@pytest.fixture
def trader():
    """Create Trader with async dependencies."""
    market_data = AsyncMock()
    orders = AsyncMock()
    db = Mock()
    return Trader(market_data, orders, db), market_data, orders, db


@pytest.mark.asyncio
async def test_execute_breakouts_places_order_when_price_above_orh(trader):
    trader_instance, market_data, orders, db = trader
    candidate = Candidate(
        ticker="BHP",
        or_high=10.0,
        or_low=9.5,
        scan_date="2024-01-01",
        status="watching",
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 10.5}
    )
    orders.place_order.return_value = type(
        "OrderResult", (), {"filled_price": 10.5}
    )

    executed = await trader_instance.execute_breakouts([candidate])

    assert executed == 1
    orders.place_order.assert_awaited_once()
    db.create_position.assert_called_once()
    db.update_candidate_status.assert_called_once_with("BHP", "entered")


@pytest.mark.asyncio
async def test_execute_breakouts_skips_when_price_not_above_orh(trader):
    trader_instance, market_data, orders, db = trader
    candidate = Candidate(
        ticker="RIO",
        or_high=20.0,
        or_low=19.0,
        scan_date="2024-01-01",
        status="watching",
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 19.5}
    )

    executed = await trader_instance.execute_breakouts([candidate])

    assert executed == 0
    orders.place_order.assert_not_awaited()
    db.create_position.assert_not_called()


@pytest.mark.asyncio
async def test_execute_stops_closes_position_when_price_below_stop(trader):
    trader_instance, market_data, orders, db = trader
    position = Position(
        ticker="BHP",
        quantity=10,
        entry_price=10.0,
        stop_loss=9.5,
        entry_date="2024-01-01",
        status="open",
        id=7,
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 9.0}
    )
    orders.place_order.return_value = type(
        "OrderResult", (), {"filled_price": 9.0}
    )

    executed = await trader_instance.execute_stops([position])

    assert executed == 1
    orders.place_order.assert_awaited_once_with("BHP", "SELL", 10)
    db.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_execute_stops_ignores_when_price_above_stop(trader):
    trader_instance, market_data, orders, db = trader
    position = Position(
        ticker="RIO",
        quantity=5,
        entry_price=20.0,
        stop_loss=19.0,
        entry_date="2024-01-01",
        status="open",
        id=3,
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 19.1}
    )

    executed = await trader_instance.execute_stops([position])

    assert executed == 0
    orders.place_order.assert_not_awaited()
    db.close_position.assert_not_called()
