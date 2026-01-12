"""Test ScannerConfig dataclass structure and functionality"""

import os
from dataclasses import is_dataclass
from unittest.mock import patch

from loguru import logger


def test_scanner_config_import():
    """Test that ScannerConfig can be imported"""
    from skim.trading.core.config import ScannerConfig

    assert ScannerConfig is not None


def test_scanner_config_is_dataclass():
    """Test that ScannerConfig is a dataclass"""
    from skim.trading.core.config import ScannerConfig

    assert is_dataclass(ScannerConfig)


def test_scanner_config_has_required_fields():
    """Test that ScannerConfig has all required scanner configuration fields"""
    from skim.trading.core.config import ScannerConfig

    # Create instance to check field existence
    config = ScannerConfig()

    # Check all required fields exist
    assert hasattr(config, "volume_filter")
    assert hasattr(config, "price_filter")
    assert hasattr(config, "or_duration_minutes")
    assert hasattr(config, "or_poll_interval_seconds")
    assert hasattr(config, "gap_fill_tolerance")
    assert hasattr(config, "or_breakout_buffer")


def test_scanner_config_default_values():
    """Test that ScannerConfig has correct ASX-optimized default values"""
    from skim.trading.core.config import ScannerConfig

    config = ScannerConfig()

    # These should match the ASX-optimized defaults from config.py
    assert config.volume_filter == 10000
    assert config.price_filter == 0.05
    assert config.or_duration_minutes == 5
    assert config.or_poll_interval_seconds == 30
    assert config.gap_fill_tolerance == 0.05
    assert config.or_breakout_buffer == 0.1


def test_scanner_config_custom_values():
    """Test that ScannerConfig accepts custom values"""
    from skim.trading.core.config import ScannerConfig

    config = ScannerConfig(
        volume_filter=75000,
        price_filter=0.75,
        or_duration_minutes=15,
        or_poll_interval_seconds=45,
        gap_fill_tolerance=1.5,
        or_breakout_buffer=0.2,
    )

    assert config.volume_filter == 75000
    assert config.price_filter == 0.75
    assert config.or_duration_minutes == 15
    assert config.or_poll_interval_seconds == 45
    assert config.gap_fill_tolerance == 1.5
    assert config.or_breakout_buffer == 0.2


def test_scanner_config_type_annotations():
    """Test that ScannerConfig fields have correct type annotations"""
    import typing

    from skim.trading.core.config import ScannerConfig

    # Get type hints
    hints = typing.get_type_hints(ScannerConfig)

    # Check field types
    assert hints["volume_filter"] is int
    assert hints["price_filter"] is float
    assert hints["or_duration_minutes"] is int
    assert hints["or_poll_interval_seconds"] is int
    assert hints["gap_fill_tolerance"] is float
    assert hints["or_breakout_buffer"] is float


def test_scanner_config_asx_optimized_defaults():
    """Test that ScannerConfig has ASX-optimized defaults for 4c+ stocks"""
    from skim.trading.core.config import ScannerConfig

    config = ScannerConfig()

    # ASX-optimized defaults for low-priced stocks
    assert (
        config.volume_filter == 10000
    )  # Lower volume threshold for ASX small caps
    assert config.price_filter == 0.05  # 5c minimum for 4c+ stock opportunities
    assert config.or_duration_minutes == 5
    assert config.or_poll_interval_seconds == 30
    assert config.gap_fill_tolerance == 0.05
    assert config.or_breakout_buffer == 0.1


@patch.dict(
    os.environ,
    {
        "PAPER_TRADING": "true",
    },
)
def test_config_from_env_uses_scanner_defaults():
    """Test that Config.from_env() uses scanner config defaults"""
    from skim.trading.core.config import Config

    config = Config.from_env()

    # Should use class defaults, not environment variables
    assert config.scanner_config.volume_filter == 10000
    assert config.scanner_config.price_filter == 0.05
    assert config.scanner_config.or_duration_minutes == 5
    assert config.scanner_config.or_poll_interval_seconds == 30
    assert config.scanner_config.gap_fill_tolerance == 0.05
    assert config.scanner_config.or_breakout_buffer == 0.1


@patch.dict(
    os.environ,
    {
        "IB_CLIENT_ID": "1",
        "PAPER_TRADING": "true",
    },
)
def test_config_from_env_scanner_config_logging():
    """Test scanner config values are logged correctly"""
    import sys
    from io import StringIO

    from skim.trading.core.config import Config

    # Capture loguru output
    log_capture = StringIO()
    logger.remove()
    logger.add(log_capture, level="INFO")

    try:
        Config.from_env()
        log_output = log_capture.getvalue()

        # Check that scanner config values are logged
        assert "Scanner Volume Filter: 10,000 shares" in log_output
        assert "Scanner Price Filter: $0.05" in log_output
        assert "OR Duration: 5 minutes" in log_output
        assert "OR Poll Interval: 30 seconds" in log_output
        assert "Gap Fill Tolerance: $0.05" in log_output
        assert "OR Breakout Buffer: $0.1" in log_output
    finally:
        # Restore default logger
        logger.remove()
        logger.add(sys.stderr, level="INFO")


def test_scanner_config_integration_with_config():
    """Test integration between ScannerConfig and Config classes"""
    from skim.trading.core.config import Config, ScannerConfig

    # Create custom scanner config
    custom_scanner_config = ScannerConfig(
        volume_filter=50000,
        price_filter=0.25,
        or_duration_minutes=20,
        or_poll_interval_seconds=60,
        gap_fill_tolerance=2.0,
        or_breakout_buffer=0.3,
    )

    # Create config with custom scanner config
    config = Config(
        ib_client_id=1,
        paper_trading=True,
        scanner_config=custom_scanner_config,
        discord_webhook_url=None,
    )

    # Verify integration
    assert config.scanner_config.volume_filter == 50000
    assert config.scanner_config.price_filter == 0.25
    assert config.scanner_config.or_duration_minutes == 20
    assert config.scanner_config.or_poll_interval_seconds == 60
    assert config.scanner_config.gap_fill_tolerance == 2.0
    assert config.scanner_config.or_breakout_buffer == 0.3
