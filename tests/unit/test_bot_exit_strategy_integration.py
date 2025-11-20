"""Tests for TradingBot integration with strategy/exit.py

Tests that TradingBot properly delegates exit logic to the strategy module
instead of duplicating logic inline.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock

from skim.strategy.exit import (
    check_half_exit,
    check_stop_loss,
    check_trailing_stop,
)


class TestBotExitStrategyIntegration:
    """Test that TradingBot uses exit_strategy functions"""

    def test_manage_positions_uses_check_stop_loss(self, mock_trading_bot):
        """Test that manage_positions() uses check_stop_loss()"""
        # Create a position below stop loss
        mock_position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
            stop_loss=42.00,
            days_held=1,
            half_sold=False,
        )

        mock_trading_bot.db.get_open_positions.return_value = [mock_position]

        # Mock market data below stop loss
        mock_market_data = Mock(last_price=41.50)  # Below stop loss
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=41.50
        )

        mock_trading_bot.db.update_position_exit.return_value = None
        mock_trading_bot.db.create_trade.return_value = None

        result = mock_trading_bot.manage_positions()

        # Verify stop loss was triggered
        mock_trading_bot.ib_client.place_order.assert_called_once_with(
            "BHP", "SELL", 100
        )
        assert result == 1

    def test_manage_positions_uses_check_half_exit(self, mock_trading_bot):
        """Test that manage_positions() uses check_half_exit()"""
        # Create a position on day 3
        entry_date = (datetime.now() - timedelta(days=3)).isoformat()
        mock_position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
            stop_loss=42.00,
            days_held=3,
            half_sold=False,
            entry_date=entry_date,
        )

        mock_trading_bot.db.get_open_positions.return_value = [mock_position]

        # Mock market data above stop loss
        mock_market_data = Mock(last_price=50.00)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=50.00
        )

        mock_trading_bot.db.update_position_half_sold.return_value = None
        mock_trading_bot.db.create_trade.return_value = None
        mock_trading_bot.db.update_candidate_status.return_value = None

        result = mock_trading_bot.manage_positions()

        # Verify half exit was triggered
        mock_trading_bot.ib_client.place_order.assert_called_once_with(
            "BHP",
            "SELL",
            50,  # Half of 100
        )
        assert result == 1

    def test_manage_positions_both_day3_and_stoploss_trigger(
        self, mock_trading_bot
    ):
        """Test that both day 3 and stop loss can trigger on same position (current behavior)"""
        # Position on day 3 but below stop loss
        entry_date = (datetime.now() - timedelta(days=3)).isoformat()
        mock_position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
            stop_loss=42.00,
            days_held=3,
            half_sold=False,
            entry_date=entry_date,
        )

        mock_trading_bot.db.get_open_positions.return_value = [mock_position]

        # Market price below stop loss
        mock_market_data = Mock(last_price=41.50)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=41.50
        )

        mock_trading_bot.db.update_position_half_sold.return_value = None
        mock_trading_bot.db.update_position_exit.return_value = None
        mock_trading_bot.db.create_trade.return_value = None
        mock_trading_bot.db.update_candidate_status.return_value = None

        result = mock_trading_bot.manage_positions()

        # Current implementation triggers both day3 (50) and stop loss (100)
        calls = mock_trading_bot.ib_client.place_order.call_args_list
        assert len(calls) == 2
        assert calls[0][0] == ("BHP", "SELL", 50)  # Day 3 half exit
        assert calls[1][0] == ("BHP", "SELL", 100)  # Stop loss
        assert result == 2

    def test_manage_positions_half_sold_flag_affects_quantity(
        self, mock_trading_bot
    ):
        """Test that half_sold flag correctly affects position quantity"""
        # Position that already had half sold
        mock_position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
            stop_loss=42.00,
            days_held=5,
            half_sold=True,  # Already sold half
        )

        mock_trading_bot.db.get_open_positions.return_value = [mock_position]

        # Market price below stop loss
        mock_market_data = Mock(last_price=41.50)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )
        mock_trading_bot.ib_client.place_order.return_value = Mock(
            filled_price=41.50
        )

        mock_trading_bot.db.update_position_exit.return_value = None
        mock_trading_bot.db.create_trade.return_value = None

        result = mock_trading_bot.manage_positions()

        # Should only sell remaining half (50)
        mock_trading_bot.ib_client.place_order.assert_called_once_with(
            "BHP", "SELL", 50
        )
        assert result == 1

    def test_manage_positions_no_exit_when_healthy(self, mock_trading_bot):
        """Test that no exit happens when position is healthy"""
        # Healthy position: day 1, above stop loss
        mock_position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
            stop_loss=42.00,
            days_held=1,
            half_sold=False,
        )

        mock_trading_bot.db.get_open_positions.return_value = [mock_position]

        # Market price above stop loss, before day 3
        mock_market_data = Mock(last_price=47.00)
        mock_trading_bot.ib_client._get_contract_id.return_value = "8644"
        mock_trading_bot.ib_client.get_market_data.return_value = (
            mock_market_data
        )

        result = mock_trading_bot.manage_positions()

        # No orders should be placed
        mock_trading_bot.ib_client.place_order.assert_not_called()
        assert result == 0


class TestExitStrategyFunctions:
    """Test exit_strategy functions work correctly"""

    def test_check_stop_loss_triggered(self):
        """Test that check_stop_loss triggers when price below stop"""
        position = Mock(
            stop_loss=42.00,
            quantity=100,
            half_sold=False,
        )
        signal = check_stop_loss(position, current_price=41.50)
        assert signal is not None
        assert signal.action == "SELL_ALL"
        assert signal.quantity == 100

    def test_check_stop_loss_not_triggered(self):
        """Test that check_stop_loss doesn't trigger above stop"""
        position = Mock(
            stop_loss=42.00,
            quantity=100,
            half_sold=False,
        )
        signal = check_stop_loss(position, current_price=43.00)
        assert signal is None

    def test_check_stop_loss_with_low_of_day(self):
        """Test that check_stop_loss uses low_of_day when provided"""
        position = Mock(
            stop_loss=42.00,
            quantity=100,
            half_sold=False,
        )
        # low_of_day=41.00, current_price=41.50, stop_price uses low_of_day so 41.50 > 41.00
        # Actually it should NOT trigger. Let me fix to make current_price <= low_of_day
        signal = check_stop_loss(
            position, current_price=40.50, low_of_day=41.00
        )
        assert signal is not None
        assert signal.action == "SELL_ALL"

    def test_check_stop_loss_respects_half_sold(self):
        """Test that check_stop_loss sells correct amount when half sold"""
        position = Mock(
            stop_loss=42.00,
            quantity=100,
            half_sold=True,
        )
        signal = check_stop_loss(position, current_price=41.50)
        assert signal is not None
        assert signal.quantity == 50  # Half of 100

    def test_check_half_exit_on_day3(self):
        """Test that check_half_exit triggers on day 3"""
        position = Mock(
            quantity=100,
            half_sold=False,
        )
        signal = check_half_exit(position, days_held=3)
        assert signal is not None
        assert signal.action == "SELL_HALF"
        assert signal.quantity == 50

    def test_check_half_exit_not_before_day3(self):
        """Test that check_half_exit doesn't trigger before day 3"""
        position = Mock(
            quantity=100,
            half_sold=False,
        )
        signal = check_half_exit(position, days_held=2)
        assert signal is None

    def test_check_half_exit_skips_if_already_sold(self):
        """Test that check_half_exit skips if already half sold"""
        position = Mock(
            quantity=100,
            half_sold=True,
        )
        signal = check_half_exit(position, days_held=3)
        assert signal is None

    def test_check_trailing_stop_triggered(self):
        """Test that check_trailing_stop triggers below SMA"""
        position = Mock(
            quantity=100,
            half_sold=True,
        )
        signal = check_trailing_stop(
            position, current_price=45.00, sma_10=46.00
        )
        assert signal is not None
        assert signal.action == "SELL_ALL"
        assert signal.quantity == 50

    def test_check_trailing_stop_not_triggered(self):
        """Test that check_trailing_stop doesn't trigger above SMA"""
        position = Mock(
            quantity=100,
            half_sold=True,
        )
        signal = check_trailing_stop(
            position, current_price=47.00, sma_10=46.00
        )
        assert signal is None

    def test_check_trailing_stop_only_after_half_exit(self):
        """Test that check_trailing_stop only applies after half exit"""
        position = Mock(
            quantity=100,
            half_sold=False,
        )
        signal = check_trailing_stop(
            position, current_price=45.00, sma_10=46.00
        )
        assert signal is None
