"""Test updated configuration loading behavior after refactor"""

import os


def test_config_ignores_scanner_env_vars():
    """Test that Config.from_env() ignores scanner environment variables"""
    # Set scanner environment variables to non-default values
    os.environ["SCANNER_VOLUME_FILTER"] = "99999"
    os.environ["SCANNER_PRICE_FILTER"] = "0.99"
    os.environ["OR_DURATION_MINUTES"] = "99"
    os.environ["OR_POLL_INTERVAL_SECONDS"] = "99"
    os.environ["GAP_FILL_TOLERANCE"] = "9.9"
    os.environ["OR_BREAKOUT_BUFFER"] = "0.9"

    # Set required non-scanner environment variables
    os.environ["PAPER_TRADING"] = "true"

    from skim.core.config import Config

    config = Config.from_env()

    # Should use ScannerConfig defaults, not environment variables
    assert config.scanner_config.volume_filter == 50000  # Default, not 99999
    assert config.scanner_config.price_filter == 0.50  # Default, not 0.99
    assert config.scanner_config.or_duration_minutes == 10  # Default, not 99
    assert (
        config.scanner_config.or_poll_interval_seconds == 30
    )  # Default, not 99
    assert config.scanner_config.gap_fill_tolerance == 1.0  # Default, not 9.9
    assert config.scanner_config.or_breakout_buffer == 0.1  # Default, not 0.9

    # Clean up
    for key in [
        "SCANNER_VOLUME_FILTER",
        "SCANNER_PRICE_FILTER",
        "OR_DURATION_MINUTES",
        "OR_POLL_INTERVAL_SECONDS",
        "GAP_FILL_TOLERANCE",
        "OR_BREAKOUT_BUFFER",
        "PAPER_TRADING",
    ]:
        os.environ.pop(key, None)


def test_config_logging_uses_scanner_config():
    """Test that configuration logging uses scanner_config values"""
    # Set required non-scanner environment variables
    os.environ["PAPER_TRADING"] = "true"

    import io

    from loguru import logger

    from skim.core.config import Config

    # Capture log output
    log_capture = io.StringIO()
    logger.remove()
    logger.add(log_capture, format="{message}")

    Config.from_env()

    # Get log output
    log_output = log_capture.getvalue()

    # Should log scanner configuration values
    assert "Scanner Volume Filter: 50,000 shares" in log_output
    assert "Scanner Price Filter: $0.5" in log_output
    assert "OR Duration: 10 minutes" in log_output
    assert "OR Poll Interval: 30 seconds" in log_output
    assert "Gap Fill Tolerance: $1.0" in log_output
    assert "OR Breakout Buffer: $0.1" in log_output

    # Clean up
    os.environ.pop("PAPER_TRADING", None)


def test_config_custom_scanner_config():
    """Test that Config can be created with custom ScannerConfig"""
    from skim.core.config import Config, ScannerConfig

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
