"""Tests for decoupled scan method - database and Discord independent"""

from unittest.mock import Mock, patch

import pytest

from skim.core.bot import TradingBot
from skim.scanners.ibkr_gap_scanner import GapStock


class TestScanMethodDecoupling:
    """Test that scan method has decoupled database and Discord operations"""

    @pytest.fixture
    def bot(self, mock_bot_config):
        """Create TradingBot instance with mocked dependencies"""
        with (
            patch("skim.core.bot.Database"),
            patch("skim.core.bot.IBKRClient"),
            patch("skim.core.bot.DiscordNotifier"),
            patch("skim.core.bot.IBKRGapScanner"),
            patch("skim.core.bot.ASXAnnouncementScanner"),
        ):
            return TradingBot(mock_bot_config)

    @pytest.fixture
    def mock_gap_stocks(self):
        """Create mock gap stocks data"""
        return [
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                conid=8644,
            ),
            GapStock(
                ticker="RIO",
                gap_percent=4.2,
                conid=8653,
            ),
        ]

    def test_scan_discord_still_called_when_db_write_fails(
        self, bot, mock_gap_stocks
    ):
        """Test that Discord notification is still called even if database write fails

        Currently, if database persistence fails for any candidate, the entire loop
        stops and Discord never gets notified. This test verifies that after
        refactoring, Discord notification should happen independently.
        """
        # Setup mocks
        bot.asx_scanner.fetch_price_sensitive_tickers.return_value = {
            "BHP",
            "RIO",
        }

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks
        mock_scanner.get_market_data.return_value = Mock(last_price=50.0)

        # Make database write fail for second candidate
        save_call_count = [0]

        def save_candidate_side_effect(candidate):
            save_call_count[0] += 1
            if save_call_count[0] == 2:
                raise Exception("Database write failed")

        bot.db.save_candidate = Mock(side_effect=save_candidate_side_effect)
        bot.discord_notifier.send_scan_results = Mock()

        result = bot.scan()

        # Verify scan completes despite database error
        assert result == 2  # Should still return count of candidates found
        # Verify Discord notification was called (even though DB had an error)
        bot.discord_notifier.send_scan_results.assert_called_once()

    def test_scan_db_writes_still_happen_when_discord_fails(
        self, bot, mock_gap_stocks
    ):
        """Test that database writes still happen even if Discord notification fails

        Verifies that if Discord notification fails, database persistence still
        happens for all candidates.
        """
        # Setup mocks
        bot.asx_scanner.fetch_price_sensitive_tickers.return_value = {
            "BHP",
            "RIO",
        }

        mock_scanner = bot.ibkr_scanner
        mock_scanner.is_connected.return_value = True
        mock_scanner.scan_for_gaps.return_value = mock_gap_stocks
        mock_scanner.get_market_data.return_value = Mock(last_price=50.0)

        bot.db.save_candidate = Mock()
        # Make Discord notification fail
        bot.discord_notifier.send_scan_results = Mock(
            side_effect=Exception("Discord API error")
        )

        result = bot.scan()

        # Verify scan completes despite Discord error
        assert result == 2  # Should still return count of candidates found
        # Verify database save was still called (2 times for 2 candidates)
        assert bot.db.save_candidate.call_count == 2
