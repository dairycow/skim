"""Tests for ORH Breakout Strategy - Event-driven architecture"""

from unittest.mock import AsyncMock, Mock, patch

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

    mock_context = Mock()
    mock_context.config = mock_config
    mock_context.repository = mock_repo
    mock_context.event_bus = AsyncMock()
    mock_context.event_bus.start = AsyncMock()
    mock_context.event_bus.stop = AsyncMock()
    mock_context.event_bus.publish = AsyncMock()
    mock_context.event_bus.subscribe = Mock()
    mock_context.notifier = Mock()
    mock_context.market_data = AsyncMock()
    mock_context.order_service = AsyncMock()
    mock_context.scanner_service = Mock()
    mock_context.database = Mock()
    mock_context.historical_service = None
    mock_context.connection_manager = Mock()
    mock_context.connection_manager.is_connected = Mock(return_value=True)

    strategy = ORHBreakoutStrategy(mock_context)
    yield strategy


@pytest.mark.asyncio
class TestORHBreakoutStrategyAlert:
    """Tests for alert method."""

    async def test_alert_sends_tradeable_candidates(self, mock_strategy):
        """alert() should query repository via alerter."""
        mock_alertable = [
            Mock(
                ticker=Mock(symbol="BHP"),
                gap_percent=5.0,
                headline="Results",
            ),
            Mock(
                ticker=Mock(symbol="RIO"),
                gap_percent=4.2,
                headline="Halt",
            ),
        ]

        with patch.object(
            mock_strategy.repo, "get_alertable", return_value=mock_alertable
        ):
            count = await mock_strategy.alert()

            assert count == 2
            mock_strategy.repo.get_alertable.assert_called_once()

    async def test_alert_returns_zero_when_no_candidates(self, mock_strategy):
        """alert() should return 0 when no alertable candidates exist."""
        with patch.object(mock_strategy.repo, "get_alertable", return_value=[]):
            with patch.object(
                mock_strategy.event_bus, "publish", new_callable=AsyncMock
            ) as mock_publish:
                count = await mock_strategy.alert()

                assert count == 0
                mock_strategy.repo.get_alertable.assert_called_once()
                mock_publish.assert_not_called()

    async def test_alert_handles_repository_error(self, mock_strategy):
        """alert() should return 0 and log error when repository query fails."""
        with patch.object(
            mock_strategy.repo,
            "get_alertable",
            side_effect=Exception("DB error"),
        ):
            count = await mock_strategy.alert()

            assert count == 0


@pytest.mark.asyncio
class TestORHBreakoutStrategyScan:
    """Tests for scan method."""

    async def test_scan_runs_all_scanners(self, mock_strategy):
        """scan() should run all scanners via orchestrator."""
        with patch.object(
            mock_strategy.scanner_orchestrator,
            "run_all",
            new_callable=AsyncMock,
        ) as mock_run:
            mock_run.return_value = {"gap": 5, "news": 3}

            count = await mock_strategy.scan()

            assert count == 8
            mock_run.assert_called_once()

    async def test_scan_returns_zero_on_error(self, mock_strategy):
        """scan() should return 0 when scan fails."""
        with patch.object(
            mock_strategy.scanner_orchestrator,
            "run_all",
            new_callable=AsyncMock,
            side_effect=Exception("Scan failed"),
        ):
            count = await mock_strategy.scan()

            assert count == 0


@pytest.mark.asyncio
class TestORHBreakoutStrategyTrade:
    """Tests for trade method."""

    async def test_trade_with_no_candidates(self, mock_strategy):
        """trade() should return 0 when no candidates."""
        with patch.object(mock_strategy.repo, "get_tradeable", return_value=[]):
            count = await mock_strategy.trade()

            assert count == 0

    async def test_trade_filters_candidates(self, mock_strategy):
        """trade() should apply filter chain."""
        candidates = [Mock(ticker=Mock(symbol="BHP"))]

        with patch.object(
            mock_strategy.repo, "get_tradeable", return_value=candidates
        ), patch.object(
            mock_strategy.filter_chain, "apply", return_value=[]
        ):
            count = await mock_strategy.trade()

            assert count == 0


@pytest.mark.asyncio
class TestORHBreakoutStrategyManage:
    """Tests for manage method."""

    async def test_manage_with_positions(self, mock_strategy):
        """manage() should check stops and execute exits."""
        positions = [Mock(ticker=Mock(symbol="BHP"), quantity=100)]

        with patch.object(
            mock_strategy.db, "get_open_positions", return_value=positions
        ), patch.object(
            mock_strategy.monitor, "check_stops", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = positions

            with patch.object(
                mock_strategy.trader,
                "execute_stops",
                new_callable=AsyncMock,
            ) as mock_execute:
                mock_execute.return_value = [Mock()]

                count = await mock_strategy.manage()

                assert count == 1

    async def test_manage_with_no_positions(self, mock_strategy):
        """manage() should return 0 when no positions."""
        with patch.object(
            mock_strategy.db, "get_open_positions", return_value=[]
        ):
            count = await mock_strategy.manage()

            assert count == 0


@pytest.mark.asyncio
class TestORHBreakoutStrategyTrackRanges:
    """Tests for track_ranges method."""

    async def test_track_ranges_updates_candidates(self, mock_strategy):
        """track_ranges() should update opening ranges."""
        with patch.object(
            mock_strategy.range_tracker,
            "track_opening_ranges",
            new_callable=AsyncMock,
            return_value=5,
        ) as mock_track:
            count = await mock_strategy.track_ranges()

            assert count == 5
            mock_track.assert_called_once()

    async def test_track_ranges_handles_error(self, mock_strategy):
        """track_ranges() should return 0 on error."""
        with patch.object(
            mock_strategy.range_tracker,
            "track_opening_ranges",
            new_callable=AsyncMock,
            side_effect=Exception("Error"),
        ):
            count = await mock_strategy.track_ranges()

            assert count == 0


@pytest.mark.asyncio
class TestORHBreakoutStrategyPurge:
    """Tests for purge_candidates method."""

    async def test_purge_candidates_deletes_all(self, mock_strategy):
        """purge_candidates() should delete all candidates."""
        with patch.object(
            mock_strategy.db, "purge_candidates", return_value=10
        ):
            count = await mock_strategy.purge_candidates()

            assert count == 10

    async def test_purge_candidates_with_date(self, mock_strategy):
        """purge_candidates() should accept date filter."""
        from datetime import date

        with patch.object(mock_strategy.db, "purge_candidates", return_value=5):
            count = await mock_strategy.purge_candidates(
                only_before_utc_date=date(2025, 1, 1)
            )

            assert count == 5
            mock_strategy.db.purge_candidates.assert_called_once()
