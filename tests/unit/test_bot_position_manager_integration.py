"""Tests for TradingBot integration with strategy/position_manager.py

Tests that TradingBot properly delegates position sizing and limit checking
to the strategy module instead of duplicating logic inline.
"""

from unittest.mock import Mock

from skim.strategy.position_manager import (
    calculate_position_size,
    calculate_stop_loss,
    can_open_new_position,
)


class TestBotPositionManagerIntegration:
    """Test that TradingBot uses position_manager functions"""

    def test_execute_uses_can_open_new_position(self, mock_trading_bot):
        """Test that execute() uses can_open_new_position() to check limits"""
        mock_trading_bot.db.count_open_positions.return_value = 5
        mock_trading_bot.config.max_positions = 5

        result = mock_trading_bot.execute()

        # Should return 0 when at position limit
        assert result == 0
        mock_trading_bot.db.get_triggered_candidates.assert_not_called()

    def test_execute_can_open_position_when_under_limit(self, mock_trading_bot):
        """Test that execute() allows opening when under position limit"""
        mock_trading_bot.db.count_open_positions.return_value = 2
        mock_trading_bot.config.max_positions = 5
        mock_trading_bot.db.get_triggered_candidates.return_value = []

        result = mock_trading_bot.execute()

        # Should proceed to get candidates when under limit
        assert result == 0
        mock_trading_bot.db.get_triggered_candidates.assert_called_once()

    def test_execute_uses_calculate_position_size(self, mock_trading_bot):
        """Test that execute() uses calculate_position_size() for position sizing"""
        mock_candidate = Mock(ticker="BHP")
        mock_trading_bot.db.count_open_positions.return_value = 0
        mock_trading_bot.db.get_triggered_candidates.return_value = [
            mock_candidate
        ]
        mock_trading_bot.config.max_positions = 5

        # Mock market data
        mock_market_data = Mock(last_price=46.80, low=44.50)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=46.75
        )

        # Mock database operations
        mock_trading_bot.db.create_position.return_value = 1
        mock_trading_bot.db.create_trade.return_value = None
        mock_trading_bot.db.update_candidate_status.return_value = None

        mock_trading_bot.execute()

        # Verify order was placed with correct quantity
        # Expected: calculate_position_size(46.80) = min(int(5000/46.80), max_size) = 106
        expected_quantity = calculate_position_size(
            46.80, mock_trading_bot.config.max_position_size
        )
        mock_trading_bot.ib_client.place_order.assert_called_once_with(
            "BHP", "BUY", expected_quantity
        )

    def test_execute_uses_calculate_stop_loss(self, mock_trading_bot):
        """Test that execute() uses calculate_stop_loss() for stop loss calculation"""
        mock_candidate = Mock(ticker="BHP")
        mock_trading_bot.db.count_open_positions.return_value = 0
        mock_trading_bot.db.get_triggered_candidates.return_value = [
            mock_candidate
        ]
        mock_trading_bot.config.max_positions = 5

        # Mock market data with daily low
        mock_market_data = Mock(last_price=46.80, low=44.50)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=46.75
        )

        # Mock database operations
        mock_trading_bot.db.create_position.return_value = 1
        mock_trading_bot.db.create_trade.return_value = None
        mock_trading_bot.db.update_candidate_status.return_value = None

        mock_trading_bot.execute()

        # Verify stop loss was calculated using daily low
        expected_stop_loss = calculate_stop_loss(
            entry_price=46.75, low_of_day=44.50
        )
        mock_trading_bot.db.create_position.assert_called_once()
        call_args = mock_trading_bot.db.create_position.call_args
        actual_stop_loss = call_args[1]["stop_loss"]
        assert actual_stop_loss == expected_stop_loss

    def test_execute_stop_loss_fallback_when_no_daily_low(
        self, mock_trading_bot
    ):
        """Test that stop loss uses percentage fallback when daily low unavailable"""
        mock_candidate = Mock(ticker="BHP")
        mock_trading_bot.db.count_open_positions.return_value = 0
        mock_trading_bot.db.get_triggered_candidates.return_value = [
            mock_candidate
        ]
        mock_trading_bot.config.max_positions = 5

        # Mock market data without daily low
        mock_market_data = Mock(last_price=46.80, low=0.0)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=46.75
        )

        # Mock database operations
        mock_trading_bot.db.create_position.return_value = 1
        mock_trading_bot.db.create_trade.return_value = None
        mock_trading_bot.db.update_candidate_status.return_value = None

        mock_trading_bot.execute()

        # Verify stop loss uses percentage fallback (5% below current_price, not fill_price)
        # Bot uses current_price for stop loss calculation as per current implementation
        expected_stop_loss = calculate_stop_loss(
            entry_price=46.80, low_of_day=None, default_stop_percent=0.05
        )
        mock_trading_bot.db.create_position.assert_called_once()
        call_args = mock_trading_bot.db.create_position.call_args
        actual_stop_loss = call_args[1]["stop_loss"]
        assert abs(actual_stop_loss - expected_stop_loss) < 0.01

    def test_execute_orh_uses_calculate_position_size(self, mock_trading_bot):
        """Test that execute_orh_breakouts() uses calculate_position_size()"""
        mock_candidate = Mock(ticker="BHP", or_low=44.80)
        mock_trading_bot.db.get_orh_breakout_candidates.return_value = [
            mock_candidate
        ]
        mock_trading_bot.db.count_open_positions.return_value = 0

        # Mock market data
        mock_market_data = Mock(last_price=46.80)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=46.75
        )

        # Mock database operations
        mock_trading_bot.db.create_position.return_value = 1
        mock_trading_bot.db.create_trade.return_value = None
        mock_trading_bot.db.update_candidate_status.return_value = None

        mock_trading_bot.execute_orh_breakouts()

        # Verify position size calculation
        expected_quantity = calculate_position_size(
            46.80, mock_trading_bot.config.max_position_size
        )
        mock_trading_bot.ib_client.place_order.assert_called_once_with(
            "BHP", "BUY", expected_quantity
        )

    def test_execute_orh_uses_calculate_stop_loss(self, mock_trading_bot):
        """Test that execute_orh_breakouts() uses calculate_stop_loss() with OR low"""
        mock_candidate = Mock(ticker="BHP", or_low=44.80)
        mock_trading_bot.db.get_orh_breakout_candidates.return_value = [
            mock_candidate
        ]
        mock_trading_bot.db.count_open_positions.return_value = 0

        # Mock market data
        mock_market_data = Mock(last_price=46.80)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=46.75
        )

        # Mock database operations
        mock_trading_bot.db.create_position.return_value = 1
        mock_trading_bot.db.create_trade.return_value = None
        mock_trading_bot.db.update_candidate_status.return_value = None

        mock_trading_bot.execute_orh_breakouts()

        # Verify stop loss uses OR low
        expected_stop_loss = calculate_stop_loss(
            entry_price=46.75, low_of_day=44.80
        )
        mock_trading_bot.db.create_position.assert_called_once()
        call_args = mock_trading_bot.db.create_position.call_args
        actual_stop_loss = call_args[1]["stop_loss"]
        assert actual_stop_loss == expected_stop_loss


class TestPositionManagerFunctions:
    """Test position_manager functions work correctly"""

    def test_can_open_new_position_at_limit(self):
        """Test that can_open_new_position returns False at limit"""
        assert can_open_new_position(5, max_positions=5) is False

    def test_can_open_new_position_under_limit(self):
        """Test that can_open_new_position returns True under limit"""
        assert can_open_new_position(4, max_positions=5) is True

    def test_calculate_position_size_standard(self):
        """Test standard position size calculation"""
        # $5000 / $50 = 100 shares
        assert calculate_position_size(50.0) == 100

    def test_calculate_position_size_respects_max_shares(self):
        """Test that position size respects max_shares limit"""
        # Would be 500 shares, but limited to 100
        assert calculate_position_size(10.0, max_shares=100) == 100

    def test_calculate_position_size_too_expensive(self):
        """Test position size is 0 when price is too high"""
        # $5000 / $10000 = 0.5 shares (rounds to 0)
        assert calculate_position_size(10000.0) == 0

    def test_calculate_stop_loss_uses_daily_low(self):
        """Test that stop loss prefers daily low"""
        # Should use low_of_day=48.0, not 5% fallback
        result = calculate_stop_loss(50.0, low_of_day=48.0)
        assert result == 48.0

    def test_calculate_stop_loss_fallback_percentage(self):
        """Test that stop loss falls back to percentage"""
        # 50.0 * 0.95 = 47.5
        result = calculate_stop_loss(50.0, low_of_day=None)
        assert result == 47.5

    def test_calculate_stop_loss_with_custom_percentage(self):
        """Test stop loss with custom percentage"""
        # 100.0 * 0.90 = 90.0
        result = calculate_stop_loss(
            100.0, low_of_day=None, default_stop_percent=0.10
        )
        assert result == 90.0
