"""Test dependency injection for core components."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from skim.core.bot import TradingBot
from skim.core.config import Config, ScannerConfig


@pytest.mark.asyncio
class TestTradingBotDependencyInjection:
    """Test TradingBot uses shared client for all components"""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create a mock Config object."""
        return Config(
            ib_client_id=1,
            db_path=str(tmp_path / "test.db"),
            discord_webhook_url="https://discord.com/webhook/test",
            paper_trading=True,
            max_positions=3,
            max_position_size=10000,
            scanner_config=ScannerConfig(),
            oauth_signature_key_path=str(tmp_path / "sig.pem"),
            oauth_encryption_key_path=str(tmp_path / "enc.pem"),
        )

    async def test_creates_only_one_ibkr_client_and_services(self, mock_config):
        """TradingBot should create only one IBKRClient instance and related services."""
        with (
            patch("skim.core.bot.Database"),
            patch("skim.core.bot.IBKRClient") as mock_ibkr_client_class,
            patch("skim.core.bot.IBKRMarketData") as mock_market_data_class,
            patch("skim.core.bot.IBKROrders") as mock_orders_class,
            patch("skim.core.bot.IBKRScanner") as mock_scanner_service_class,
            patch("skim.core.bot.Scanner"),
            patch("skim.core.bot.RangeTracker"),
            patch("skim.core.bot.Trader"),
            patch("skim.core.bot.Monitor"),
            patch("skim.core.bot.DiscordNotifier"),
        ):
            # Mock return values for the classes
            mock_ibkr_client_instance = AsyncMock()
            mock_ibkr_client_class.return_value = mock_ibkr_client_instance

            mock_market_data_instance = Mock()
            mock_market_data_class.return_value = mock_market_data_instance

            mock_orders_instance = Mock()
            mock_orders_class.return_value = mock_orders_instance

            mock_scanner_service_instance = Mock()
            mock_scanner_service_class.return_value = (
                mock_scanner_service_instance
            )

            bot = TradingBot(mock_config)

            # Verify IBKRClient is instantiated exactly once
            mock_ibkr_client_class.assert_called_once_with(
                paper_trading=mock_config.paper_trading
            )

            # Verify MarketData is instantiated once with the correct client
            mock_market_data_class.assert_called_once_with(
                mock_ibkr_client_instance
            )

            # Verify Orders is instantiated once with the correct client and market data
            mock_orders_class.assert_called_once_with(
                mock_ibkr_client_instance, mock_market_data_instance
            )

            # Verify ScannerService is instantiated once with the correct client and config
            mock_scanner_service_class.assert_called_once_with(
                mock_ibkr_client_instance, mock_config.scanner_config
            )

            # Verify that the bot holds references to these single instances
            assert bot.ib_client is mock_ibkr_client_instance
            assert bot.market_data_service is mock_market_data_instance
            assert bot.order_service is mock_orders_instance
            assert bot.scanner_service is mock_scanner_service_instance

    async def test_components_receive_correct_dependencies(self, mock_config):
        """Test that Scanner, Trader, and Monitor receive the correct service dependencies."""
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
            patch("skim.core.bot.DiscordNotifier"),
        ):
            # Mock return values for the classes
            mock_db_instance = Mock()
            mock_db_class.return_value = mock_db_instance

            mock_ibkr_client_instance = AsyncMock()
            mock_ibkr_client_class.return_value = mock_ibkr_client_instance

            mock_market_data_instance = Mock()
            mock_market_data_class.return_value = mock_market_data_instance

            mock_orders_instance = Mock()
            mock_orders_class.return_value = mock_orders_instance

            mock_scanner_service_instance = Mock()
            mock_scanner_service_class.return_value = (
                mock_scanner_service_instance
            )

            bot = TradingBot(mock_config)

            # Verify Scanner logic receives correct services
            mock_scanner_logic_class.assert_called_once_with(
                scanner_service=mock_scanner_service_instance,
                gap_threshold=mock_config.scanner_config.gap_threshold,
            )

            # Verify Trader logic receives correct services
            mock_trader_logic_class.assert_called_once_with(
                mock_market_data_instance,
                mock_orders_instance,
                mock_db_instance,
            )

            # Verify Monitor logic receives correct services
            mock_monitor_logic_class.assert_called_once_with(
                mock_market_data_instance
            )

            # Verify that the bot holds references to these logic modules
            assert bot.scanner is mock_scanner_logic_class.return_value
            assert bot.trader is mock_trader_logic_class.return_value
            assert bot.monitor is mock_monitor_logic_class.return_value
