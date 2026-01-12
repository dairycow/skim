"""Comprehensive configuration tests for Config and ScannerConfig classes

This test suite consolidates all configuration testing to avoid duplication.
It covers:
- Trading parameter defaults and environment variable overrides
- ScannerConfig integration with Config class
- Scanner parameter defaults and immutability from environment variables
- Configuration logging
- Custom configuration creation
"""

import io
import os

import pytest
from loguru import logger

from skim.trading.core.config import Config, ScannerConfig


class TestTradingParameters:
    """Tests for trading-related configuration parameters"""

    def test_default_trading_parameters(self):
        """Test that trading parameters have correct default values"""
        # Clear any existing environment variables
        for key in [
            "PAPER_TRADING",
        ]:
            os.environ.pop(key, None)

        config = Config.from_env()

        # Test default values
        assert config.paper_trading
        assert config.scanner_config.gap_threshold == 9.0
        assert config.max_position_size == 10000
        assert config.max_positions == 50
        # Path should be either Docker or local path depending on environment
        assert config.db_path.endswith("skim.db")

    def test_trading_parameters_can_be_overridden(self):
        """Test that trading parameters can be overridden via environment variables"""
        # Set test environment variables
        os.environ["PAPER_TRADING"] = "true"

        config = Config.from_env()

        # Should use environment variable values
        assert config.paper_trading
        assert (
            config.scanner_config.gap_threshold == 9.0
        )  # No longer configurable via env
        assert config.max_position_size == 10000  # Fixed default
        assert config.max_positions == 50  # Fixed default
        # Path should be either Docker or local path depending on environment
        assert config.db_path.endswith("skim.db")  # Fixed default

        # Clean up
        for key in [
            "PAPER_TRADING",
        ]:
            os.environ.pop(key, None)


class TestScannerConfigIntegration:
    """Tests for ScannerConfig integration with Config class"""

    def test_config_has_scanner_config_attribute(self):
        """Test that Config class has scanner_config attribute instead of individual scanner fields"""
        config = Config(
            ib_client_id=1,
            discord_webhook_url=None,
            scanner_config=ScannerConfig(),
        )

        # Should have scanner_config attribute
        assert hasattr(config, "scanner_config")

        # Should NOT have individual scanner fields
        assert not hasattr(config, "scanner_volume_filter")
        assert not hasattr(config, "scanner_price_filter")
        assert not hasattr(config, "or_duration_minutes")
        assert not hasattr(config, "or_poll_interval_seconds")
        assert not hasattr(config, "gap_fill_tolerance")
        assert not hasattr(config, "or_breakout_buffer")

    def test_scanner_config_type(self):
        """Test that Config.scanner_config is of correct type"""
        config = Config(
            ib_client_id=1,
            discord_webhook_url=None,
            scanner_config=ScannerConfig(),
        )

        assert isinstance(config.scanner_config, ScannerConfig)

    def test_from_env_creates_scanner_config(self):
        """Test that Config.from_env() creates scanner_config from ScannerConfig"""
        # No scanner environment variables exist anymore

        # Set required non-scanner environment variables
        os.environ["PAPER_TRADING"] = "true"

        config = Config.from_env()

        # Should have scanner_config attribute
        assert hasattr(config, "scanner_config")
        assert config.scanner_config is not None

        # Should not have individual scanner attributes
        assert not hasattr(config, "scanner_volume_filter")
        assert not hasattr(config, "scanner_price_filter")
        assert not hasattr(config, "or_duration_minutes")
        assert not hasattr(config, "or_poll_interval_seconds")
        assert not hasattr(config, "gap_fill_tolerance")
        assert not hasattr(config, "or_breakout_buffer")

        # Clean up
        os.environ.pop("PAPER_TRADING", None)


class TestScannerParameters:
    """Tests for scanner configuration parameters"""

    @pytest.mark.parametrize(
        "field,expected_value",
        [
            ("gap_threshold", 9.0),
            ("volume_filter", 10000),
            ("price_filter", 0.05),
            ("or_duration_minutes", 5),
            ("or_poll_interval_seconds", 30),
            ("gap_fill_tolerance", 0.05),
            ("or_breakout_buffer", 0.1),
        ],
    )
    def test_scanner_default_values(self, field, expected_value):
        """Test that scanner parameters have correct default values (parameterized)"""
        # Clear any existing environment variables
        for key in [
            "SCANNER_VOLUME_FILTER",
            "SCANNER_PRICE_FILTER",
            "OR_DURATION_MINUTES",
            "OR_POLL_INTERVAL_SECONDS",
            "GAP_FILL_TOLERANCE",
            "OR_BREAKOUT_BUFFER",
        ]:
            os.environ.pop(key, None)

        config = Config.from_env()

        # Test through scanner_config attribute
        assert getattr(config.scanner_config, field) == expected_value


class TestCustomScannerConfig:
    """Tests for custom ScannerConfig creation"""

    def test_custom_scanner_config(self):
        """Test that Config can be created with custom ScannerConfig"""
        custom_scanner_config = ScannerConfig(
            volume_filter=75000,
            price_filter=0.75,
            or_duration_minutes=15,
            or_poll_interval_seconds=45,
            gap_fill_tolerance=1.5,
            or_breakout_buffer=0.2,
        )

        config = Config(
            ib_client_id=1,
            discord_webhook_url=None,
            scanner_config=custom_scanner_config,
        )

        # Should use custom values
        assert config.scanner_config.volume_filter == 75000
        assert config.scanner_config.price_filter == 0.75
        assert config.scanner_config.or_duration_minutes == 15
        assert config.scanner_config.or_poll_interval_seconds == 45
        assert config.scanner_config.gap_fill_tolerance == 1.5
        assert config.scanner_config.or_breakout_buffer == 0.2


class TestConfigLogging:
    """Tests for configuration logging output"""

    def test_logging_uses_scanner_config(self):
        """Test that configuration logging uses scanner_config values"""
        # Set required non-scanner environment variables
        os.environ["PAPER_TRADING"] = "true"

        # Capture log output
        log_capture = io.StringIO()
        logger.remove()
        logger.add(log_capture, format="{message}")

        Config.from_env()

        # Get log output
        log_output = log_capture.getvalue()

        # Should log scanner configuration values
        assert "Scanner Gap Threshold: 9.0%" in log_output
        assert "Scanner Volume Filter: 10,000 shares" in log_output
        assert "Scanner Price Filter: $0.05" in log_output
        assert "OR Duration: 5 minutes" in log_output
        assert "OR Poll Interval: 30 seconds" in log_output
        assert "Gap Fill Tolerance: $0.05" in log_output
        assert "OR Breakout Buffer: $0.1" in log_output

        # Clean up
        os.environ.pop("PAPER_TRADING", None)


class TestOAuthKeyPaths:
    """Tests for OAuth key path constants"""

    def test_oauth_signature_key_path_constant(self):
        """Test that OAuth signature key path is correctly defined in Config"""
        from skim.trading.core.config import Config

        config = Config.from_env()
        # Path should be either Docker or local path depending on environment
        assert config.oauth_signature_key_path.endswith("private_signature.pem")

    def test_oauth_encryption_key_path_constant(self):
        """Test that OAuth encryption key path is correctly defined in Config"""
        from skim.trading.core.config import Config

        config = Config.from_env()
        # Path should be either Docker or local path depending on environment
        assert config.oauth_encryption_key_path.endswith(
            "private_encryption.pem"
        )
