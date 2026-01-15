"""Unit tests for the monitor module using the async market data provider."""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from skim.domain.models import Position
from skim.domain.models.price import Price
from skim.domain.models.ticker import Ticker
from skim.trading.monitor import Monitor


@pytest.fixture
def monitor():
    """Monitor wired with an async market data provider mock."""
    market_data = AsyncMock()
    return Monitor(market_data), market_data


@pytest.mark.asyncio
async def test_get_current_price_returns_last_price(monitor):
    monitor_instance, market_data = monitor
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 10.5}
    )

    price = await monitor_instance.get_current_price("BHP")

    assert price == 10.5
    market_data.get_market_data.assert_awaited_once_with("BHP")


@pytest.mark.asyncio
@pytest.mark.parametrize("response", [None, type("MD", (), {"last_price": 0})])
async def test_get_current_price_handles_missing_or_zero(monitor, response):
    monitor_instance, market_data = monitor
    market_data.get_market_data.return_value = response

    price = await monitor_instance.get_current_price("RIO")

    assert price is None


@pytest.mark.asyncio
async def test_check_stops_flags_positions_below_stop(monitor):
    monitor_instance, market_data = monitor
    positions = [
        Position(
            ticker=Ticker(symbol="BHP"),
            quantity=10,
            entry_price=Price(value=11.0, timestamp=datetime(2024, 1, 1)),
            stop_loss=Price(value=10.0, timestamp=datetime(2024, 1, 1)),
            entry_date=datetime(2024, 1, 1),
            status="open",
            id=1,
        )
    ]
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 9.9}
    )

    result = await monitor_instance.check_stops(positions)

    assert [p.ticker.symbol for p in result] == ["BHP"]
    market_data.get_market_data.assert_awaited_once_with("BHP")


@pytest.mark.asyncio
async def test_check_stops_ignores_positions_above_stop(monitor):
    monitor_instance, market_data = monitor
    positions = [
        Position(
            ticker=Ticker(symbol="RIO"),
            quantity=5,
            entry_price=Price(value=100.0, timestamp=datetime(2024, 1, 1)),
            stop_loss=Price(value=95.0, timestamp=datetime(2024, 1, 1)),
            entry_date=datetime(2024, 1, 1),
            status="open",
            id=2,
        )
    ]
    market_data.get_market_data.return_value = type(
        "MarketData", (), {"last_price": 96.0}
    )

    result = await monitor_instance.check_stops(positions)

    assert result == []
