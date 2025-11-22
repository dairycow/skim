"""Test dependency injection for scanner components - TDD RED phase

This test module defines the expected behaviour after refactoring to use
dependency injection for IBKR client instances.
"""

from unittest.mock import Mock

import pytest

from skim.brokers.ib_interface import IBInterface
from skim.core.bot import TradingBot
from skim.core.config import Config, ScannerConfig
from skim.scanner import Scanner
from skim.scanners.ibkr_gap_scanner import IBKRGapScanner


class TestIBKRGapScannerDependencyInjection:
    """Test IBKRGapScanner accepts injected IBInterface client"""

    def test_accepts_client_parameter(self):
        """IBKRGapScanner should accept client parameter in constructor"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        mock_client.is_connected.return_value = True

        # Act
        scanner = IBKRGapScanner(client=mock_client)

        # Assert
        assert scanner.client is mock_client

    def test_raises_error_without_client(self):
        """IBKRGapScanner should raise TypeError if no client provided"""
        # Act & Assert
        with pytest.raises(TypeError):
            IBKRGapScanner()  # Missing required 'client' parameter

    def test_uses_injected_client_for_operations(self):
        """IBKRGapScanner should use injected client for scanner operations"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        mock_client.is_connected.return_value = True
        mock_client.run_scanner.return_value = []

        scanner = IBKRGapScanner(client=mock_client)

        # Act
        scanner.scan_for_gaps(min_gap=3.0)

        # Assert
        mock_client.run_scanner.assert_called_once()

    def test_accepts_scanner_config_parameter(self):
        """IBKRGapScanner should still accept optional scanner_config"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        config = ScannerConfig(gap_threshold=5.0)

        # Act
        scanner = IBKRGapScanner(client=mock_client, scanner_config=config)

        # Assert
        assert scanner.scanner_config.gap_threshold == 5.0

    def test_no_longer_has_connect_method(self):
        """IBKRGapScanner should not have connect() method"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        scanner = IBKRGapScanner(client=mock_client)

        # Assert
        assert not hasattr(scanner, "connect") or not callable(
            getattr(scanner, "connect", None)
        )

    def test_no_longer_has_disconnect_method(self):
        """IBKRGapScanner should not have disconnect() method"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        scanner = IBKRGapScanner(client=mock_client)

        # Assert
        assert not hasattr(scanner, "disconnect") or not callable(
            getattr(scanner, "disconnect", None)
        )

    def test_is_connected_delegates_to_client(self):
        """IBKRGapScanner.is_connected() should delegate to client.is_connected()"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        mock_client.is_connected.return_value = True
        scanner = IBKRGapScanner(client=mock_client)

        # Act
        result = scanner.is_connected()

        # Assert
        assert result is True
        mock_client.is_connected.assert_called_once()


class TestScannerDependencyInjection:
    """Test Scanner accepts injected IBInterface client"""

    def test_accepts_ib_client_parameter(self):
        """Scanner should accept ib_client parameter in constructor"""
        # Arrange
        mock_client = Mock(spec=IBInterface)

        # Act
        scanner = Scanner(ib_client=mock_client, gap_threshold=3.0)

        # Assert
        assert scanner.ib_client is mock_client

    def test_raises_error_without_client(self):
        """Scanner should raise TypeError if no client provided"""
        # Act & Assert
        with pytest.raises(TypeError):
            Scanner(gap_threshold=3.0)  # Missing required 'ib_client' parameter

    def test_passes_client_to_ibkr_gap_scanner(self, mocker):
        """Scanner should pass shared client to IBKRGapScanner"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        mock_gap_scanner_init = mocker.patch("skim.scanner.IBKRGapScanner")

        # Act
        Scanner(ib_client=mock_client, gap_threshold=3.0)

        # Assert
        # Verify IBKRGapScanner was called with the client
        mock_gap_scanner_init.assert_called_once()
        call_kwargs = mock_gap_scanner_init.call_args.kwargs
        assert "client" in call_kwargs
        assert call_kwargs["client"] is mock_client

    def test_does_not_create_own_ibkr_client(self, mocker):
        """Scanner should not create its own IBKRClient instance"""
        # Arrange
        mock_client = Mock(spec=IBInterface)
        mocker.patch("skim.scanner.IBKRGapScanner")

        # Act
        scanner = Scanner(ib_client=mock_client, gap_threshold=3.0)

        # Assert
        # Scanner should use the injected client, not create its own
        assert scanner.ib_client is mock_client
        # IBKRClient should not even be imported in scanner module
        import skim.scanner as scanner_module

        assert not hasattr(scanner_module, "IBKRClient")


class TestTradingBotDependencyInjection:
    """Test TradingBot uses shared client for all components"""

    def test_passes_same_client_to_all_components(self, mocker, tmp_path):
        """TradingBot should pass same client instance to Scanner, Trader, Monitor"""
        # Arrange - Mock all component constructors
        mock_scanner_init = mocker.patch("skim.core.bot.Scanner")
        mock_trader_init = mocker.patch("skim.core.bot.Trader")
        mock_monitor_init = mocker.patch("skim.core.bot.Monitor")
        mocker.patch("skim.core.bot.Database")
        mocker.patch("skim.core.bot.DiscordNotifier")

        # Create test config
        config = Config(
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

        # Act
        bot = TradingBot(config)

        # Assert - All components should receive the same client instance
        scanner_client = mock_scanner_init.call_args.kwargs.get("ib_client")
        trader_client = mock_trader_init.call_args[0][0]  # First positional arg
        monitor_client = mock_monitor_init.call_args[0][
            0
        ]  # First positional arg

        assert scanner_client is not None
        assert scanner_client is trader_client
        assert scanner_client is monitor_client
        assert scanner_client is bot.ib_client

    def test_creates_only_one_ibkr_client(self, mocker, tmp_path):
        """TradingBot should create only one IBKRClient instance"""
        # Arrange
        mock_ibkr_client_init = mocker.patch("skim.core.bot.IBKRClient")
        mocker.patch("skim.core.bot.Scanner")
        mocker.patch("skim.core.bot.Trader")
        mocker.patch("skim.core.bot.Monitor")
        mocker.patch("skim.core.bot.Database")
        mocker.patch("skim.core.bot.DiscordNotifier")

        config = Config(
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

        # Act
        TradingBot(config)

        # Assert - IBKRClient should be instantiated exactly once
        assert mock_ibkr_client_init.call_count == 1
        mock_ibkr_client_init.assert_called_once_with(paper_trading=True)

    def test_connection_managed_at_bot_level(self, mocker, tmp_path):
        """TradingBot should manage connection, not individual components"""
        # Arrange
        mocker.patch("skim.core.bot.Scanner")
        mocker.patch("skim.core.bot.Trader")
        mocker.patch("skim.core.bot.Monitor")
        mocker.patch("skim.core.bot.Database")
        mocker.patch("skim.core.bot.DiscordNotifier")

        config = Config(
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

        # Act
        bot = TradingBot(config)

        # Assert - Bot should own the client connection
        assert hasattr(bot, "ib_client")
        assert hasattr(bot, "_ensure_connection")
