"""Tests for OrderExecutor strategy class using async services"""

from unittest.mock import AsyncMock, Mock

import pytest

from skim.strategy.order_executor import OrderExecutor


@pytest.fixture
def order_executor():
    """Create OrderExecutor with mocked async dependencies."""
    mock_orders = AsyncMock()
    mock_market_data = AsyncMock()
    mock_db = Mock()
    executor = OrderExecutor(mock_orders, mock_market_data, mock_db)
    return executor, mock_orders, mock_market_data, mock_db


@pytest.mark.asyncio
class TestOrderExecutor:
    """Test OrderExecutor order execution logic."""

    async def test_execute_entry_success(self, order_executor):
        """Entry execution should place order and persist position."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        candidate = Mock(ticker="BHP", or_low=44.80)
        mock_market_data.get_market_data.return_value = Mock(
            last_price=46.80, low=44.50
        )
        mock_orders.place_order.return_value = Mock(
            filled_price=46.75, status="filled"
        )
        mock_db.create_position.return_value = 1

        result = await executor.execute_entry(
            candidate, stop_loss_source="or_low"
        )

        mock_market_data.get_market_data.assert_awaited_once_with("BHP")
        mock_orders.place_order.assert_awaited_once_with("BHP", "BUY", 106)
        mock_db.create_position.assert_called_once()
        mock_db.create_trade.assert_called_once()
        mock_db.update_candidate_status.assert_called_once_with(
            "BHP", "entered"
        )
        assert result == 1

    async def test_execute_entry_no_market_data(self, order_executor):
        """Entry should abort when market data is unavailable."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        candidate = Mock(ticker="BHP")
        mock_market_data.get_market_data.return_value = None

        result = await executor.execute_entry(candidate)

        assert result is None
        mock_orders.place_order.assert_not_awaited()
        mock_db.create_position.assert_not_called()

    async def test_execute_entry_invalid_price(self, order_executor):
        """Entry should abort when price is invalid."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        candidate = Mock(ticker="BHP")
        mock_market_data.get_market_data.return_value = Mock(
            last_price=0.0, low=0.0
        )

        result = await executor.execute_entry(candidate)

        assert result is None
        mock_orders.place_order.assert_not_awaited()
        mock_db.create_position.assert_not_called()

    async def test_execute_entry_quantity_too_small(self, order_executor):
        """Entry should abort when calculated quantity is below 1."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        candidate = Mock(ticker="EXPENSIVE")
        mock_market_data.get_market_data.return_value = Mock(
            last_price=10000.0, low=9000.0
        )

        result = await executor.execute_entry(candidate)

        assert result is None
        mock_orders.place_order.assert_not_awaited()
        mock_db.create_position.assert_not_called()

    async def test_execute_entry_order_failed(self, order_executor):
        """Entry should abort when order placement fails."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        candidate = Mock(ticker="BHP")
        mock_market_data.get_market_data.return_value = Mock(
            last_price=46.80, low=44.50
        )
        mock_orders.place_order.return_value = None

        result = await executor.execute_entry(candidate)

        assert result is None
        mock_db.create_position.assert_not_called()

    async def test_execute_exit_success(self, order_executor):
        """Exit execution should place sell order and record trade."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
        )
        mock_orders.place_order.return_value = Mock(
            filled_price=47.50, status="filled"
        )

        result = await executor.execute_exit(
            position, quantity=50, reason="Day 3 half exit"
        )

        mock_orders.place_order.assert_awaited_once_with("BHP", "SELL", 50)
        mock_db.create_trade.assert_called_once()
        call_args = mock_db.create_trade.call_args
        assert call_args[1]["action"] == "SELL"
        assert call_args[1]["quantity"] == 50
        assert call_args[1]["pnl"] == 125.0
        assert result == 47.50

    async def test_execute_exit_order_failed(self, order_executor):
        """Exit should abort when order placement fails."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
        )
        mock_orders.place_order.return_value = None

        result = await executor.execute_exit(position, quantity=50)

        assert result is None
        mock_db.create_trade.assert_not_called()

    async def test_execute_exit_no_fill_price(self, order_executor):
        """Exit should not record trade without a fill price."""
        executor, mock_orders, mock_market_data, mock_db = order_executor

        position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
        )
        mock_orders.place_order.return_value = Mock(
            filled_price=None, status="pending"
        )

        result = await executor.execute_exit(position, quantity=50)

        assert result is None
        mock_db.create_trade.assert_not_called()
