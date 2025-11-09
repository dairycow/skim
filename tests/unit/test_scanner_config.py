"""Test ScannerConfig dataclass structure and functionality"""

from dataclasses import is_dataclass


def test_scanner_config_import():
    """Test that ScannerConfig can be imported"""
    from skim.core.config import ScannerConfig

    assert ScannerConfig is not None


def test_scanner_config_is_dataclass():
    """Test that ScannerConfig is a dataclass"""
    from skim.core.config import ScannerConfig

    assert is_dataclass(ScannerConfig)


def test_scanner_config_has_required_fields():
    """Test that ScannerConfig has all required scanner configuration fields"""
    from skim.core.config import ScannerConfig

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
    """Test that ScannerConfig has correct default values matching current env defaults"""
    from skim.core.config import ScannerConfig

    config = ScannerConfig()

    # These should match the current defaults from config.py
    assert config.volume_filter == 50000
    assert config.price_filter == 0.50
    assert config.or_duration_minutes == 10
    assert config.or_poll_interval_seconds == 30
    assert config.gap_fill_tolerance == 1.0
    assert config.or_breakout_buffer == 0.1


def test_scanner_config_custom_values():
    """Test that ScannerConfig accepts custom values"""
    from skim.core.config import ScannerConfig

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

    from skim.core.config import ScannerConfig

    # Get type hints
    hints = typing.get_type_hints(ScannerConfig)

    # Check field types
    assert hints["volume_filter"] is int
    assert hints["price_filter"] is float
    assert hints["or_duration_minutes"] is int
    assert hints["or_poll_interval_seconds"] is int
    assert hints["gap_fill_tolerance"] is float
    assert hints["or_breakout_buffer"] is float
