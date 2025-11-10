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

    def test_scan_ibkr_gaps_method_exists(self, mock_trading_bot):
        """Test that scan_ibkr_gaps method exists"""
        assert hasattr(mock_trading_bot, "scan_ibkr_gaps")
        assert callable(mock_trading_bot.scan_ibkr_gaps)

    def test_scan_ibkr_gaps_returns_int(self, mock_trading_bot):
        """Test that scan_ibkr_gaps returns int"""
        result = mock_trading_bot.scan_ibkr_gaps()
        assert isinstance(result, int)

    def test_track_or_breakouts_method_exists(self, mock_trading_bot):
        """Test that track_or_breakouts method exists"""
        assert hasattr(mock_trading_bot, "track_or_breakouts")
        assert callable(mock_trading_bot.track_or_breakouts)

    def test_track_or_breakouts_returns_int(self, mock_trading_bot):
        """Test that track_or_breakouts returns int"""
        result = mock_trading_bot.track_or_breakouts()
        assert isinstance(result, int)

    def test_execute_orh_breakouts_method_exists(self, mock_trading_bot):
        """Test that execute_orh_breakouts method exists"""
        assert hasattr(mock_trading_bot, "execute_orh_breakouts")
        assert callable(mock_trading_bot.execute_orh_breakouts)

    def test_execute_orh_breakouts_returns_int(self, mock_trading_bot):
        """Test that execute_orh_breakouts returns int"""
        result = mock_trading_bot.execute_orh_breakouts()
        assert isinstance(result, int)

    def test_scan_ibkr_gaps_uses_ibkr_scanner(
        self, mock_trading_bot, mock_gap_stocks, mocker
    ):
        """Test that scan_ibkr_gaps uses IBKRGapScanner"""
        # Get the mocked scanner instance from the bot
        mock_scanner = mock_trading_bot.ibkr_scanner
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks
        mock_scanner.is_connected.return_value = True

        result = mock_trading_bot.scan_ibkr_gaps()

        # Verify scanner was used
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=3.0)
        assert isinstance(result, int)

    def test_scan_ibkr_gaps_stores_candidates_with_or_tracking_status(
        self, mock_trading_bot, mock_gap_stocks
    ):
        """Test that scan_ibkr_gaps stores candidates with 'or_tracking' status"""
        # Get the mocked scanner instance from the bot
        mock_scanner = mock_trading_bot.ibkr_scanner
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks
        mock_scanner.is_connected.return_value = True

        # Mock database methods
        mock_trading_bot.db.get_candidate = Mock(return_value=None)
        mock_trading_bot.db.save_candidate = Mock()

        result = mock_trading_bot.scan_ibkr_gaps()

        # Verify scanner was used
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=3.0)
        assert isinstance(result, int)

    def test_track_or_breakouts_uses_existing_ibkr_client(self, mock_trading_bot):
        """Test that track_or_breakouts uses existing IBKRClient for authentication"""
        # Mock database methods
        mock_trading_bot.db.get_or_tracking_candidates = Mock(return_value=[])

        result = mock_trading_bot.track_or_breakouts()

        # Should return 0 when no candidates found
        assert result == 0

    def test_track_or_breakouts_updates_orh_breakout_status(
        self, mock_trading_bot, mock_breakout_signals
    ):
        """Test that track_or_breakouts updates candidates to 'orh_breakout' status"""
        # Get the mocked scanner instance from the bot
        mock_scanner = mock_trading_bot.ibkr_scanner
        mock_scanner.track_opening_range.return_value = []
        mock_scanner.filter_breakouts.return_value = mock_breakout_signals
        mock_scanner.is_connected.return_value = True

        # Mock database methods
        mock_trading_bot.db.get_or_tracking_candidates = Mock(
            return_value=[
                Mock(
                    ticker="BHP",
                    conid=8644,
                    prev_close=45.20,
                    gap_percent=5.5,
                )
            ]
        )
        mock_trading_bot.db.update_candidate_or_data = Mock()

        result = mock_trading_bot.track_or_breakouts()

        # Should return the number of breakouts found
        assert isinstance(result, int)

    def test_execute_orh_breakouts_uses_existing_execute_breakout_orders(
        self, mock_trading_bot
    ):
        """Test that execute_orh_breakouts leverages existing _execute_breakout_orders method"""
        # Mock the existing method
        mock_trading_bot._execute_breakout_orders = Mock(return_value=1)

        # Mock database methods
        mock_trading_bot.db.get_orh_breakout_candidates = Mock(return_value=[])

        result = mock_trading_bot.execute_orh_breakouts()

        # Should return 0 when no candidates found
        assert result == 0

    def test_bot_init_uses_ibkr_scanner(self, mock_bot_config):
        """Test that TradingBot __init__ uses IBKRGapScanner"""
        with (
            patch("skim.core.bot.Database"),
            patch("skim.core.bot.IBKRClient"),
            patch("skim.core.bot.DiscordNotifier"),
            patch("skim.core.bot.IBKRGapScanner") as mock_scanner_class,
        ):
            bot = TradingBot(mock_bot_config)

            # Verify IBKRGapScanner is initialized
            mock_scanner_class.assert_called_once()

            # Verify IBKR scanner is used
            assert hasattr(bot, "ibkr_scanner")

    def test_database_integration_methods_exist(self, mock_trading_bot):
        """Test that required database methods are available"""
        # These methods should exist from Phase 3
        assert hasattr(mock_trading_bot.db, "get_or_tracking_candidates")
        assert hasattr(mock_trading_bot.db, "get_orh_breakout_candidates")
        assert hasattr(mock_trading_bot.db, "update_candidate_or_data")
        assert callable(mock_trading_bot.db.get_or_tracking_candidates)
        assert callable(mock_trading_bot.db.get_orh_breakout_candidates)
        assert callable(mock_trading_bot.db.update_candidate_or_data)

    def test_error_handling_scan_ibkr_gaps(self, mock_trading_bot):
        """Test error handling in scan_ibkr_gaps"""
        # Get the mocked scanner instance from the bot
        mock_scanner = mock_trading_bot.ibkr_scanner
        mock_scanner.scan_for_gaps.side_effect = Exception("IBKR API Error")
        mock_scanner.is_connected.return_value = True

        result = mock_trading_bot.scan_ibkr_gaps()

        # Should return 0 when error occurs
        assert result == 0

    def test_error_handling_track_or_breakouts(self, mock_trading_bot):
        """Test error handling in track_or_breakouts"""
        # Get the mocked scanner instance from the bot
        mock_scanner = mock_trading_bot.ibkr_scanner
        mock_scanner.track_opening_range.side_effect = Exception(
            "Tracking error"
        )
        mock_scanner.is_connected.return_value = True

        mock_trading_bot.db.get_or_tracking_candidates = Mock(return_value=[])

        result = mock_trading_bot.track_or_breakouts()

        # Should return 0 when error occurs
        assert result == 0

    def test_error_handling_execute_orh_breakouts(self, mock_trading_bot):
        """Test error handling in execute_orh_breakouts"""
        mock_trading_bot.db.get_orh_breakout_candidates = Mock(
            side_effect=Exception("Database error")
        )

        result = mock_trading_bot.execute_orh_breakouts()

        # Should return 0 when error occurs
        assert result == 0

    def test_scan_method_connects_ibkr_scanner_when_not_connected(self, mock_trading_bot):
        """Test that scan() method connects IBKR scanner when not connected"""
        # Get the mocked scanner instance from the bot
        mock_scanner = mock_trading_bot.ibkr_scanner
        mock_scanner.is_connected.return_value = False
        mock_scanner.scan_for_gaps.return_value = []

        # Mock ASX scanner
        mock_trading_bot.asx_scanner.fetch_price_sensitive_tickers = Mock(return_value=[])

        # Mock Discord notifier
        mock_trading_bot.discord_notifier.send_scan_results = Mock()

        result = mock_trading_bot.scan()

        # Verify connection was established
        mock_scanner.is_connected.assert_called()
        mock_scanner.connect.assert_called_once()
        assert isinstance(result, int)

    def test_scan_method_skips_connection_when_already_connected(self, mock_trading_bot):
        """Test that scan() method skips connection when IBKR scanner is already connected"""
        # Get the mocked scanner instance from the bot
        mock_scanner = mock_trading_bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = []

        # Mock ASX scanner
        mock_trading_bot.asx_scanner.fetch_price_sensitive_tickers = Mock(return_value=[])

        # Mock Discord notifier
        mock_trading_bot.discord_notifier.send_scan_results = Mock()

        result = mock_trading_bot.scan()

        # Verify connection was not attempted
        mock_scanner.connect.assert_not_called()
        assert isinstance(result, int)


class TestTradingBotCoreMethods:
    """Comprehensive tests for TradingBot core methods"""

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

    def test_scan_ibkr_gaps_full_workflow(self, bot, mock_gap_stocks):
        """Test complete scan_ibkr_gaps workflow"""
        # Setup mocks
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = False
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks

        bot.db.get_candidate = Mock(return_value=None)
        bot.db.save_candidate = Mock()

        # Execute
        result = bot.scan_ibkr_gaps()

        # Verify workflow
        mock_scanner.is_connected.assert_called()
        mock_scanner.connect.assert_called_once()
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=3.0)

        # Verify candidates were saved
        assert bot.db.save_candidate.call_count == 2
        assert result == 2

    def test_scan_ibkr_gaps_with_existing_candidates(
        self, bot, mock_gap_stocks
    ):
        """Test scan_ibkr_gaps with existing candidates"""
        # Setup mocks
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks

        # Mock existing candidate for BHP
        def mock_get_candidate(ticker):
            if ticker == "BHP":
                return Mock(status="or_tracking")
            return None

        bot.db.get_candidate = Mock(side_effect=mock_get_candidate)
        bot.db.save_candidate = Mock()

        # Execute
        result = bot.scan_ibkr_gaps()

        # Verify only new candidate was saved
        bot.db.save_candidate.assert_called_once()
        assert result == 1

    def test_scan_ibkr_gaps_no_stocks_found(self, bot):
        """Test scan_ibkr_gaps when no stocks found"""
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = []

        result = bot.scan_ibkr_gaps()

        assert result == 0
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=3.0)

    def test_scan_ibkr_gaps_connection_error(self, bot):
        """Test scan_ibkr_gaps with connection error"""
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = False
        mock_scanner.connect.side_effect = Exception("Connection failed")

        result = bot.scan_ibkr_gaps()

        assert result == 0

    def test_track_or_breakouts_full_workflow(
        self, bot, mock_or_data, mock_breakout_signals
    ):
        """Test complete track_or_breakouts workflow"""
        # Setup mock candidates
        mock_candidates = [
            Mock(
                ticker="BHP",
                conid=8644,
                prev_close=45.20,
                gap_percent=5.5,
            )
        ]

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.track_opening_range.return_value = mock_or_data
        mock_scanner.filter_breakouts.return_value = mock_breakout_signals

        bot.db.get_or_tracking_candidates = Mock(return_value=mock_candidates)
        bot.db.update_candidate_or_data = Mock()
        bot.db.update_candidate_status = Mock()

        result = bot.track_or_breakouts()

        # Verify workflow
        bot.db.get_or_tracking_candidates.assert_called_once()
        mock_scanner.track_opening_range.assert_called_once()
        mock_scanner.filter_breakouts.assert_called_once_with(mock_or_data)

        # Verify breakout was processed
        bot.db.update_candidate_or_data.assert_called_once()
        bot.db.update_candidate_status.assert_called_once_with(
            "BHP", "orh_breakout"
        )

        assert result == 1

    def test_track_or_breakouts_no_candidates(self, bot):
        """Test track_or_breakouts with no candidates"""
        bot.db.get_or_tracking_candidates = Mock(return_value=[])

        result = bot.track_or_breakouts()

        assert result == 0
        bot.db.get_or_tracking_candidates.assert_called_once()

    def test_track_or_breakouts_invalid_candidates(self, bot):
        """Test track_or_breakouts with invalid candidates (missing conid/prev_close)"""
        mock_candidates = [
            Mock(ticker="BHP", conid=None, prev_close=45.20),  # Missing conid
            Mock(
                ticker="RIO", conid=8653, prev_close=None
            ),  # Missing prev_close
        ]

        bot.db.get_or_tracking_candidates = Mock(return_value=mock_candidates)

        result = bot.track_or_breakouts()

        assert result == 0

    def test_track_or_breakouts_connection_error(self, bot):
        """Test track_or_breakouts with connection error"""
        mock_candidates = [
            Mock(ticker="BHP", conid=8644, prev_close=45.20),
        ]

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = False
        mock_scanner.connect.side_effect = Exception("Connection failed")

        bot.db.get_or_tracking_candidates = Mock(return_value=mock_candidates)

        result = bot.track_or_breakouts()

        assert result == 0

    def test_execute_orh_breakouts_full_workflow(self, bot):
        """Test complete execute_orh_breakouts workflow"""
        # Setup mock candidates
        mock_candidates = [
            Mock(
                ticker="BHP",
                or_low=44.80,
            )
        ]

        # Mock IB client
        mock_ib_client = bot.ib_client
        mock_market_data = Mock(last_price=46.80, low=44.50)
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_order_result = Mock(filled_price=46.75)
        mock_ib_client.place_order.return_value = mock_order_result

        # Mock database
        bot.db.get_orh_breakout_candidates = Mock(return_value=mock_candidates)
        bot.db.count_open_positions = Mock(return_value=0)
        bot.db.create_position = Mock(return_value=1)
        bot.db.create_trade = Mock()
        bot.db.update_candidate_status = Mock()

        result = bot.execute_orh_breakouts()

        # Verify workflow
        bot.db.get_orh_breakout_candidates.assert_called_once()
        mock_ib_client.get_market_data.assert_called_once_with("BHP")
        mock_ib_client.place_order.assert_called_once_with(
            "BHP", "BUY", 106
        )  # 5000/46.80 ≈ 106
        bot.db.create_position.assert_called_once()
        bot.db.create_trade.assert_called_once()
        bot.db.update_candidate_status.assert_called_once_with("BHP", "entered")

        assert result == 1

    def test_execute_orh_breakouts_no_candidates(self, bot):
        """Test execute_orh_breakouts with no candidates"""
        bot.db.get_orh_breakout_candidates = Mock(return_value=[])

        result = bot.execute_orh_breakouts()

        assert result == 0

    def test_execute_orh_breakouts_max_positions_reached(self, bot):
        """Test execute_orh_breakouts when max positions reached"""
        mock_candidates = [Mock(ticker="BHP")]

        bot.db.get_orh_breakout_candidates = Mock(return_value=mock_candidates)
        bot.db.count_open_positions = Mock(return_value=5)  # Max positions

        result = bot.execute_orh_breakouts()

        assert result == 0

    def test_execute_orh_breakouts_no_market_data(self, bot):
        """Test execute_orh_breakouts with no market data"""
        mock_candidates = [Mock(ticker="BHP")]

        mock_ib_client = bot.ib_client
        mock_ib_client.get_market_data.return_value = None

        bot.db.get_orh_breakout_candidates = Mock(return_value=mock_candidates)
        bot.db.count_open_positions = Mock(return_value=0)

        result = bot.execute_orh_breakouts()

        assert result == 0

    def test_execute_orh_breakouts_order_failed(self, bot):
        """Test execute_orh_breakouts when order placement fails"""
        mock_candidates = [Mock(ticker="BHP")]

        mock_ib_client = bot.ib_client
        mock_market_data = Mock(last_price=46.80)
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_ib_client.place_order.return_value = None  # Order failed

        bot.db.get_orh_breakout_candidates = Mock(return_value=mock_candidates)
        bot.db.count_open_positions = Mock(return_value=0)

        result = bot.execute_orh_breakouts()

        assert result == 0

    def test_execute_orh_breakouts_fallback_stop_loss(self, bot):
        """Test execute_orh_breakouts uses fallback stop loss when or_low unavailable"""
        mock_candidates = [
            Mock(ticker="BHP", or_low=None)  # No OR low
        ]

        mock_ib_client = bot.ib_client
        mock_market_data = Mock(last_price=46.80)
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_order_result = Mock(filled_price=46.75)
        mock_ib_client.place_order.return_value = mock_order_result

        bot.db.get_orh_breakout_candidates = Mock(return_value=mock_candidates)
        bot.db.count_open_positions = Mock(return_value=0)
        bot.db.create_position = Mock(return_value=1)
        bot.db.create_trade = Mock()
        bot.db.update_candidate_status = Mock()

        result = bot.execute_orh_breakouts()

        # Verify fallback stop loss was used (5% below entry)
        expected_stop_loss = 46.75 * 0.95  # ≈ 44.41
        bot.db.create_position.assert_called_once()
        call_args = bot.db.create_position.call_args
        actual_stop_loss = call_args[1]["stop_loss"]
        assert (
            abs(actual_stop_loss - expected_stop_loss) < 0.1
        )  # Allow small rounding difference

        assert result == 1

    def test_ensure_connection_when_not_connected(self, bot):
        """Test _ensure_connection connects when not connected"""
        mock_ib_client = bot.ib_client
        mock_ib_client.is_connected.return_value = False

        bot._ensure_connection()

        mock_ib_client.connect.assert_called_once()

    def test_ensure_connection_when_already_connected(self, bot):
        """Test _ensure_connection skips when already connected"""
        mock_ib_client = bot.ib_client
        mock_ib_client.is_connected.return_value = True

        bot._ensure_connection()

        mock_ib_client.connect.assert_not_called()

    def test_connect_ib_when_not_connected(self, bot):
        """Test _connect_ib connects when not connected"""
        mock_ib_client = bot.ib_client
        mock_ib_client.is_connected.return_value = False

        bot._connect_ib()

        mock_ib_client.connect.assert_called_once_with(
            host="", port=0, client_id=0, timeout=20
        )

    def test_connect_ib_when_already_connected(self, bot):
        """Test _connect_ib skips when already connected"""
        mock_ib_client = bot.ib_client
        mock_ib_client.is_connected.return_value = True

        bot._connect_ib()

        mock_ib_client.connect.assert_not_called()


class TestTradingBotWorkflowMethods:
    """Tests for TradingBot workflow methods"""

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

    def test_scan_full_workflow_with_candidates(self, bot, mock_gap_stocks):
        """Test complete scan workflow with candidates found"""
        # Setup mocks
        bot.asx_scanner.fetch_price_sensitive_tickers.return_value = {
            "BHP",
            "RIO",
        }

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = False
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks

        bot.db.get_candidate = Mock(return_value=None)
        bot.db.save_candidate = Mock()
        bot.discord_notifier.send_scan_results = Mock()

        result = bot.scan()

        # Verify workflow
        bot.asx_scanner.fetch_price_sensitive_tickers.assert_called_once()
        mock_scanner.connect.assert_called_once()
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=2.0)

        # Verify candidates were saved
        assert bot.db.save_candidate.call_count == 2

        # Verify Discord notification
        bot.discord_notifier.send_scan_results.assert_called_once()
        call_args = bot.discord_notifier.send_scan_results.call_args
        assert call_args[0][0] == 2  # candidates_found
        assert len(call_args[0][1]) == 2  # new_candidates

        assert result == 2

    def test_scan_workflow_no_price_sensitive(self, bot, mock_gap_stocks):
        """Test scan workflow with no price-sensitive announcements"""
        # Setup mocks
        bot.asx_scanner.fetch_price_sensitive_tickers.return_value = (
            set()
        )  # No announcements

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks

        bot.db.save_candidate = Mock()
        bot.discord_notifier.send_scan_results = Mock()

        result = bot.scan()

        # Verify no candidates were saved
        bot.db.save_candidate.assert_not_called()

        # Verify Discord notification with 0 candidates
        bot.discord_notifier.send_scan_results.assert_called_once_with(0, [])

        assert result == 0

    def test_scan_workflow_no_stocks_found(self, bot):
        """Test scan workflow when no stocks found"""
        # Setup mocks
        bot.asx_scanner.fetch_price_sensitive_tickers.return_value = set()

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = []

        bot.discord_notifier.send_scan_results = Mock()

        result = bot.scan()

        # Verify Discord notification with 0 candidates
        bot.discord_notifier.send_scan_results.assert_called_once_with(0, [])

        assert result == 0

    def test_scan_workflow_discord_error(self, bot, mock_gap_stocks):
        """Test scan workflow handles Discord notification errors"""
        # Setup mocks
        bot.asx_scanner.fetch_price_sensitive_tickers.return_value = {"BHP"}

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks[
            :1
        ]  # Only BHP

        bot.db.get_candidate = Mock(return_value=None)
        bot.db.save_candidate = Mock()
        bot.discord_notifier.send_scan_results.side_effect = Exception(
            "Discord error"
        )

        result = bot.scan()

        # Should still complete successfully despite Discord error
        assert result == 1
        bot.db.save_candidate.assert_called_once()

    def test_monitor_workflow_with_triggered_candidates(
        self, bot, mock_gap_stocks
    ):
        """Test monitor workflow with triggered candidates"""
        # Setup mocks
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks

        # Mock existing candidates
        mock_candidates = [Mock(ticker="BHP")]
        bot.db.get_watching_candidates = Mock(return_value=mock_candidates)
        bot.db.update_candidate_status = Mock()

        result = bot.monitor()

        # Verify workflow
        mock_scanner.scan_for_gaps.assert_called_once_with(min_gap=3.0)
        bot.db.get_watching_candidates.assert_called_once()

        # Verify BHP was triggered (in candidates)
        bot.db.update_candidate_status.assert_called_once_with(
            "BHP", "triggered", 5.5
        )

        # Verify RIO was added as new triggered stock
        bot.db.save_candidate.assert_called_once()
        save_call = bot.db.save_candidate.call_args[0][0]
        assert save_call.ticker == "RIO"
        assert save_call.status == "triggered"

        assert result == 2

    def test_monitor_workflow_no_triggered_stocks(self, bot):
        """Test monitor workflow with no triggered stocks"""
        # Setup mocks
        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = []

        bot.db.get_watching_candidates = Mock(return_value=[])

        result = bot.monitor()

        assert result == 0
        bot.db.update_candidate_status.assert_not_called()
        bot.db.save_candidate.assert_not_called()

    def test_execute_workflow_with_orders(self, bot):
        """Test execute workflow with orders placed"""
        # Setup mocks
        mock_ib_client = bot.ib_client
        mock_market_data = Mock(last_price=46.80, low=44.50)
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_order_result = Mock(filled_price=46.75)
        mock_ib_client.place_order.return_value = mock_order_result

        # Mock triggered candidates
        mock_candidates = [Mock(ticker="BHP")]
        bot.db.get_triggered_candidates = Mock(return_value=mock_candidates)
        bot.db.count_open_positions = Mock(return_value=0)
        bot.db.create_position = Mock(return_value=1)
        bot.db.create_trade = Mock()
        bot.db.update_candidate_status = Mock()

        result = bot.execute()

        # Verify workflow
        bot.db.get_triggered_candidates.assert_called_once()
        mock_ib_client.get_market_data.assert_called()  # Called twice (once for price, once for low)
        mock_ib_client.place_order.assert_called_once_with(
            "BHP", "BUY", 106
        )  # 5000/46.80 ≈ 106
        bot.db.create_position.assert_called_once()
        bot.db.create_trade.assert_called_once()
        bot.db.update_candidate_status.assert_called_once_with("BHP", "entered")

        assert result == 1

    def test_execute_workflow_max_positions_reached(self, bot):
        """Test execute workflow when max positions reached"""
        bot.db.count_open_positions = Mock(return_value=5)  # Max positions

        result = bot.execute()

        assert result == 0
        # get_triggered_candidates is not called when max positions reached

    def test_execute_workflow_no_triggered_candidates(self, bot):
        """Test execute workflow with no triggered candidates"""
        bot.db.count_open_positions = Mock(
            return_value=0
        )  # Mock return value as int
        bot.db.get_triggered_candidates = Mock(return_value=[])

        result = bot.execute()

        assert result == 0

    def test_execute_workflow_no_market_data(self, bot):
        """Test execute workflow with no market data"""
        mock_ib_client = bot.ib_client
        mock_ib_client.get_market_data.return_value = None

        bot.db.get_triggered_candidates = Mock(
            return_value=[Mock(ticker="BHP")]
        )
        bot.db.count_open_positions = Mock(return_value=0)

        result = bot.execute()

        assert result == 0

    def test_execute_workflow_order_failed(self, bot):
        """Test execute workflow when order placement fails"""
        mock_ib_client = bot.ib_client
        mock_market_data = Mock(last_price=46.80)
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_ib_client.place_order.return_value = None  # Order failed

        bot.db.get_triggered_candidates = Mock(
            return_value=[Mock(ticker="BHP")]
        )
        bot.db.count_open_positions = Mock(return_value=0)

        result = bot.execute()

        assert result == 0

    def test_manage_positions_day3_exit(self, bot):
        """Test manage_positions with day 3 exit"""
        # Setup mock position
        mock_position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
            stop_loss=42.00,
            days_held=3,
            half_sold=False,
        )

        mock_ib_client = bot.ib_client
        mock_market_data = Mock(last_price=50.00)
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_order_result = Mock(filled_price=50.00)
        mock_ib_client.place_order.return_value = mock_order_result

        bot.db.get_open_positions = Mock(return_value=[mock_position])
        bot.db.update_position_half_sold = Mock()
        bot.db.create_trade = Mock()
        bot.db.update_candidate_status = Mock()

        result = bot.manage_positions()

        # Verify day 3 exit
        mock_ib_client.place_order.assert_called_once_with(
            "BHP", "SELL", 50
        )  # Half of 100
        bot.db.update_position_half_sold.assert_called_once_with(1, True)
        bot.db.create_trade.assert_called_once()
        bot.db.update_candidate_status.assert_called_once_with(
            "BHP", "half_exited"
        )

        assert result == 1

    def test_manage_positions_stop_loss_triggered(self, bot):
        """Test manage_positions with stop loss triggered"""
        # Setup mock position
        mock_position = Mock(
            ticker="BHP",
            id=1,
            quantity=100,
            entry_price=45.00,
            stop_loss=42.00,
            days_held=1,
            half_sold=False,
        )

        mock_ib_client = bot.ib_client
        mock_market_data = Mock(last_price=41.50)  # Below stop loss
        mock_ib_client.get_market_data.return_value = mock_market_data
        mock_order_result = Mock(filled_price=41.50)
        mock_ib_client.place_order.return_value = mock_order_result

        bot.db.get_open_positions = Mock(return_value=[mock_position])
        bot.db.update_position_exit = Mock()
        bot.db.create_trade = Mock()

        result = bot.manage_positions()

        # Verify stop loss exit
        mock_ib_client.place_order.assert_called_once_with("BHP", "SELL", 100)
        bot.db.update_position_exit.assert_called_once()
        bot.db.create_trade.assert_called_once()

        assert result == 1

    def test_manage_positions_no_positions(self, bot):
        """Test manage_positions with no open positions"""
        bot.db.get_open_positions = Mock(return_value=[])

        result = bot.manage_positions()

        assert result == 0

    def test_manage_positions_no_market_data(self, bot):
        """Test manage_positions with no market data"""
        mock_position = Mock(ticker="BHP", id=1)

        mock_ib_client = bot.ib_client
        mock_ib_client.get_market_data.return_value = None

        bot.db.get_open_positions = Mock(return_value=[mock_position])

        result = bot.manage_positions()

        assert result == 0

    def test_status_display(self, bot):
        """Test status display method"""
        # Setup mocks
        bot.db.count_watching_candidates = Mock(return_value=3)
        bot.db.count_open_positions = Mock(return_value=2)
        bot.db.get_open_positions = Mock(
            return_value=[
                Mock(
                    ticker="BHP", quantity=100, entry_price=45.00, status="open"
                ),
                Mock(
                    ticker="RIO", quantity=50, entry_price=120.00, status="open"
                ),
            ]
        )
        bot.db.get_total_pnl = Mock(return_value=1250.50)

        # Should not raise any exceptions
        bot.status()

        # Verify all database methods were called
        bot.db.count_watching_candidates.assert_called_once()
        bot.db.count_open_positions.assert_called_once()
        bot.db.get_open_positions.assert_called_once()
        bot.db.get_total_pnl.assert_called_once()
