"""Tests for ORH Breakout Strategy"""

from unittest.mock import AsyncMock, Mock

import pytest

from skim.trading.strategies.orh_breakout import ORHBreakoutStrategy


@pytest.fixture
def mock_strategy():
    """Create a mock ORHBreakoutStrategy for testing."""
    mock_config = Mock()
    mock_config.scanner_config.gap_threshold = 9.0
    mock_config.historical_config.enable_filtering = False

    mock_repo = Mock()
    mock_repo.STRATEGY_NAME = "orh_breakout"

    context = Mock()
    context.config = mock_config
    context.repository = mock_repo

    strategy = ORHBreakoutStrategy(context)
    yield strategy


@pytest.mark.asyncio
class TestORHBreakoutStrategyAlert:
    """Tests for alert method."""

    async def test_alert_sends_tradeable_candidates(self, mock_strategy):
        """alert() should query DB and send Discord notification."""
        mock_alertable = [
            Mock(
                ticker="BHP",
                gap_percent=5.0,
                headline="Results",
            ),
            Mock(
                ticker="RIO",
                gap_percent=4.2,
                headline="Halt",
            ),
        ]
        mock_strategy.ctx.repository.get_alertable_candidates = Mock(
            return_value=mock_alertable
        )
        mock_strategy.ctx.notifier.send_tradeable_candidates = Mock()

        count = await mock_strategy.alert()

        assert count == 2
        mock_strategy.ctx.repository.get_alertable_candidates.assert_called_once()
        mock_strategy.ctx.notifier.send_tradeable_candidates.assert_called_once_with(
            2,
            [
                {
                    "ticker": "BHP",
                    "gap_percent": 5.0,
                    "headline": "Results",
                },
                {
                    "ticker": "RIO",
                    "gap_percent": 4.2,
                    "headline": "Halt",
                },
            ],
        )

    async def test_alert_returns_zero_when_no_candidates(self, mock_strategy):
        """alert() should return 0 when no alertable candidates exist."""
        mock_strategy.ctx.repository.get_alertable_candidates = Mock(
            return_value=[]
        )

        count = await mock_strategy.alert()

        assert count == 0
        mock_strategy.ctx.repository.get_alertable_candidates.assert_called_once()
        mock_strategy.ctx.notifier.send_tradeable_candidates.assert_not_called()

    async def test_alert_handles_database_error(self, mock_strategy):
        """alert() should return 0 and log error when DB query fails."""
        mock_strategy.ctx.repository.get_alertable_candidates = Mock(
            side_effect=Exception("DB error")
        )

        count = await mock_strategy.alert()

        assert count == 0
        mock_strategy.ctx.notifier.send_tradeable_candidates.assert_not_called()


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

        mock_strategy.ctx.notifier.send_tradeable_candidates.assert_not_called()

    async def test_scan_news_no_discord_calls(self, mock_strategy):
        """scan_news() should NOT send Discord notifications."""
        mock_candidates = [Mock(ticker="BHP", headline="Results")]
        mock_strategy.news_scanner.find_news_candidates = AsyncMock(
            return_value=mock_candidates
        )

        await mock_strategy.scan_news()

        mock_strategy.ctx.notifier.send_tradeable_candidates.assert_not_called()
