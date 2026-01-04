"""Tests for TradingBot orchestrator using async services"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from skim.core.bot import TradingBot
from skim.core.config import Config, ScannerConfig


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
        patch("skim.core.bot.ORHBreakoutStrategy") as mock_strategy_class,
        patch("skim.core.bot.DiscordNotifier") as mock_discord_notifier_class,
    ):
        # Mock instances
        mock_db = mock_db_class.return_value
        mock_ibkr_client = mock_ibkr_client_class.return_value
        mock_market_data_service = mock_market_data_class.return_value
        mock_orders_service = mock_orders_class.return_value
        mock_scanner_service = mock_scanner_service_class.return_value
        mock_strategy = Mock()
        mock_discord_notifier = mock_discord_notifier_class.return_value

        # Configure mocks for async methods
        mock_ibkr_client.is_connected.return_value = False
        mock_ibkr_client.connect = AsyncMock()
        mock_ibkr_client.disconnect = AsyncMock()
        mock_ibkr_client.get_account = Mock(return_value="DU123")

        mock_market_data_service.get_market_data = AsyncMock()

        # Mock strategy methods
        mock_strategy.scan = AsyncMock(return_value=0)
        mock_strategy.trade = AsyncMock(return_value=0)
        mock_strategy.manage = AsyncMock(return_value=0)
        mock_strategy.health_check = AsyncMock(return_value=True)
        mock_strategy_class.return_value = mock_strategy

        bot = TradingBot(mock_bot_config)

        # Attach mocks to bot instance for easier access in tests
        bot.db = mock_db
        bot.ib_client = mock_ibkr_client
        bot.market_data_service = mock_market_data_service
        bot.order_service = mock_orders_service
        bot.scanner_service = mock_scanner_service
        bot.discord = mock_discord_notifier

        yield bot


@pytest.mark.asyncio
class TestTradingBot:
    """Tests for refactored TradingBot orchestrator."""

    async def test_init_instantiates_services_and_strategies(
        self, mock_bot_config
    ):
        """TradingBot should wire all services and register strategies."""
        with (
            patch("skim.core.bot.Database") as mock_db_class,
            patch("skim.core.bot.IBKRClient") as mock_ibkr_client_class,
            patch("skim.core.bot.IBKRMarketData") as mock_market_data_class,
            patch("skim.core.bot.IBKROrders") as mock_orders_class,
            patch("skim.core.bot.IBKRGapScanner") as mock_scanner_service_class,
            patch("skim.core.bot.ORHBreakoutStrategy") as mock_strategy_class,
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
            mock_discord_notifier_class.assert_called_once_with(
                mock_bot_config.discord_webhook_url
            )
            mock_strategy_class.assert_called_once()
            assert bot.db == mock_db_class.return_value
            assert "orh_breakout" in bot.strategies

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

    async def test_scan_delegates_to_strategy(self, mock_trading_bot):
        """scan should delegate to strategy."""
        mock_trading_bot.strategies["orh_breakout"].scan.return_value = 8

        result = await mock_trading_bot.scan()

        mock_trading_bot.strategies["orh_breakout"].scan.assert_awaited_once()
        assert result == 8

    async def test_trade_delegates_to_strategy(self, mock_trading_bot):
        """trade should delegate to the strategy."""
        mock_trading_bot.strategies["orh_breakout"].trade.return_value = 2

        result = await mock_trading_bot.trade()

        mock_trading_bot.strategies["orh_breakout"].trade.assert_awaited_once()
        assert result == 2

    async def test_manage_delegates_to_strategy(self, mock_trading_bot):
        """manage should delegate to the strategy."""
        mock_trading_bot.strategies["orh_breakout"].manage.return_value = 1

        result = await mock_trading_bot.manage()

        mock_trading_bot.strategies["orh_breakout"].manage.assert_awaited_once()
        assert result == 1

    async def test_status_delegates_to_strategy(self, mock_trading_bot):
        """status should delegate to the strategy."""
        mock_trading_bot.strategies[
            "orh_breakout"
        ].health_check.return_value = True

        result = await mock_trading_bot.status()

        mock_trading_bot.strategies[
            "orh_breakout"
        ].health_check.assert_awaited_once()
        assert result is True

    async def test_get_strategy_returns_strategy(self, mock_trading_bot):
        """_get_strategy should return the strategy instance."""
        strategy = mock_trading_bot._get_strategy("orh_breakout")
        assert strategy == mock_trading_bot.strategies["orh_breakout"]

    async def test_get_strategy_raises_for_unknown(self, mock_trading_bot):
        """_get_strategy should raise ValueError for unknown strategy."""
        with pytest.raises(ValueError) as exc:
            mock_trading_bot._get_strategy("unknown_strategy")
        assert "Unknown strategy" in str(exc.value)

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
