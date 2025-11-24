"""Tests for TradingBot orchestrator using async services"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from skim.core.bot import TradingBot
from skim.core.config import Config, ScannerConfig
from skim.data.models import Candidate, Position


@pytest.fixture
def mock_bot_config():
    """Mock configuration for the TradingBot."""
    return Config(
        ib_client_id=1,
        discord_webhook_url="http://mock.discord.com",
        scanner_config=ScannerConfig(
            gap_threshold=3.0,
            volume_filter=50000,
            price_filter=0.50,
            or_duration_minutes=10,
            or_poll_interval_seconds=30,
            gap_fill_tolerance=1.0,
            or_breakout_buffer=0.1,
        ),
        db_path=":memory:",
    )


@pytest.fixture
def mock_trading_bot(mock_bot_config):
    """Create a TradingBot instance with mocked dependencies."""
    with (
        patch("skim.core.bot.Database") as mock_db_class,
        patch("skim.core.bot.IBKRClient") as mock_ibkr_client_class,
        patch("skim.core.bot.IBKRMarketData") as mock_market_data_class,
        patch("skim.core.bot.IBKROrders") as mock_orders_class,
        patch("skim.core.bot.IBKRScanner") as mock_scanner_class,
        patch("skim.core.bot.Scanner") as mock_scanner_logic_class,
        patch("skim.core.bot.RangeTracker"),
        patch("skim.core.bot.Trader") as mock_trader_logic_class,
        patch("skim.core.bot.Monitor") as mock_monitor_logic_class,
        patch("skim.core.bot.DiscordNotifier") as mock_discord_notifier_class,
    ):
        # Mock instances
        mock_db = mock_db_class.return_value
        mock_ibkr_client = mock_ibkr_client_class.return_value
        mock_market_data_service = mock_market_data_class.return_value
        mock_orders_service = mock_orders_class.return_value
        mock_scanner_service = mock_scanner_class.return_value
        mock_scanner_logic = mock_scanner_logic_class.return_value
        mock_trader_logic = mock_trader_logic_class.return_value
        mock_monitor_logic = mock_monitor_logic_class.return_value
        mock_discord_notifier = mock_discord_notifier_class.return_value

        # Configure mocks for async methods
        mock_ibkr_client.is_connected.return_value = False
        mock_ibkr_client.connect = AsyncMock()
        mock_ibkr_client.disconnect = AsyncMock()
        mock_ibkr_client.get_account = Mock(return_value="DU123")

        mock_scanner_logic.find_candidates = AsyncMock(return_value=[])
        mock_trader_logic.execute_breakouts = AsyncMock(return_value=0)
        mock_trader_logic.execute_stops = AsyncMock(return_value=0)
        mock_monitor_logic.check_stops = AsyncMock(return_value=[])

        bot = TradingBot(mock_bot_config)

        # Attach mocks to the bot instance for easier access in tests
        bot.db = mock_db
        bot.ib_client = mock_ibkr_client
        bot.market_data_service = mock_market_data_service
        bot.order_service = mock_orders_service
        bot.scanner_service = mock_scanner_service
        bot.scanner = mock_scanner_logic
        bot.trader = mock_trader_logic
        bot.monitor = mock_monitor_logic
        bot.discord = mock_discord_notifier

        yield bot


@pytest.mark.asyncio
class TestTradingBot:
    """Tests for the refactored TradingBot orchestrator."""

    async def test_init_instantiates_services_and_logic(self, mock_bot_config):
        """TradingBot should wire all services and business modules."""
        with (
            patch("skim.core.bot.Database") as mock_db_class,
            patch("skim.core.bot.IBKRClient") as mock_ibkr_client_class,
            patch("skim.core.bot.IBKRMarketData") as mock_market_data_class,
            patch("skim.core.bot.IBKROrders") as mock_orders_class,
            patch("skim.core.bot.IBKRScanner") as mock_scanner_service_class,
            patch("skim.core.bot.Scanner") as mock_scanner_logic_class,
            patch("skim.core.bot.RangeTracker"),
            patch("skim.core.bot.Trader") as mock_trader_logic_class,
            patch("skim.core.bot.Monitor") as mock_monitor_logic_class,
            patch(
                "skim.core.bot.DiscordNotifier"
            ) as mock_discord_notifier_class,
        ):
            bot = TradingBot(mock_bot_config)

            mock_db_class.assert_called_once_with(mock_bot_config.db_path)
            mock_ibkr_client_class.assert_called_once_with(
                paper_trading=mock_bot_config.paper_trading
            )
            mock_market_data_class.assert_called_once_with(
                mock_ibkr_client_class.return_value
            )
            mock_orders_class.assert_called_once_with(
                mock_ibkr_client_class.return_value,
                mock_market_data_class.return_value,
            )
            mock_scanner_service_class.assert_called_once_with(
                mock_ibkr_client_class.return_value,
                mock_bot_config.scanner_config,
            )
            mock_scanner_logic_class.assert_called_once_with(
                scanner_service=mock_scanner_service_class.return_value,
                gap_threshold=mock_bot_config.scanner_config.gap_threshold,
            )
            mock_trader_logic_class.assert_called_once_with(
                mock_market_data_class.return_value,
                mock_orders_class.return_value,
                mock_db_class.return_value,
            )
            mock_monitor_logic_class.assert_called_once_with(
                mock_market_data_class.return_value
            )
            mock_discord_notifier_class.assert_called_once_with(
                mock_bot_config.discord_webhook_url
            )
            assert bot.db == mock_db_class.return_value

    async def test_ensure_connection_connects_when_not_connected(
        self, mock_trading_bot
    ):
        """_ensure_connection should connect when IBKR client is disconnected."""
        mock_trading_bot.ib_client.is_connected.return_value = False
        await mock_trading_bot._ensure_connection()
        mock_trading_bot.ib_client.connect.assert_awaited_once()

    async def test_ensure_connection_skips_when_connected(
        self, mock_trading_bot
    ):
        """_ensure_connection should not reconnect if already connected."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        await mock_trading_bot._ensure_connection()
        mock_trading_bot.ib_client.connect.assert_not_awaited()

    async def test_scan_workflow(self, mock_trading_bot):
        """scan should ensure connection, persist candidates, and notify."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_candidates = [
            Candidate(
                ticker="ABC",
                scan_date="2024-01-01",
                status="watching",
                or_high=None,
                or_low=None,
            )
        ]
        mock_trading_bot.scanner.find_candidates.return_value = mock_candidates

        result = await mock_trading_bot.scan()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.scanner.find_candidates.assert_awaited_once()
        assert mock_trading_bot.db.save_candidate.call_count == len(
            mock_candidates
        )
        mock_trading_bot.discord.send_scan_results.assert_called_once_with(
            len(mock_candidates),
            [
                {
                    "ticker": "ABC",
                    "gap_percent": None,
                    "price": None,
                }
            ],
        )
        assert result == len(mock_candidates)

    async def test_scan_handles_no_candidates(self, mock_trading_bot):
        """scan should return zero when no candidates are found."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_trading_bot.scanner.find_candidates.return_value = []

        result = await mock_trading_bot.scan()

        mock_trading_bot.scanner.find_candidates.assert_awaited_once()
        mock_trading_bot.db.save_candidate.assert_not_called()
        mock_trading_bot.discord.send_scan_results.assert_called_once_with(
            0, []
        )
        assert result == 0

    async def test_scan_handles_connection_error(self, mock_trading_bot):
        """scan should handle connection errors gracefully."""
        mock_trading_bot.ib_client.is_connected.return_value = False
        mock_trading_bot.ib_client.connect.side_effect = Exception(
            "Connection failed"
        )

        result = await mock_trading_bot.scan()

        assert result == 0
        mock_trading_bot.ib_client.connect.assert_awaited_once()
        mock_trading_bot.scanner.find_candidates.assert_not_awaited()

    async def test_trade_workflow(self, mock_trading_bot):
        """trade should retrieve watching candidates and delegate to Trader."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_candidates = [Mock(spec=Candidate)]
        mock_trading_bot.db.get_watching_candidates.return_value = (
            mock_candidates
        )
        mock_trading_bot.trader.execute_breakouts.return_value = len(
            mock_candidates
        )

        result = await mock_trading_bot.trade()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.db.get_watching_candidates.assert_called_once()
        mock_trading_bot.trader.execute_breakouts.assert_awaited_once_with(
            mock_candidates
        )
        assert result == len(mock_candidates)

    async def test_trade_handles_no_candidates(self, mock_trading_bot):
        """trade should early-exit when no watching candidates exist."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_trading_bot.db.get_watching_candidates.return_value = []

        result = await mock_trading_bot.trade()

        mock_trading_bot.db.get_watching_candidates.assert_called_once()
        mock_trading_bot.trader.execute_breakouts.assert_not_awaited()
        assert result == 0

    async def test_manage_workflow(self, mock_trading_bot):
        """manage should check stops and delegate exits."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_positions = [Mock(spec=Position)]
        mock_stops_hit = [Mock(spec=Position)]
        mock_trading_bot.db.get_open_positions.return_value = mock_positions
        mock_trading_bot.monitor.check_stops.return_value = mock_stops_hit
        mock_trading_bot.trader.execute_stops.return_value = len(mock_stops_hit)

        result = await mock_trading_bot.manage()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.db.get_open_positions.assert_called_once()
        mock_trading_bot.monitor.check_stops.assert_awaited_once_with(
            mock_positions
        )
        mock_trading_bot.trader.execute_stops.assert_awaited_once_with(
            mock_stops_hit
        )
        assert result == len(mock_stops_hit)

    async def test_manage_handles_no_positions(self, mock_trading_bot):
        """manage should early-exit when no open positions exist."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_trading_bot.db.get_open_positions.return_value = []

        result = await mock_trading_bot.manage()

        mock_trading_bot.db.get_open_positions.assert_called_once()
        mock_trading_bot.monitor.check_stops.assert_not_awaited()
        mock_trading_bot.trader.execute_stops.assert_not_awaited()
        assert result == 0

    async def test_manage_handles_no_stops_hit(self, mock_trading_bot):
        """manage should return zero when no stops are hit."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_positions = [Mock(spec=Position)]
        mock_trading_bot.db.get_open_positions.return_value = mock_positions
        mock_trading_bot.monitor.check_stops.return_value = []

        result = await mock_trading_bot.manage()

        mock_trading_bot.db.get_open_positions.assert_called_once()
        mock_trading_bot.monitor.check_stops.assert_awaited_once_with(
            mock_positions
        )
        mock_trading_bot.trader.execute_stops.assert_not_awaited()
        assert result == 0

    async def test_status_connects_and_checks_account(self, mock_trading_bot):
        """status should establish connection and return True when healthy."""
        mock_trading_bot.ib_client.is_connected.return_value = False
        mock_trading_bot.ib_client.get_account.return_value = "DU123"

        result = await mock_trading_bot.status()

        mock_trading_bot.ib_client.connect.assert_awaited_once()
        mock_trading_bot.ib_client.get_account.assert_called_once()
        assert result is True

    async def test_status_returns_false_on_failure(self, mock_trading_bot):
        """status should handle connection failures gracefully."""
        mock_trading_bot.ib_client.is_connected.return_value = False
        mock_trading_bot.ib_client.connect.side_effect = Exception("down")

        result = await mock_trading_bot.status()

        assert result is False
