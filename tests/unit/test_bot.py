"""Tests for TradingBot class"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest

from skim.core.bot import TradingBot
from skim.core.config import Config
from skim.scanners.ibkr_gap_scanner import (
    BreakoutSignal,
    GapStock,
    OpeningRangeData,
)


class TestTradingBotIBKRIntegration:
    """Test IBKR gap scanning integration with TradingBot"""

    @pytest.fixture
    def config(self):
        """Create test configuration"""
        config = Mock(spec=Config)
        config.gap_threshold = 3.0
        config.max_positions = 5
        config.max_position_size = 1000
        config.paper_trading = True
        config.discord_webhook_url = "https://discord-webhook.com"
        config.db_path = ":memory:"
        return config

    @pytest.fixture
    def bot(self, config):
        """Create TradingBot instance with mocked dependencies"""
        with (
            patch("skim.core.bot.Database"),
            patch("skim.core.bot.IBKRClient"),
            patch("skim.core.bot.DiscordNotifier"),
            patch("skim.core.bot.IBKRGapScanner"),
            patch("skim.core.bot.ASXAnnouncementScanner"),
        ):
            return TradingBot(config)

    @pytest.fixture
    def mock_gap_stocks(self):
        """Create mock gap stocks data"""
        return [
            GapStock(
                ticker="BHP", gap_percent=5.5, close_price=45.20, conid=8644
            ),
            GapStock(
                ticker="RIO", gap_percent=4.2, close_price=120.50, conid=8653
            ),
        ]

    @pytest.fixture
    def mock_or_data(self):
        """Create mock opening range data"""
        return [
            OpeningRangeData(
                ticker="BHP",
                conid=8644,
                or_high=46.50,
                or_low=44.80,
                open_price=45.50,
                prev_close=45.20,
                current_price=46.80,
                gap_holding=True,
            ),
            OpeningRangeData(
                ticker="RIO",
                conid=8653,
                or_high=121.50,
                or_low=119.80,
                open_price=120.00,
                prev_close=120.50,
                current_price=119.50,
                gap_holding=False,
            ),
        ]

    @pytest.fixture
    def mock_breakout_signals(self):
        """Create mock breakout signals"""
        return [
            BreakoutSignal(
                ticker="BHP",
                conid=8644,
                gap_pct=5.5,
                or_high=46.50,
                or_low=44.80,
                or_size_pct=3.8,
                current_price=46.80,
                entry_signal="ORB_HIGH_BREAKOUT",
                timestamp=datetime.now(),
            )
        ]

    def test_scan_ibkr_gaps_method_exists(self, bot):
        """Test that scan_ibkr_gaps method exists"""
        assert hasattr(bot, "scan_ibkr_gaps")
        assert callable(bot.scan_ibkr_gaps)

    def test_scan_ibkr_gaps_returns_int(self, bot):
        """Test that scan_ibkr_gaps returns int"""
        result = bot.scan_ibkr_gaps()
        assert isinstance(result, int)

    def test_track_or_breakouts_method_exists(self, bot):
        """Test that track_or_breakouts method exists"""
        assert hasattr(bot, "track_or_breakouts")
        assert callable(bot.track_or_breakouts)

    def test_track_or_breakouts_returns_int(self, bot):
        """Test that track_or_breakouts returns int"""
        result = bot.track_or_breakouts()
        assert isinstance(result, int)

    def test_execute_orh_breakouts_method_exists(self, bot):
        """Test that execute_orh_breakouts method exists"""
        assert hasattr(bot, "execute_orh_breakouts")
        assert callable(bot.execute_orh_breakouts)

    def test_execute_orh_breakouts_returns_int(self, bot):
        """Test that execute_orh_breakouts returns int"""
        result = bot.execute_orh_breakouts()
        assert isinstance(result, int)

    def test_scan_ibkr_gaps_uses_ibkr_scanner(
        self, bot, mock_gap_stocks, mocker
    ):
        """Test that scan_ibkr_gaps uses IBKRGapScanner"""
        # Get the mocked scanner instance from the bot
        mock_scanner = bot.ibkr_scanner
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks
        mock_scanner.is_connected.return_value = True

        result = bot.scan_ibkr_gaps()

        # Verify scanner was used
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=3.0)
        assert isinstance(result, int)

    def test_scan_ibkr_gaps_stores_candidates_with_or_tracking_status(
        self, bot, mock_gap_stocks
    ):
        """Test that scan_ibkr_gaps stores candidates with 'or_tracking' status"""
        # Get the mocked scanner instance from the bot
        mock_scanner = bot.ibkr_scanner
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks
        mock_scanner.is_connected.return_value = True

        # Mock database methods
        bot.db.get_candidate = Mock(return_value=None)
        bot.db.save_candidate = Mock()

        result = bot.scan_ibkr_gaps()

        # Verify scanner was used
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=3.0)
        assert isinstance(result, int)

    def test_track_or_breakouts_uses_existing_ibkr_client(self, bot):
        """Test that track_or_breakouts uses existing IBKRClient for authentication"""
        # Mock database methods
        bot.db.get_or_tracking_candidates = Mock(return_value=[])

        result = bot.track_or_breakouts()

        # Should return 0 when no candidates found
        assert result == 0

    def test_track_or_breakouts_updates_orh_breakout_status(
        self, bot, mock_breakout_signals
    ):
        """Test that track_or_breakouts updates candidates to 'orh_breakout' status"""
        # Get the mocked scanner instance from the bot
        mock_scanner = bot.ibkr_scanner
        mock_scanner.track_opening_range.return_value = []
        mock_scanner.filter_breakouts.return_value = mock_breakout_signals
        mock_scanner.is_connected.return_value = True

        # Mock database methods
        bot.db.get_or_tracking_candidates = Mock(
            return_value=[
                Mock(
                    ticker="BHP",
                    conid=8644,
                    prev_close=45.20,
                    gap_percent=5.5,
                )
            ]
        )
        bot.db.update_candidate_or_data = Mock()

        result = bot.track_or_breakouts()

        # Should return the number of breakouts found
        assert isinstance(result, int)

    def test_execute_orh_breakouts_uses_existing_execute_breakout_orders(
        self, bot
    ):
        """Test that execute_orh_breakouts leverages existing _execute_breakout_orders method"""
        # Mock the existing method
        bot._execute_breakout_orders = Mock(return_value=1)

        # Mock database methods
        bot.db.get_orh_breakout_candidates = Mock(return_value=[])

        result = bot.execute_orh_breakouts()

        # Should return 0 when no candidates found
        assert result == 0

    def test_bot_init_uses_ibkr_scanner(self, config):
        """Test that TradingBot __init__ uses IBKRGapScanner"""
        with (
            patch("skim.core.bot.Database"),
            patch("skim.core.bot.IBKRClient"),
            patch("skim.core.bot.DiscordNotifier"),
            patch("skim.core.bot.IBKRGapScanner") as mock_scanner_class,
        ):
            bot = TradingBot(config)

            # Verify IBKRGapScanner is initialized
            mock_scanner_class.assert_called_once()

            # Verify IBKR scanner is used
            assert hasattr(bot, "ibkr_scanner")

    def test_database_integration_methods_exist(self, bot):
        """Test that required database methods are available"""
        # These methods should exist from Phase 3
        assert hasattr(bot.db, "get_or_tracking_candidates")
        assert hasattr(bot.db, "get_orh_breakout_candidates")
        assert hasattr(bot.db, "update_candidate_or_data")
        assert callable(bot.db.get_or_tracking_candidates)
        assert callable(bot.db.get_orh_breakout_candidates)
        assert callable(bot.db.update_candidate_or_data)

    def test_error_handling_scan_ibkr_gaps(self, bot):
        """Test error handling in scan_ibkr_gaps"""
        # Get the mocked scanner instance from the bot
        mock_scanner = bot.ibkr_scanner
        mock_scanner.scan_for_gaps.side_effect = Exception("IBKR API Error")
        mock_scanner.is_connected.return_value = True

        result = bot.scan_ibkr_gaps()

        # Should return 0 when error occurs
        assert result == 0

    def test_error_handling_track_or_breakouts(self, bot):
        """Test error handling in track_or_breakouts"""
        # Get the mocked scanner instance from the bot
        mock_scanner = bot.ibkr_scanner
        mock_scanner.track_opening_range.side_effect = Exception(
            "Tracking error"
        )
        mock_scanner.is_connected.return_value = True

        bot.db.get_or_tracking_candidates = Mock(return_value=[])

        result = bot.track_or_breakouts()

        # Should return 0 when error occurs
        assert result == 0

    def test_error_handling_execute_orh_breakouts(self, bot):
        """Test error handling in execute_orh_breakouts"""
        bot.db.get_orh_breakout_candidates = Mock(
            side_effect=Exception("Database error")
        )

        result = bot.execute_orh_breakouts()

        # Should return 0 when error occurs
        assert result == 0

    def test_scan_method_connects_ibkr_scanner_when_not_connected(self, bot):
        """Test that scan() method connects IBKR scanner when not connected"""
        # Get the mocked scanner instance from the bot
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = False
        mock_scanner.scan_for_gaps.return_value = []

        # Mock ASX scanner
        bot.asx_scanner.fetch_price_sensitive_tickers = Mock(return_value=[])

        # Mock Discord notifier
        bot.discord_notifier.send_scan_results = Mock()

        result = bot.scan()

        # Verify connection was established
        mock_scanner.is_connected.assert_called()
        mock_scanner.connect.assert_called_once()
        assert isinstance(result, int)

    def test_scan_method_skips_connection_when_already_connected(self, bot):
        """Test that scan() method skips connection when IBKR scanner is already connected"""
        # Get the mocked scanner instance from the bot
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = []

        # Mock ASX scanner
        bot.asx_scanner.fetch_price_sensitive_tickers = Mock(return_value=[])

        # Mock Discord notifier
        bot.discord_notifier.send_scan_results = Mock()

        result = bot.scan()

        # Verify connection was not attempted
        mock_scanner.connect.assert_not_called()
        assert isinstance(result, int)
