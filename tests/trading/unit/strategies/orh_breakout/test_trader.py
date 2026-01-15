"""Unit tests for Trader using async provider and order manager."""

from unittest.mock import AsyncMock, Mock

import pytest

from skim.trading.strategies.orh_breakout import TradeEvent, Trader


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
    from tests.factories import CandidateFactory

    candidate = CandidateFactory.gap_candidate(
        ticker="BHP",
        gap_percent=5.0,
        conid=8644,
    )
    # Set up ORH data on the candidate
    from skim.domain.models.orh_candidate import ORHCandidateData

    candidate.orh_data = ORHCandidateData(
        gap_percent=5.0,
        conid=8644,
        or_high=10.0,
        or_low=9.5,
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 10.5}
    )
    orders.place_order.return_value = type(
        "OrderResult", (), {"filled_price": 10.5}
    )

    events = await trader_instance.execute_breakouts([candidate])

    assert len(events) == 1
    assert isinstance(events[0], TradeEvent)
    orders.place_order.assert_awaited_once()
    db.create_position.assert_called_once()
    db.update_candidate_status.assert_called_once_with("BHP", "entered")


@pytest.mark.asyncio
async def test_execute_breakouts_skips_when_price_not_above_orh(trader):
    trader_instance, market_data, orders, db = trader
    from skim.domain.models.orh_candidate import ORHCandidateData
    from tests.factories import CandidateFactory

    candidate = CandidateFactory.gap_candidate(
        ticker="RIO",
        gap_percent=4.0,
        conid=8645,
    )
    candidate.orh_data = ORHCandidateData(
        gap_percent=4.0,
        conid=8645,
        or_high=20.0,
        or_low=19.0,
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 19.5}
    )

    events = await trader_instance.execute_breakouts([candidate])

    assert len(events) == 0
    orders.place_order.assert_not_awaited()
    db.create_position.assert_not_called()


@pytest.mark.asyncio
async def test_execute_stops_closes_position_when_price_below_stop(trader):
    trader_instance, market_data, orders, db = trader
    from tests.factories import PositionFactory

    position = PositionFactory.position(
        ticker="BHP",
        quantity=10,
        entry_price=10.0,
        stop_loss=9.5,
        id=7,
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 9.0}
    )
    orders.place_order.return_value = type(
        "OrderResult", (), {"filled_price": 9.0}
    )

    events = await trader_instance.execute_stops([position])

    assert len(events) == 1
    assert isinstance(events[0], TradeEvent)
    orders.place_order.assert_awaited_once_with("BHP", "SELL", 10)
    db.close_position.assert_called_once()


@pytest.mark.asyncio
async def test_execute_stops_ignores_when_price_above_stop(trader):
    trader_instance, market_data, orders, db = trader
    from tests.factories import PositionFactory

    position = PositionFactory.position(
        ticker="RIO",
        quantity=5,
        entry_price=20.0,
        stop_loss=19.0,
        id=3,
    )
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 19.1}
    )

    events = await trader_instance.execute_stops([position])

    assert len(events) == 0
    orders.place_order.assert_not_awaited()
    db.close_position.assert_not_called()
