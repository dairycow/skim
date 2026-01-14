"""Tests for CLI and CommandDispatcher"""

from datetime import date
from unittest.mock import AsyncMock, Mock

import pytest

from skim.application.commands.base import (
    ManageCommand,
    PurgeCommand,
    ScanCommand,
    StatusCommand,
    TradeCommand,
)
from skim.application.services.command_dispatcher import CommandDispatcher


@pytest.fixture
def mock_trading_bot():
    """Create a mock TradingBot for testing the dispatcher."""
    bot = Mock()
    bot.scan = AsyncMock(return_value=5)
    bot.trade = AsyncMock(return_value=2)
    bot.manage = AsyncMock(return_value=1)
    bot.status = AsyncMock(return_value=True)
    bot.purge_candidates = AsyncMock(return_value=10)
    bot.ib_client.is_connected.return_value = False
    return bot


class TestCommandDispatcher:
    """Tests for CommandDispatcher."""

    @pytest.mark.asyncio
    async def test_dispatch_unknown_command_returns_error(
        self, mock_trading_bot
    ):
        """dispatch should return 1 for unknown commands."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher.dispatch(["skim", "unknown_command"])
        assert result == 1

    @pytest.mark.asyncio
    async def test_dispatch_no_args_returns_error(self, mock_trading_bot):
        """dispatch should return 1 when no command is provided."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher.dispatch(["skim"])
        assert result == 1

    @pytest.mark.asyncio
    async def test_scan_command_calls_bot_scan(self, mock_trading_bot):
        """scan command should call bot.scan with default strategy."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher._handle_scan(["skim", "scan"])
        mock_trading_bot.scan.assert_awaited_once_with("orh_breakout")
        assert result == 0

    @pytest.mark.asyncio
    async def test_scan_command_with_strategy(self, mock_trading_bot):
        """scan command should pass strategy argument to bot.scan."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher._handle_scan(
            ["skim", "scan", "custom_strategy"]
        )
        mock_trading_bot.scan.assert_awaited_once_with("custom_strategy")
        assert result == 0

    @pytest.mark.asyncio
    async def test_trade_command_calls_bot_trade(self, mock_trading_bot):
        """trade command should call bot.trade with default strategy."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher._handle_trade(["skim", "trade"])
        mock_trading_bot.trade.assert_awaited_once_with("orh_breakout")
        assert result == 0

    @pytest.mark.asyncio
    async def test_manage_command_calls_bot_manage(self, mock_trading_bot):
        """manage command should call bot.manage with default strategy."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher._handle_manage(["skim", "manage"])
        mock_trading_bot.manage.assert_awaited_once_with("orh_breakout")
        assert result == 0

    @pytest.mark.asyncio
    async def test_status_command_calls_bot_status(self, mock_trading_bot):
        """status command should call bot.status with default strategy."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher._handle_status(["skim", "status"])
        mock_trading_bot.status.assert_awaited_once_with("orh_breakout")
        assert result == 0

    @pytest.mark.asyncio
    async def test_purge_command_calls_bot_purge(self, mock_trading_bot):
        """purge command should call bot.purge_candidates with no cutoff."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher._handle_purge(["skim", "purge_candidates"])
        mock_trading_bot.purge_candidates.assert_awaited_once_with(None)
        assert result == 0

    @pytest.mark.asyncio
    async def test_purge_command_with_cutoff(self, mock_trading_bot):
        """purge command should pass cutoff date to bot.purge_candidates."""
        dispatcher = CommandDispatcher(mock_trading_bot)
        result = await dispatcher._handle_purge(
            ["skim", "purge_candidates", "2024-01-15"]
        )
        mock_trading_bot.purge_candidates.assert_awaited_once_with(
            date(2024, 1, 15)
        )
        assert result == 0


class TestCommandClasses:
    """Tests for command dataclasses."""

    def test_scan_command_defaults(self):
        """ScanCommand should have default strategy."""
        cmd = ScanCommand(name="scan")
        assert cmd.strategy is None

    def test_scan_command_with_strategy(self):
        """ScanCommand should accept strategy."""
        cmd = ScanCommand(name="scan", strategy="custom")
        assert cmd.strategy == "custom"

    def test_trade_command_defaults(self):
        """TradeCommand should have default strategy."""
        cmd = TradeCommand(name="trade")
        assert cmd.strategy is None

    def test_manage_command_defaults(self):
        """ManageCommand should have default strategy."""
        cmd = ManageCommand(name="manage")
        assert cmd.strategy is None

    def test_purge_command_defaults(self):
        """PurgeCommand should have default cutoff_date."""
        cmd = PurgeCommand(name="purge")
        assert cmd.cutoff_date is None

    def test_status_command_defaults(self):
        """StatusCommand should have default strategy."""
        cmd = StatusCommand(name="status")
        assert cmd.strategy is None
