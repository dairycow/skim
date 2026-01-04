"""Tests for TradingBot orchestrator using async services"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from skim.core.bot import TradingBot
from skim.core.config import Config, ScannerConfig
from skim.data.models import Position


@pytest.fixture
def mock_bot_config():
    """Mock configuration for TradingBot."""
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
        patch("skim.core.bot.IBKRGapScanner") as mock_scanner_service_class,
        patch("skim.core.bot.GapScanner"),
        patch("skim.core.bot.NewsScanner"),
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
        mock_scanner_service = mock_scanner_service_class.return_value
        mock_scanner_logic = Mock()
        mock_trader_logic = mock_trader_logic_class.return_value
        mock_monitor_logic = mock_monitor_logic_class.return_value
        mock_discord_notifier = mock_discord_notifier_class.return_value

        # Configure mocks for async methods
        mock_ibkr_client.is_connected.return_value = False
        mock_ibkr_client.connect = AsyncMock()
        mock_ibkr_client.disconnect = AsyncMock()
        mock_ibkr_client.get_account = Mock(return_value="DU123")

        mock_scanner_logic.find_gap_candidates = AsyncMock(return_value=[])
        mock_scanner_logic.find_news_candidates = AsyncMock(return_value=[])
        mock_market_data_service.get_market_data = AsyncMock()
        mock_trader_logic.execute_breakouts = AsyncMock(return_value=0)
        mock_trader_logic.execute_stops = AsyncMock(return_value=0)
        mock_monitor_logic.check_stops = AsyncMock(return_value=[])

        bot = TradingBot(mock_bot_config)

        # Attach mocks to bot instance for easier access in tests
        bot.db = mock_db
        bot.ib_client = mock_ibkr_client
        bot.market_data_service = mock_market_data_service
        bot.order_service = mock_orders_service
        bot.scanner_service = mock_scanner_service
        bot.gap_scanner = mock_scanner_logic
        bot.news_scanner = mock_scanner_logic
        bot.trader = mock_trader_logic
        bot.monitor = mock_monitor_logic
        bot.discord = mock_discord_notifier

        yield bot


@pytest.mark.asyncio
class TestTradingBot:
    """Tests for refactored TradingBot orchestrator."""

    async def test_init_instantiates_services_and_logic(self, mock_bot_config):
        """TradingBot should wire all services and business modules."""
        with (
            patch("skim.core.bot.Database") as mock_db_class,
            patch("skim.core.bot.IBKRClient") as mock_ibkr_client_class,
            patch("skim.core.bot.IBKRMarketData") as mock_market_data_class,
            patch("skim.core.bot.IBKROrders") as mock_orders_class,
            patch("skim.core.bot.IBKRGapScanner") as mock_scanner_service_class,
            patch("skim.core.bot.GapScanner"),
            patch("skim.core.bot.NewsScanner"),
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

    async def test_scan_gaps_workflow(self, mock_trading_bot):
        """scan_gaps should ensure connection, persist candidates, and notify."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_trading_bot.gap_scanner.find_gap_candidates.return_value = []

        result = await mock_trading_bot.scan_gaps()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.gap_scanner.find_gap_candidates.assert_awaited_once()
        mock_trading_bot.discord.send_gap_candidates.assert_called_once_with(
            0, []
        )
        assert result == 0

    async def test_scan_news_workflow(self, mock_trading_bot):
        """scan_news should ensure connection, persist candidates, and notify."""
        mock_trading_bot.news_scanner.find_news_candidates.return_value = []

        result = await mock_trading_bot.scan_news()

        mock_trading_bot.news_scanner.find_news_candidates.assert_awaited_once()
        mock_trading_bot.discord.send_news_candidates.assert_called_once_with(
            0, []
        )
        assert result == 0

    async def test_track_ranges_workflow(self, mock_trading_bot):
        """track_ranges should delegate to RangeTracker."""
        mock_trading_bot.range_tracker.track_opening_ranges.return_value = 0

        result = await mock_trading_bot.track_ranges()

        mock_trading_bot.range_tracker.track_opening_ranges.assert_called_once()
        assert result == 0

    async def test_trade_workflow(self, mock_trading_bot):
        """trade should retrieve tradeable candidates and delegate to Trader."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_candidates = [Mock(spec=Position)]
        mock_trading_bot.db.get_tradeable_candidates.return_value = (
            mock_candidates
        )
        mock_trading_bot.trader.execute_breakouts.return_value = []

        result = await mock_trading_bot.trade()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.db.get_tradeable_candidates.assert_called_once()
        mock_trading_bot.trader.execute_breakouts.assert_awaited_once_with(
            mock_candidates
        )
        assert result == 0

    async def test_trade_handles_no_candidates(self, mock_trading_bot):
        """trade should early-exit when no tradeable candidates exist."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_trading_bot.db.get_tradeable_candidates.return_value = []

        result = await mock_trading_bot.trade()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.db.get_tradeable_candidates.assert_called_once()
        mock_trading_bot.trader.execute_breakouts.assert_not_awaited()
        assert result == 0

    async def test_manage_workflow(self, mock_trading_bot):
        """manage should check stops and delegate exits."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_positions = [Mock(spec=Position)]
        mock_stops_hit = [Mock(spec=Position)]
        mock_trading_bot.db.get_open_positions.return_value = mock_positions
        mock_trading_bot.monitor.check_stops.return_value = mock_stops_hit
        mock_trading_bot.trader.execute_stops.return_value = []

        result = await mock_trading_bot.manage()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.db.get_open_positions.assert_called_once()
        mock_trading_bot.monitor.check_stops.assert_awaited_once_with(
            mock_positions
        )
        mock_trading_bot.trader.execute_stops.assert_awaited_once_with(
            mock_stops_hit
        )
        assert result == 0

    async def test_manage_handles_no_positions(self, mock_trading_bot):
        """manage should early-exit when no open positions exist."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_trading_bot.db.get_open_positions.return_value = []

        result = await mock_trading_bot.manage()

        mock_trading_bot.ib_client.connect.assert_not_awaited()
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

        mock_trading_bot.ib_client.connect.assert_not_awaited()
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

    async def test_fetch_market_data_connects_and_returns_data(
        self, mock_trading_bot
    ):
        """fetch_market_data should ensure connection then return snapshot."""
        mock_trading_bot.ib_client.is_connected.return_value = False
        sample_data = Mock(last_price=1.23, high=1.5, low=1.1)
        mock_trading_bot.market_data_service.get_market_data.return_value = (
            sample_data
        )

        result = await mock_trading_bot.fetch_market_data("ABC")

        mock_trading_bot.ib_client.connect.assert_awaited_once()
        mock_trading_bot.market_data_service.get_market_data.assert_awaited_once_with(
            "ABC"
        )
        assert result is sample_data

    async def test_fetch_market_data_handles_empty_ticker(
        self, mock_trading_bot
    ):
        """fetch_market_data should return None when ticker is missing."""
        result = await mock_trading_bot.fetch_market_data("")

        mock_trading_bot.ib_client.connect.assert_not_awaited()
        mock_trading_bot.market_data_service.get_market_data.assert_not_awaited()
        assert result is None

    async def test_fetch_market_data_handles_errors(self, mock_trading_bot):
        """fetch_market_data should swallow errors and return None."""
        mock_trading_bot.ib_client.is_connected.return_value = True
        mock_trading_bot.market_data_service.get_market_data.side_effect = (
            Exception("boom")
        )

        result = await mock_trading_bot.fetch_market_data("ABC")

        mock_trading_bot.market_data_service.get_market_data.assert_awaited_once_with(
            "ABC"
        )
        assert result is None

    async def test_purge_candidates_deletes_rows(self, mock_trading_bot):
        """purge_candidates should delegate deletion tos database."""
        mock_trading_bot.db.purge_candidates.return_value = 3

        deleted = await mock_trading_bot.purge_candidates()

        mock_trading_bot.db.purge_candidates.assert_called_once_with(None)
        assert deleted == 3
