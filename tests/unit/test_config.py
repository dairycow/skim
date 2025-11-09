"""Test configuration loading for new scanner parameters and default values"""

import os

from skim.core.config import Config


def test_config_default_trading_parameters():
    """Test that trading parameters have correct default values"""
    # Clear any existing environment variables
    for key in [
        "PAPER_TRADING",
        "GAP_THRESHOLD",
        "MAX_POSITION_SIZE",
        "MAX_POSITIONS",
        "DB_PATH",
    ]:
        os.environ.pop(key, None)

    config = Config.from_env()

    # Test default values
    assert config.paper_trading
    assert config.gap_threshold == 3.0
    assert config.max_position_size == 1000
    assert config.max_positions == 5
    assert config.db_path == "/app/data/skim.db"


def test_config_trading_parameters_can_be_overridden():
    """Test that trading parameters can be overridden via environment variables"""
    # Set test environment variables
    os.environ["PAPER_TRADING"] = "true"
    os.environ["GAP_THRESHOLD"] = "5.0"
    os.environ["MAX_POSITION_SIZE"] = "2000"
    os.environ["MAX_POSITIONS"] = "10"
    os.environ["DB_PATH"] = "/custom/path/db.sqlite"

    config = Config.from_env()

    # Should use environment variable values
    assert config.paper_trading
    assert config.gap_threshold == 5.0
    assert config.max_position_size == 2000
    assert config.max_positions == 10
    assert config.db_path == "/custom/path/db.sqlite"

    # Clean up
    for key in [
        "PAPER_TRADING",
        "GAP_THRESHOLD",
        "MAX_POSITION_SIZE",
        "MAX_POSITIONS",
        "DB_PATH",
    ]:
        os.environ.pop(key, None)


def test_config_scanner_parameters_default_values():
    """Test that scanner parameters have correct default values"""
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
    assert config.scanner_config.volume_filter == 50000
    assert config.scanner_config.price_filter == 0.50
    assert config.scanner_config.or_duration_minutes == 10
    assert config.scanner_config.or_poll_interval_seconds == 30
    assert config.scanner_config.gap_fill_tolerance == 1.0
    assert config.scanner_config.or_breakout_buffer == 0.1


def test_config_scanner_parameters_ignored_from_env():
    """Test that scanner environment variables are ignored (using ScannerConfig defaults)"""
    # Set test environment variables
    os.environ["SCANNER_VOLUME_FILTER"] = "75000"
    os.environ["SCANNER_PRICE_FILTER"] = "0.75"
    os.environ["OR_DURATION_MINUTES"] = "15"
    os.environ["OR_POLL_INTERVAL_SECONDS"] = "45"
    os.environ["GAP_FILL_TOLERANCE"] = "1.5"
    os.environ["OR_BREAKOUT_BUFFER"] = "0.2"

    config = Config.from_env()

    # Should still use ScannerConfig defaults, not environment variables
    assert config.scanner_config.volume_filter == 50000
    assert config.scanner_config.price_filter == 0.50
    assert config.scanner_config.or_duration_minutes == 10
    assert config.scanner_config.or_poll_interval_seconds == 30
    assert config.scanner_config.gap_fill_tolerance == 1.0
    assert config.scanner_config.or_breakout_buffer == 0.1

    # Clean up
    for key in [
        "SCANNER_VOLUME_FILTER",
        "SCANNER_PRICE_FILTER",
        "OR_DURATION_MINUTES",
        "OR_POLL_INTERVAL_SECONDS",
        "GAP_FILL_TOLERANCE",
        "OR_BREAKOUT_BUFFER",
    ]:
        os.environ.pop(key, None)
