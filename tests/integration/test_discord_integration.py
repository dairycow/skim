"""Integration tests for Discord notifications in TradingBot"""

from unittest.mock import Mock, patch

import pytest

from skim.core.bot import TradingBot
from skim.core.config import Config, ScannerConfig


@pytest.mark.integration
class TestTradingBotDiscordIntegration:
    """Tests for Discord integration in TradingBot"""

    @patch("skim.core.bot.ASXAnnouncementScanner")
    @patch("skim.core.bot.IBKRGapScanner")
    @patch("skim.core.bot.Database")
    @patch("skim.notifications.discord.requests.post")
    def test_scan_with_discord_notification_success(
        self, mock_requests_post, mock_db, mock_ibkr_scanner, mock_asx_scanner
    ):
        """Test scan method with Discord notification success"""
        from skim.validation.scanners import GapScanResult

        # Setup config
        config = Config(
            ib_client_id=1,
            paper_trading=True,
            max_position_size=1000,
            max_positions=5,
            db_path="test.db",
            discord_webhook_url="https://discord.com/api/webhooks/test/webhook",
            scanner_config=ScannerConfig(
                gap_threshold=3.0,
                volume_filter=50000,
                price_filter=0.50,
                or_duration_minutes=10,
                or_poll_interval_seconds=30,
                gap_fill_tolerance=1.0,
                or_breakout_buffer=0.1,
            ),
        )

        # Setup mocks
        mock_asx_scanner.return_value.fetch_price_sensitive_tickers.return_value = {
            "BHP",
            "RIO",
        }

        # Create mock result with proper GapScanResult structure
        mock_candidate = {
            "ticker": "BHP",
            "headline": "BHP announces earnings",
            "scan_date": "2025-11-21",
            "status": "watching",
            "gap_percent": 5.5,
            "price": 45.20,
        }

        mock_scan_result = GapScanResult(
            gap_stocks=[], new_candidates=[mock_candidate]
        )
        mock_ibkr_scanner.return_value.is_connected.return_value = True
        mock_ibkr_scanner.return_value.scan_gaps_with_announcements.return_value = mock_scan_result

        mock_db.return_value.get_candidate.return_value = None
        mock_db.return_value.save_candidate = Mock()

        # Mock successful Discord response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_requests_post.return_value = mock_response

        # Create bot and run scan
        bot = TradingBot(config)
        result = bot.scan()

        # Verify scan completed
        assert result == 1

        # Verify Discord notification was sent
        mock_requests_post.assert_called_once()
        call_args = mock_requests_post.call_args
        assert call_args[0][0] == config.discord_webhook_url
        assert "json" in call_args[1]

        payload = call_args[1]["json"]
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1

        embed = payload["embeds"][0]
        assert embed["title"] == "ASX Market Scan Complete"
        assert "1 new candidates found" in embed["description"]
        assert embed["color"] == 0x00FF00

    @patch("skim.core.bot.ASXAnnouncementScanner")
    @patch("skim.core.bot.IBKRGapScanner")
    @patch("skim.core.bot.Database")
    @patch("skim.notifications.discord.requests.post")
    def test_scan_with_discord_notification_no_candidates(
        self, mock_requests_post, mock_db, mock_ibkr_scanner, mock_asx_scanner
    ):
        """Test scan method with no candidates and Discord notification"""
        from skim.validation.scanners import GapScanResult

        # Setup config
        config = Config(
            ib_client_id=1,
            paper_trading=True,
            max_position_size=1000,
            max_positions=5,
            db_path="test.db",
            discord_webhook_url="https://discord.com/api/webhooks/test/webhook",
            scanner_config=ScannerConfig(
                gap_threshold=3.0,
                volume_filter=50000,
                price_filter=0.50,
                or_duration_minutes=10,
                or_poll_interval_seconds=30,
                gap_fill_tolerance=1.0,
                or_breakout_buffer=0.1,
            ),
        )

        # Setup mocks - no gap stocks found
        mock_asx_scanner.return_value.fetch_price_sensitive_tickers.return_value = set()
        mock_scan_result = GapScanResult(gap_stocks=[], new_candidates=[])
        mock_ibkr_scanner.return_value.is_connected.return_value = True
        mock_ibkr_scanner.return_value.scan_gaps_with_announcements.return_value = mock_scan_result

        # Mock successful Discord response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_requests_post.return_value = mock_response

        # Create bot and run scan
        bot = TradingBot(config)
        result = bot.scan()

        # Verify scan completed with no candidates
        assert result == 0

        # Verify Discord notification was sent
        mock_requests_post.assert_called_once()
        call_args = mock_requests_post.call_args
        payload = call_args[1]["json"]
        embed = payload["embeds"][0]
        assert "No new candidates found" in embed["description"]
        assert embed["color"] == 0xFFFF00  # Yellow

    @patch("skim.core.bot.ASXAnnouncementScanner")
    @patch("skim.core.bot.IBKRGapScanner")
    @patch("skim.core.bot.Database")
    @patch("skim.notifications.discord.requests.post")
    def test_scan_with_discord_notification_error(
        self, mock_requests_post, mock_db, mock_ibkr_scanner, mock_asx_scanner
    ):
        """Test scan method with Discord notification error"""
        from skim.validation.scanners import GapScanResult

        # Setup config
        config = Config(
            ib_client_id=1,
            paper_trading=True,
            max_position_size=1000,
            max_positions=5,
            db_path="test.db",
            discord_webhook_url="https://discord.com/api/webhooks/test/webhook",
            scanner_config=ScannerConfig(
                gap_threshold=3.0,
                volume_filter=50000,
                price_filter=0.50,
                or_duration_minutes=10,
                or_poll_interval_seconds=30,
                gap_fill_tolerance=1.0,
                or_breakout_buffer=0.1,
            ),
        )

        # Setup mocks
        mock_asx_scanner.return_value.fetch_price_sensitive_tickers.return_value = {
            "BHP",
        }

        mock_candidate = {
            "ticker": "BHP",
            "headline": "BHP announces earnings",
            "scan_date": "2025-11-21",
            "status": "watching",
            "gap_percent": 5.5,
            "price": 45.20,
        }

        mock_scan_result = GapScanResult(
            gap_stocks=[], new_candidates=[mock_candidate]
        )
        mock_ibkr_scanner.return_value.is_connected.return_value = True
        mock_ibkr_scanner.return_value.scan_gaps_with_announcements.return_value = mock_scan_result

        mock_db.return_value.get_candidate.return_value = None
        mock_db.return_value.save_candidate = Mock()

        # Mock Discord error
        mock_requests_post.side_effect = Exception("Discord error")

        # Create bot and run scan
        bot = TradingBot(config)
        result = bot.scan()

        # Verify scan completed despite Discord error
        assert result == 1
        mock_requests_post.assert_called_once()

    @patch("skim.core.bot.ASXAnnouncementScanner")
    @patch("skim.core.bot.IBKRGapScanner")
    @patch("skim.core.bot.Database")
    def test_scan_without_discord_webhook(
        self, mock_db, mock_ibkr_scanner, mock_asx_scanner
    ):
        """Test scan method without Discord webhook configured"""
        from skim.validation.scanners import GapScanResult

        # Setup config without Discord webhook
        config = Config(
            ib_client_id=1,
            paper_trading=True,
            max_position_size=1000,
            max_positions=5,
            db_path="test.db",
            discord_webhook_url=None,
            scanner_config=ScannerConfig(
                gap_threshold=3.0,
                volume_filter=50000,
                price_filter=0.50,
                or_duration_minutes=10,
                or_poll_interval_seconds=30,
                gap_fill_tolerance=1.0,
                or_breakout_buffer=0.1,
            ),
        )

        # Setup mocks
        mock_asx_scanner.return_value.fetch_price_sensitive_tickers.return_value = {
            "BHP",
        }

        mock_candidate = {
            "ticker": "BHP",
            "headline": "BHP announces earnings",
            "scan_date": "2025-11-21",
            "status": "watching",
            "gap_percent": 5.5,
            "price": 45.20,
        }

        mock_scan_result = GapScanResult(
            gap_stocks=[], new_candidates=[mock_candidate]
        )
        mock_ibkr_scanner.return_value.is_connected.return_value = True
        mock_ibkr_scanner.return_value.scan_gaps_with_announcements.return_value = mock_scan_result

        mock_db.return_value.get_candidate.return_value = None
        mock_db.return_value.save_candidate = Mock()

        # Create bot and run scan
        bot = TradingBot(config)
        result = bot.scan()

        # Verify scan completed without Discord notification
        assert result == 1

        # Verify Discord notifier was created with None URL
        assert bot.discord_notifier.webhook_url is None
