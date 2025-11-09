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

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration"""
        config = Mock()
        config.max_position_size = 10000
        config.max_positions = 5
        config.gap_threshold = 2.0
        config.stop_loss_pct = 5.0
        config.db_path = ":memory:"
        config.paper_trading = True
        config.discord_webhook_url = "https://example.com/webhook"
        return config

    @pytest.fixture
    def mock_ib_client(self):
        """Create mock IBKR client"""
        client = Mock()
        client.is_connected.return_value = True
        return client

    @pytest.fixture
    def bot(self, mock_config, mock_ib_client):
        """Create TradingBot instance with mocked dependencies"""
        with (
            patch("skim.core.bot.Database"),
            patch("skim.core.bot.IBKRClient", return_value=mock_ib_client),
            patch("skim.core.bot.IBKRGapScanner"),
            patch("skim.core.bot.ASXAnnouncementScanner"),
            patch("skim.core.bot.DiscordNotifier"),
        ):
            bot = TradingBot(mock_config)
            return bot

    def test_stop_loss_uses_daily_low_when_available(self, bot, mock_ib_client):
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
        mock_ib_client.get_market_data.return_value = mock_market_data

        # Mock successful order placement
        mock_ib_client.place_order.return_value = Mock(order_id="12345")

        # Mock candidate data
        candidate = Mock()
        candidate.ticker = "AAPL"
        candidate.current_price = 150.0
        candidate.gap_pct = 3.0
        candidate.volume = 1000000

        # Mock database to return our candidate
        with (
            patch.object(
                bot.db, "get_triggered_candidates", return_value=[candidate]
            ),
            patch.object(bot.db, "count_open_positions", return_value=0),
        ):
            bot.execute()

        # Verify that get_market_data was called to get daily low (called twice - once for execution, once for stop loss)
        assert mock_ib_client.get_market_data.call_count >= 1
        mock_ib_client.get_market_data.assert_any_call("AAPL")

        # Verify order was placed
        mock_ib_client.place_order.assert_called_with(
            "AAPL", "BUY", 33
        )  # 5000/150 = 33

    def test_stop_loss_falls_back_to_percentage_when_daily_low_unavailable(
        self, bot, mock_ib_client
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
        mock_ib_client.get_market_data.return_value = mock_market_data

        # Mock successful order placement
        mock_ib_client.place_order.return_value = Mock(order_id="12345")

        # Mock candidate data
        candidate = Mock()
        candidate.ticker = "AAPL"
        candidate.current_price = 150.0
        candidate.gap_pct = 3.0
        candidate.volume = 1000000

        # This should fall back to -5% ($142.50) when daily low is unavailable
        with (
            patch.object(
                bot.db, "get_triggered_candidates", return_value=[candidate]
            ),
            patch.object(bot.db, "count_open_positions", return_value=0),
            patch("skim.core.bot.logger") as mock_logger,
        ):
            bot.execute()

        # Verify warning was logged about fallback
        mock_logger.warning.assert_any_call(
            "AAPL: Using fallback stop loss: $142.50 (daily low unavailable)"
        )

    def test_stop_loss_handles_missing_market_data_gracefully(
        self, bot, mock_ib_client
    ):
        """Test that stop loss handles missing market data gracefully"""
        # Mock missing market data
        mock_ib_client.get_market_data.return_value = None

        # Mock successful order placement
        mock_ib_client.place_order.return_value = Mock(order_id="12345")

        # Mock candidate data
        candidate = Mock()
        candidate.ticker = "AAPL"
        candidate.current_price = 150.0
        candidate.gap_pct = 3.0
        candidate.volume = 1000000

        # This should fall back to -5% when market data is None
        with (
            patch.object(
                bot.db, "get_triggered_candidates", return_value=[candidate]
            ),
            patch.object(bot.db, "count_open_positions", return_value=0),
            patch("skim.core.bot.logger") as mock_logger,
        ):
            bot.execute()

        # Verify warning was logged about missing market data
        mock_logger.warning.assert_any_call(
            "AAPL: No valid market data available"
        )
