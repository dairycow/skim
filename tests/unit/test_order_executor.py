"""Tests for OrderExecutor strategy class"""

from unittest.mock import Mock

import pytest

from skim.strategy.order_executor import OrderExecutor


class TestOrderExecutor:
    """Test OrderExecutor order execution logic"""

    @pytest.fixture
    def order_executor(self):
        """Create OrderExecutor with mocked dependencies"""
        mock_ib_client = Mock()
        mock_db = Mock()
        return OrderExecutor(mock_ib_client, mock_db), mock_ib_client, mock_db

    def test_execute_entry_success(self, order_executor):
        """Test successful entry order execution"""
        executor, mock_ib_client, mock_db = order_executor

        # Setup candidate
        candidate = Mock(ticker="BHP")

        # Setup market data
        mock_market_data = Mock(last_price=46.80, low=44.50)
        mock_ib_client._get_contract_id.return_value = "8644"
        mock_ib_client.get_market_data.return_value = mock_market_data

        # Setup order result
        mock_order_result = Mock(filled_price=46.75, status="filled")
        mock_ib_client.place_order.return_value = mock_order_result

        # Setup database
        mock_db.create_position.return_value = 1

        # Execute
        result = executor.execute_entry(candidate)

        # Verify
        assert result == 1
        mock_ib_client._get_contract_id.assert_called_once_with("BHP")
        mock_ib_client.get_market_data.assert_called_once_with("8644")
        mock_ib_client.place_order.assert_called_once_with(
            "BHP", "BUY", 106
        )  # 5000/46.80
        mock_db.create_position.assert_called_once()
        mock_db.create_trade.assert_called_once()
        mock_db.update_candidate_status.assert_called_once_with(
            "BHP", "entered"
        )

    def test_execute_entry_no_market_data(self, order_executor):
        """Test entry when market data unavailable"""
        executor, mock_ib_client, mock_db = order_executor

        candidate = Mock(ticker="BHP")
        mock_ib_client._get_contract_id.return_value = "8644"
        mock_ib_client.get_market_data.return_value = None

        result = executor.execute_entry(candidate)

        assert result is None
        mock_db.create_position.assert_not_called()

    def test_execute_entry_invalid_price(self, order_executor):
        """Test entry when price is invalid"""
        executor, mock_ib_client, mock_db = order_executor

        candidate = Mock(ticker="BHP")
        mock_market_data = Mock(last_price=0.0, low=0.0)
        mock_ib_client._get_contract_id.return_value = "8644"
        mock_ib_client.get_market_data.return_value = mock_market_data

        result = executor.execute_entry(candidate)

        assert result is None
        mock_db.create_position.assert_not_called()

    def test_execute_entry_quantity_too_small(self, order_executor):
        """Test entry when calculated quantity is too small"""
        executor, mock_ib_client, mock_db = order_executor

        candidate = Mock(ticker="EXPENSIVE")
        mock_market_data = Mock(last_price=10000.0, low=9000.0)
        mock_ib_client._get_contract_id.return_value = "12345"
        mock_ib_client.get_market_data.return_value = mock_market_data

        result = executor.execute_entry(candidate)

        assert result is None
        mock_db.create_position.assert_not_called()

    def test_execute_entry_order_failed(self, order_executor):
        """Test entry when order placement fails"""
        executor, mock_ib_client, mock_db = order_executor

        candidate = Mock(ticker="BHP")
        mock_market_data = Mock(last_price=46.80, low=44.50)
        mock_ib_client._get_contract_id.return_value = "8644"
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_ib_client.place_order.return_value = None  # Order failed

        result = executor.execute_entry(candidate)

        assert result is None
        mock_db.create_position.assert_not_called()

    def test_execute_entry_with_or_low_stop_loss(self, order_executor):
        """Test entry using OR low for stop loss"""
        executor, mock_ib_client, mock_db = order_executor

        candidate = Mock(ticker="BHP", or_low=44.80)
        mock_market_data = Mock(last_price=46.80, low=44.50)
        mock_ib_client._get_contract_id.return_value = "8644"
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_order_result = Mock(filled_price=46.75, status="filled")
        mock_ib_client.place_order.return_value = mock_order_result
        mock_db.create_position.return_value = 1

        result = executor.execute_entry(candidate, stop_loss_source="or_low")

        assert result == 1
        # Verify stop loss was calculated with or_low
        call_args = mock_db.create_position.call_args
        stop_loss = call_args[1]["stop_loss"]
        assert stop_loss == 44.80  # Should use or_low

    def test_execute_exit_success(self, order_executor):
        """Test successful exit order execution"""
        executor, mock_ib_client, mock_db = order_executor

        position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
        )

        mock_order_result = Mock(filled_price=47.50, status="filled")
        mock_ib_client.place_order.return_value = mock_order_result

        result = executor.execute_exit(
            position, quantity=50, reason="Day 3 half exit"
        )

        assert result == 47.50
        mock_ib_client.place_order.assert_called_once_with("BHP", "SELL", 50)
        mock_db.create_trade.assert_called_once()
        call_args = mock_db.create_trade.call_args
        assert call_args[1]["action"] == "SELL"
        assert call_args[1]["quantity"] == 50
        assert call_args[1]["pnl"] == 125.0  # (47.50 - 45.00) * 50

    def test_execute_exit_order_failed(self, order_executor):
        """Test exit when order placement fails"""
        executor, mock_ib_client, mock_db = order_executor

        position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
        )

        mock_ib_client.place_order.return_value = None

        result = executor.execute_exit(position, quantity=50)

        assert result is None
        mock_db.create_trade.assert_not_called()

    def test_execute_exit_no_fill_price(self, order_executor):
        """Test exit when fill price is not available"""
        executor, mock_ib_client, mock_db = order_executor

        position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
        )

        mock_order_result = Mock(filled_price=None, status="pending")
        mock_ib_client.place_order.return_value = mock_order_result

        result = executor.execute_exit(position, quantity=50)

        assert result is None
        # Trade should not be recorded without fill price
        mock_db.create_trade.assert_not_called()
