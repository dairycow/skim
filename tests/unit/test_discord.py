"""Unit tests for Discord notification module"""

from unittest.mock import Mock

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
            {"ticker": "BHP", "gap_percent": 5.5, "price": 45.20},
            {"ticker": "RIO", "gap_percent": 4.2, "price": 120.50},
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

    def test_send_scan_results_network_error(self, mocker):
        """Test scan results notification with network error"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        mocker.patch(
            "requests.post",
            side_effect=requests.exceptions.ConnectionError("Network error"),
        )

        result = notifier.send_scan_results(candidates_found=1, candidates=[])

        assert result is False

    def test_send_scan_results_http_error(self, mocker):
        """Test scan results notification with HTTP error"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("500 Server Error")
        )

        mocker.patch("requests.post", return_value=mock_response)

        result = notifier.send_scan_results(candidates_found=1, candidates=[])

        assert result is False

    def test_send_scan_results_timeout(self, mocker):
        """Test scan results notification with timeout"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        mocker.patch(
            "requests.post", side_effect=requests.exceptions.Timeout("Timeout")
        )

        result = notifier.send_scan_results(candidates_found=1, candidates=[])

        assert result is False

    def test_build_embed_with_candidates(self):
        """Test embed building with candidate data"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        candidates = [
            {"ticker": "BHP", "gap_percent": 5.5, "price": 45.20},
            {"ticker": "RIO", "gap_percent": 4.2, "price": 120.50},
        ]

        embed = notifier._build_embed(candidates_found=2, candidates=candidates)

        assert embed["title"] == "ASX Market Scan Complete"
        assert "2 new candidates found" in embed["description"]
        assert embed["color"] == 0x00FF00  # Green colour

        # Check fields contain candidate information
        assert "fields" in embed
        assert len(embed["fields"]) >= 1

        # Find candidates field
        candidates_field = None
        for field in embed["fields"]:
            if field["name"] == "New Candidates":
                candidates_field = field
                break

        assert candidates_field is not None
        assert "BHP" in candidates_field["value"]
        assert "RIO" in candidates_field["value"]
        assert "5.5%" in candidates_field["value"]
        assert "4.2%" in candidates_field["value"]

    def test_build_embed_no_candidates(self):
        """Test embed building with no candidates"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        embed = notifier._build_embed(candidates_found=0, candidates=[])

        assert embed["title"] == "ASX Market Scan Complete"
        assert "No new candidates found" in embed["description"]
        assert embed["color"] == 0xFFFF00  # Yellow colour

    def test_build_embed_error_case(self):
        """Test embed building for error case"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        embed = notifier._build_embed(candidates_found=-1, candidates=[])

        assert embed["title"] == "ASX Market Scan Error"
        assert embed["color"] == 0xFF0000  # Red colour

    def test_format_candidate_list(self):
        """Test candidate list formatting"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        candidates = [
            {"ticker": "BHP", "gap_percent": 5.5, "price": 45.20},
            {"ticker": "RIO", "gap_percent": 4.2, "price": 120.50},
        ]

        formatted = notifier._format_candidate_list(candidates)

        assert "• BHP" in formatted
        assert "• RIO" in formatted
        assert "5.5%" in formatted
        assert "4.2%" in formatted
        assert "$45.20" in formatted
        assert "$120.50" in formatted

    def test_format_candidate_list_empty(self):
        """Test empty candidate list formatting"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        formatted = notifier._format_candidate_list([])

        assert formatted == "None"

    def test_format_candidate_list_missing_data(self):
        """Test candidate list formatting with missing data"""
        webhook_url = "https://discord.com/api/webhooks/test/webhook"
        notifier = DiscordNotifier(webhook_url)

        candidates = [
            {"ticker": "BHP"},  # Missing gap_percent and price
            {"ticker": "RIO", "gap_percent": 4.2},  # Missing price
        ]

        formatted = notifier._format_candidate_list(candidates)

        assert "• BHP" in formatted
        assert "• RIO" in formatted
        assert "4.2%" in formatted
        assert "N/A" in formatted  # Should show N/A for missing values
