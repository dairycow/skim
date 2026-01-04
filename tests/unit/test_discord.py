"""Unit tests for Discord notification module"""

from unittest.mock import Mock

import pytest
import requests

from skim.notifications.discord import DiscordNotifier


class TestDiscordNotifier:
    """Tests for DiscordNotifier"""

    def test_init_with_webhook_url(self):
        """Test initialisation with webhook URL"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        assert notifier.webhook_url == webhook_url

    def test_init_without_webhook_url(self):
        """Test initialisation without webhook URL"""
        notifier = DiscordNotifier(None)

        assert notifier.webhook_url is None

    def test_send_scan_results_success(self, mocker):
        """Test successful scan results notification"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        mock_post = mocker.patch("requests.post", return_value=mock_response)

        candidates = [
            {
                "ticker": "BHP",
                "gap_percent": 5.5,
                "headline": "Trading Halt",
            },
            {
                "ticker": "RIO",
                "gap_percent": 4.2,
                "headline": "Results Released",
            },
        ]

        result = notifier.send_scan_results(
            candidates_found=2, candidates=candidates
        )

        assert result is True
        mock_post.assert_called_once()

        # Verify the call arguments
        call_args = mock_post.call_args
        assert call_args[0][0] == webhook_url
        assert "json" in call_args[1]

        payload = call_args[1]["json"]
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1

        embed = payload["embeds"][0]
        assert embed["title"] == "ASX Market Scan Complete"
        assert "2 new candidates found" in embed["description"]
        assert embed["color"] == 0x00FF00  # Green colour

    def test_send_scan_results_no_webhook(self):
        """Test scan results notification without webhook URL"""
        notifier = DiscordNotifier(None)

        result = notifier.send_scan_results(candidates_found=2, candidates=[])

        assert result is False

    @pytest.mark.parametrize(
        "exception_type,exception_msg,test_description",
        [
            (
                requests.exceptions.ConnectionError,
                "Network error",
                "network error",
            ),
            (
                requests.exceptions.HTTPError,
                "500 Server Error",
                "HTTP error",
            ),
            (requests.exceptions.Timeout, "Timeout", "timeout"),
        ],
    )
    def test_send_scan_results_error_handling(
        self, mocker, exception_type, exception_msg, test_description
    ):
        """Test scan results notification handles various errors (parameterized)"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        # For HTTPError, we need to mock the response object differently
        if exception_type == requests.exceptions.HTTPError:
            mock_response = Mock()
            mock_response.raise_for_status.side_effect = exception_type(
                exception_msg
            )
            mocker.patch("requests.post", return_value=mock_response)
        else:
            mocker.patch(
                "requests.post", side_effect=exception_type(exception_msg)
            )

        result = notifier.send_scan_results(candidates_found=1, candidates=[])

        assert result is False

    def test_format_candidate_list(self):
        """Test candidate list formatting with headlines"""
        from skim.notifications.discord import _format_candidate_list

        candidates = [
            {
                "ticker": "BHP",
                "gap_percent": 5.5,
                "headline": "Trading Halt Announcement",
            },
            {
                "ticker": "RIO",
                "gap_percent": 4.2,
                "headline": "Quarterly Results Released",
            },
        ]

        formatted = _format_candidate_list(candidates)

        assert "**BHP**" in formatted
        assert "**RIO**" in formatted
        assert "5.5%" in formatted
        assert "4.2%" in formatted
        assert "Trading Halt Announcement" in formatted
        assert "Quarterly Results Released" in formatted

    def test_format_candidate_list_empty(self):
        """Test empty candidate list formatting"""
        from skim.notifications.discord import _format_candidate_list

        formatted = _format_candidate_list([])

        assert formatted == "None"

    def test_format_candidate_list_missing_data(self):
        """Test candidate list formatting with missing headline"""
        from skim.notifications.discord import _format_candidate_list

        candidates = [
            {"ticker": "BHP", "gap_percent": 5.5, "headline": None},
            {"ticker": "RIO", "gap_percent": 4.2},  # Missing headline key
        ]

        formatted = _format_candidate_list(candidates)

        assert "**BHP**" in formatted
        assert "**RIO**" in formatted
        assert "5.5%" in formatted
        assert "4.2%" in formatted
        assert (
            "No announcement" in formatted
        )  # Should show fallback for missing headline

    def test_send_trade_notification_success(self, mocker):
        """Test successful trade notification."""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post = mocker.patch("requests.post", return_value=mock_response)

        result = notifier.send_trade_notification(
            action="BUY", ticker="BHP", quantity=100, price=10.5, pnl=None
        )

        assert result is True
        mock_post.assert_called_once()
        payload = mock_post.call_args[1]["json"]
        embed = payload["embeds"][0]
        assert embed["title"] == "Trade Executed"
        assert embed["color"] == 0x00FF00
        assert any(field["name"] == "PnL" for field in embed["fields"]) is False

    def test_send_trade_notification_no_webhook(self):
        """Test trade notification skipped without webhook URL."""
        notifier = DiscordNotifier(None)

        result = notifier.send_trade_notification(
            action="SELL", ticker="RIO", quantity=50, price=9.5, pnl=-25.0
        )

        assert result is False
