"""Tests for bot stop loss calculation using real daily low price.

Tests the enhanced stop loss logic that uses real daily low instead of hardcoded -5%.
Follows TDD approach - tests are written first, then implementation.
"""

from unittest.mock import Mock, patch

import pytest

from skim.brokers.ib_interface import MarketData
from skim.core.bot import TradingBot


@pytest.mark.unit
class TestBotStopLossWithDailyLow:
    """Tests for TradingBot stop loss calculation with daily low"""

    def test_stop_loss_uses_daily_low_when_available(
        self, mock_trading_bot
    ):
        """Test that stop loss uses real daily low instead of hardcoded -5%"""
        # Mock market data with daily low
        mock_market_data = MarketData(
            ticker="AAPL",
            last_price=150.0,
            bid=149.5,
            ask=150.5,
            volume=1000,
            low=145.0,  # Daily low is $145
        )
        mock_trading_bot.ib_client.get_market_data.return_value = mock_market_data

        # Mock successful order placement
        mock_trading_bot.ib_client.place_order.return_value = Mock(order_id="12345")

        # Mock candidate data
        candidate = Mock()
        candidate.ticker = "AAPL"
        candidate.current_price = 150.0
        candidate.gap_pct = 3.0
        candidate.volume = 1000000

        # Mock database to return our candidate
        with (
            patch.object(
                mock_trading_bot.db, "get_triggered_candidates", return_value=[candidate]
            ),
            patch.object(mock_trading_bot.db, "count_open_positions", return_value=0),
        ):
            mock_trading_bot.execute()

        # Verify that get_market_data was called to get daily low (called twice - once for execution, once for stop loss)
        assert mock_trading_bot.ib_client.get_market_data.call_count >= 1
        mock_trading_bot.ib_client.get_market_data.assert_any_call("AAPL")

        # Verify order was placed
        mock_trading_bot.ib_client.place_order.assert_called_with(
            "AAPL", "BUY", 33
        )  # 5000/150 = 33

    def test_stop_loss_falls_back_to_percentage_when_daily_low_unavailable(
        self, mock_trading_bot
    ):
        """Test that stop loss falls back to -5% when daily low is unavailable"""
        # Mock market data without daily low (low = 0.0)
        mock_market_data = MarketData(
            ticker="AAPL",
            last_price=150.0,
            bid=149.5,
            ask=150.5,
            volume=1000,
            low=0.0,  # Daily low unavailable
        )
        mock_trading_bot.ib_client.get_market_data.return_value = mock_market_data

        # Mock successful order placement
        mock_trading_bot.ib_client.place_order.return_value = Mock(order_id="12345")

        # Mock candidate data
        candidate = Mock()
        candidate.ticker = "AAPL"
        candidate.current_price = 150.0
        candidate.gap_pct = 3.0
        candidate.volume = 1000000

        # This should fall back to -5% ($142.50) when daily low is unavailable
        with (
            patch.object(
                mock_trading_bot.db, "get_triggered_candidates", return_value=[candidate]
            ),
            patch.object(mock_trading_bot.db, "count_open_positions", return_value=0),
            patch("skim.core.bot.logger") as mock_logger,
        ):
            mock_trading_bot.execute()

        # Verify warning was logged about fallback
        mock_logger.warning.assert_any_call(
            "AAPL: Using fallback stop loss: $142.50 (daily low unavailable)"
        )

    def test_stop_loss_handles_missing_market_data_gracefully(
        self, mock_trading_bot
    ):
        """Test that stop loss handles missing market data gracefully"""
        # Mock missing market data
        mock_trading_bot.ib_client.get_market_data.return_value = None

        # Mock successful order placement
        mock_trading_bot.ib_client.place_order.return_value = Mock(order_id="12345")

        # Mock candidate data
        candidate = Mock()
        candidate.ticker = "AAPL"
        candidate.current_price = 150.0
        candidate.gap_pct = 3.0
        candidate.volume = 1000000

        # This should fall back to -5% when market data is None
        with (
            patch.object(
                mock_trading_bot.db, "get_triggered_candidates", return_value=[candidate]
            ),
            patch.object(mock_trading_bot.db, "count_open_positions", return_value=0),
            patch("skim.core.bot.logger") as mock_logger,
        ):
            mock_trading_bot.execute()

        # Verify warning was logged about missing market data
        mock_logger.warning.assert_any_call(
            "AAPL: No valid market data available"
        )
