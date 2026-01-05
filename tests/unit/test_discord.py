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

    def test_send_tradeable_candidates_success(self, mocker):
        """Test successful tradeable candidates notification"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post = mocker.patch("requests.post", return_value=mock_response)

        candidates = [
            {
                "ticker": "BHP",
                "gap_percent": 5.5,
                "headline": "Results Released",
                "or_high": 47.80,
                "or_low": 45.90,
            },
            {
                "ticker": "RIO",
                "gap_percent": 4.2,
                "headline": "Trading Halt",
                "or_high": 92.30,
                "or_low": 90.10,
            },
        ]

        result = notifier.send_tradeable_candidates(
            candidates_found=2, candidates=candidates
        )

        assert result is True
        mock_post.assert_called_once()

        call_args = mock_post.call_args
        assert call_args[0][0] == webhook_url
        assert "json" in call_args[1]

        payload = call_args[1]["json"]
        assert "embeds" in payload
        assert len(payload["embeds"]) == 1

        embed = payload["embeds"][0]
        assert embed["title"] == "Tradeable Candidates Ready"
        assert "2 tradeable candidates" in embed["description"]
        assert embed["color"] == 0x00FF00

    def test_send_tradeable_candidates_no_webhook(self):
        """Test tradeable candidates notification without webhook URL"""
        notifier = DiscordNotifier(None)

        result = notifier.send_tradeable_candidates(
            candidates_found=2, candidates=[]
        )

        assert result is False

    def test_send_tradeable_candidates_empty(self, mocker):
        """Test empty tradeable candidates notification"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_post = mocker.patch("requests.post", return_value=mock_response)

        result = notifier.send_tradeable_candidates(
            candidates_found=0, candidates=[]
        )

        assert result is True
        payload = mock_post.call_args[1]["json"]
        embed = payload["embeds"][0]
        assert embed["description"] == "No tradeable candidates found"
        assert embed["color"] == 0xFFFF00

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
    def test_send_tradeable_candidates_error_handling(
        self, mocker, exception_type, exception_msg, test_description
    ):
        """Test tradeable candidates notification handles various errors (parameterized)"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

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

        result = notifier.send_tradeable_candidates(
            candidates_found=1, candidates=[]
        )

        assert result is False

    def test_format_tradeable_candidate_list(self):
        """Test tradeable candidate list formatting"""
        from skim.notifications.discord import _format_tradeable_candidate_list

        candidates = [
            {
                "ticker": "BHP",
                "gap_percent": 5.5,
                "headline": "Results Released",
                "or_high": 47.80,
                "or_low": 45.90,
            },
            {
                "ticker": "RIO",
                "gap_percent": 4.2,
                "headline": "Trading Halt Announcement",
                "or_high": 92.30,
                "or_low": 90.10,
            },
        ]

        formatted = _format_tradeable_candidate_list(candidates)

        assert "**BHP**" in formatted
        assert "**RIO**" in formatted
        assert "5.5%" in formatted
        assert "4.2%" in formatted
        assert "47.80" in formatted
        assert "92.30" in formatted
        assert "Results Release" in formatted
        assert "Trading Halt Announce" in formatted

    def test_format_tradeable_candidate_list_empty(self):
        """Test empty tradeable candidate list formatting"""
        from skim.notifications.discord import _format_tradeable_candidate_list

        formatted = _format_tradeable_candidate_list([])

        assert formatted == "None"

    def test_format_tradeable_candidate_list_missing_data(self):
        """Test tradeable candidate list formatting with missing data"""
        from skim.notifications.discord import _format_tradeable_candidate_list

        candidates = [
            {
                "ticker": "BHP",
                "gap_percent": 5.5,
                "headline": None,
                "or_high": 47.80,
                "or_low": 45.90,
            },
            {
                "ticker": "RIO",
                "gap_percent": None,
                "headline": "Results",
                "or_high": None,
                "or_low": None,
            },
        ]

        formatted = _format_tradeable_candidate_list(candidates)

        assert "**BHP**" in formatted
        assert "**RIO**" in formatted
        assert "No headline" in formatted
        assert "Gap: N/A" in formatted
        assert "ORH: N/A" in formatted

    def test_format_tradeable_candidate_list_truncation(self):
        """Test tradeable candidate list truncation at 1024 chars"""
        from skim.notifications.discord import _format_tradeable_candidate_list

        candidates = [
            {
                "ticker": f"STK{i:03d}",
                "gap_percent": 1.0,
                "headline": "A" * 100,
                "or_high": 10.0,
                "or_low": 9.0,
            }
            for i in range(20)
        ]

        formatted = _format_tradeable_candidate_list(candidates)

        assert len(formatted) <= 1024
        assert "... (truncated)" in formatted

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
