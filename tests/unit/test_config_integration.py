"""Test Config class integration with ScannerConfig"""

import os


def test_config_has_scanner_config_attribute():
    """Test that Config class has scanner_config attribute"""
    from skim.core.config import Config, ScannerConfig

    # Create instance to check attribute existence
    config = Config(
        ib_client_id=1,
        discord_webhook_url=None,
        scanner_config=ScannerConfig(),
    )

    # Should have scanner_config attribute instead of individual scanner fields
    assert hasattr(config, "scanner_config")
    assert not hasattr(config, "scanner_volume_filter")
    assert not hasattr(config, "scanner_price_filter")
    assert not hasattr(config, "or_duration_minutes")
    assert not hasattr(config, "or_poll_interval_seconds")
    assert not hasattr(config, "gap_fill_tolerance")
    assert not hasattr(config, "or_breakout_buffer")


def test_config_scanner_config_type():
    """Test that Config.scanner_config is of correct type"""
    from skim.core.config import Config, ScannerConfig

    config = Config(
        ib_client_id=1,
        discord_webhook_url=None,
        scanner_config=ScannerConfig(),
    )

    assert isinstance(config.scanner_config, ScannerConfig)


def test_config_from_env_uses_scanner_config():
    """Test that Config.from_env() creates scanner_config from ScannerConfig"""
    # Clear any existing scanner environment variables
    for key in [
        "SCANNER_VOLUME_FILTER",
        "SCANNER_PRICE_FILTER",
        "OR_DURATION_MINUTES",
        "OR_POLL_INTERVAL_SECONDS",
        "GAP_FILL_TOLERANCE",
        "OR_BREAKOUT_BUFFER",
    ]:
        os.environ.pop(key, None)

    # Set required non-scanner environment variables
    os.environ["PAPER_TRADING"] = "true"

    from skim.core.config import Config

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


def test_config_scanner_config_default_values():
    """Test that Config.scanner_config has correct default values"""
    # Clear any existing scanner environment variables
    for key in [
        "SCANNER_VOLUME_FILTER",
        "SCANNER_PRICE_FILTER",
        "OR_DURATION_MINUTES",
        "OR_POLL_INTERVAL_SECONDS",
        "GAP_FILL_TOLERANCE",
        "OR_BREAKOUT_BUFFER",
    ]:
        os.environ.pop(key, None)

    # Set required non-scanner environment variables
    os.environ["PAPER_TRADING"] = "true"

    from skim.core.config import Config

    config = Config.from_env()

    # Check default values through scanner_config
    assert config.scanner_config.volume_filter == 50000
    assert config.scanner_config.price_filter == 0.50
    assert config.scanner_config.or_duration_minutes == 10
    assert config.scanner_config.or_poll_interval_seconds == 30
    assert config.scanner_config.gap_fill_tolerance == 1.0
    assert config.scanner_config.or_breakout_buffer == 0.1

    # Clean up
    os.environ.pop("PAPER_TRADING", None)
