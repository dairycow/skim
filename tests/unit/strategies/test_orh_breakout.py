"""Tests for ORH Breakout Strategy"""

from unittest.mock import AsyncMock, Mock

import pytest

from skim.strategies.orh_breakout import ORHBreakoutStrategy


@pytest.fixture
def mock_strategy():
    """Create a mock ORHBreakoutStrategy for testing."""
    strategy = ORHBreakoutStrategy(
        ib_client=Mock(),
        scanner_service=Mock(),
        market_data_service=Mock(),
        order_service=Mock(),
        db=Mock(),
        orh_repo=Mock(),
        discord=Mock(),
        config=Mock(),
    )
    yield strategy


@pytest.mark.asyncio
class TestORHBreakoutStrategyAlert:
    """Tests for alert method."""

    async def test_alert_sends_tradeable_candidates(self, mock_strategy):
        """alert() should query DB and send Discord notification."""
        mock_tradeable = [
            Mock(
                ticker="BHP",
                gap_percent=5.0,
                headline="Results",
                or_high=47.80,
                or_low=45.90,
            ),
            Mock(
                ticker="RIO",
                gap_percent=4.2,
                headline="Halt",
                or_high=92.30,
                or_low=90.10,
            ),
        ]
        mock_strategy.orh_repo.get_tradeable_candidates = Mock(
            return_value=mock_tradeable
        )
        mock_strategy.discord.send_tradeable_candidates = Mock()

        count = await mock_strategy.alert()

        assert count == 2
        mock_strategy.orh_repo.get_tradeable_candidates.assert_called_once()
        mock_strategy.discord.send_tradeable_candidates.assert_called_once_with(
            2,
            [
                {
                    "ticker": "BHP",
                    "gap_percent": 5.0,
                    "headline": "Results",
                    "or_high": 47.80,
                    "or_low": 45.90,
                },
                {
                    "ticker": "RIO",
                    "gap_percent": 4.2,
                    "headline": "Halt",
                    "or_high": 92.30,
                    "or_low": 90.10,
                },
            ],
        )

    async def test_alert_returns_zero_when_no_candidates(self, mock_strategy):
        """alert() should return 0 when no tradeable candidates exist."""
        mock_strategy.orh_repo.get_tradeable_candidates = Mock(return_value=[])

        count = await mock_strategy.alert()

        assert count == 0
        mock_strategy.orh_repo.get_tradeable_candidates.assert_called_once()
        mock_strategy.discord.send_tradeable_candidates.assert_not_called()

    async def test_alert_handles_database_error(self, mock_strategy):
        """alert() should return 0 and log error when DB query fails."""
        mock_strategy.orh_repo.get_tradeable_candidates = Mock(
            side_effect=Exception("DB error")
        )

        count = await mock_strategy.alert()

        assert count == 0
        mock_strategy.discord.send_tradeable_candidates.assert_not_called()


@pytest.mark.asyncio
class TestORHBreakoutStrategyScanNoDiscord:
    """Tests verifying scan methods do not send Discord notifications."""

    async def test_scan_gaps_no_discord_calls(self, mock_strategy):
        """scan_gaps() should NOT send Discord notifications."""
        mock_candidates = [Mock(ticker="BHP", gap_percent=5.0)]
        mock_strategy.gap_scanner.find_gap_candidates = AsyncMock(
            return_value=mock_candidates
        )

        await mock_strategy.scan_gaps()

        mock_strategy.discord.send_tradeable_candidates.assert_not_called()

    async def test_scan_news_no_discord_calls(self, mock_strategy):
        """scan_news() should NOT send Discord notifications."""
        mock_candidates = [Mock(ticker="BHP", headline="Results")]
        mock_strategy.news_scanner.find_news_candidates = AsyncMock(
            return_value=mock_candidates
        )

        await mock_strategy.scan_news()

        mock_strategy.discord.send_tradeable_candidates.assert_not_called()
