"""Pytest fixtures for integration tests"""

import os

import pytest


def validate_oauth_environment():
    """Validate required OAuth environment variables are set for integration tests."""
    required_vars = [
        "OAUTH_CONSUMER_KEY",
        "OAUTH_ACCESS_TOKEN",
        "OAUTH_ACCESS_TOKEN_SECRET",
        "OAUTH_DH_PRIME",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {missing_vars}"
        )

    try:
        from skim.core.config import get_oauth_key_paths

        oauth_paths = get_oauth_key_paths()

        if not oauth_paths["signature"].exists():
            raise ValueError(
                f"Signature key file not found: {oauth_paths['signature']}"
            )
        if not oauth_paths["encryption"].exists():
            raise ValueError(
                f"Encryption key file not found: {oauth_paths['encryption']}"
            )

    except Exception as e:
        raise ValueError(f"OAuth key validation failed: {e}") from e


@pytest.fixture(scope="module")
def oauth_config():
    """Load real OAuth configuration from environment for integration tests."""
    validate_oauth_environment()

    from skim.core.config import get_oauth_key_paths

    oauth_paths = get_oauth_key_paths()

    return {
        "consumer_key": os.getenv("OAUTH_CONSUMER_KEY"),
        "access_token": os.getenv("OAUTH_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("OAUTH_ACCESS_TOKEN_SECRET"),
        "dh_prime_hex": os.getenv("OAUTH_DH_PRIME"),
        "signature_key_path": oauth_paths["signature"],
        "encryption_key_path": oauth_paths["encryption"],
    }


@pytest.fixture(scope="module")
def ibkr_client():
    """Create and connect IBKR client for integration testing."""
    validate_oauth_environment()

    import asyncio

    from skim.brokers.ibkr_client import IBKRClient

    client = IBKRClient(paper_trading=True)
    asyncio.run(client.connect())

    yield client

    if client.is_connected():
        asyncio.run(client.disconnect())


@pytest.fixture
def mock_ibkr_scanner(mocker):
    """Mock IBKRGapScanner for testing decoupled scanner"""
    from skim.brokers.ibkr_gap_scanner import IBKRGapScanner

    scanner = mocker.MagicMock(spec=IBKRGapScanner)
    return scanner


def create_gap_scan_result(gap_stocks=None, new_candidates=None):
    """Helper to create GapScanResult for test mocks"""
    from skim.validation.scanners import GapScanResult

    return GapScanResult(
        gap_stocks=gap_stocks or [],
        new_candidates=new_candidates or [],
    )


def create_monitoring_result(gap_stocks=None, triggered_candidates=None):
    """Helper to create MonitoringResult for test mocks"""
    from skim.validation.scanners import MonitoringResult

    return MonitoringResult(
        gap_stocks=gap_stocks or [],
        triggered_candidates=triggered_candidates or [],
    )


def create_or_tracking_result(gap_stocks=None, or_tracking_candidates=None):
    """Helper to create ORTrackingResult for test mocks"""
    from skim.validation.scanners import ORTrackingResult

    return ORTrackingResult(
        gap_stocks=gap_stocks or [],
        or_tracking_candidates=or_tracking_candidates or [],
    )
