"""Pytest fixtures for Skim trading bot tests"""

import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

from skim.data.database import Database
from skim.data.models import (
    GapStockInPlay,
    MarketData,
    NewsStockInPlay,
    OpeningRange,
    OrderResult,
    Position,
    TradeableCandidate,
)

# =============================================================================
# Global Test Setup
# =============================================================================

# Add src to Python path for all tests
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Load environment variables from .env file for all tests
# This ensures OAuth credentials are available for integration tests
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)


# =============================================================================
# Fixture Data Caching (Phase 3 Optimisation)
# =============================================================================

_FIXTURE_CACHE = {}


def _cached_fixture_load(fixtures_dir: Path, filename: str) -> dict:
    """Load and cache fixture files to avoid repeated file I/O.

    This implements Phase 3 optimisation: Fixture Data Caching.
    Loads each fixture file only once per session.
    """
    cache_key = str(fixtures_dir / "ibkr_responses" / filename)
    if cache_key not in _FIXTURE_CACHE:
        fixture_path = fixtures_dir / "ibkr_responses" / filename
        with open(fixture_path) as f:
            _FIXTURE_CACHE[cache_key] = json.load(f)
    return _FIXTURE_CACHE[cache_key]


@pytest.fixture
def test_db():
    """In-memory SQLite database for testing"""
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture(scope="session")
def sample_gap_candidate() -> GapStockInPlay:
    """Sample gap-only candidate for testing

    Session scope: Immutable dataclass, safe to share across all tests.
    """
    return GapStockInPlay(
        ticker="RIO",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=4.2,
        conid=8645,
    )


@pytest.fixture(scope="session")
def sample_news_candidate() -> NewsStockInPlay:
    """Sample news-only candidate for testing

    Session scope: Immutable dataclass, safe to share across all tests.
    """
    return NewsStockInPlay(
        ticker="CBA",
        scan_date="2025-11-03",
        status="watching",
        headline="Trading Halt",
    )


@pytest.fixture(scope="session")
def sample_opening_range() -> OpeningRange:
    """Sample opening range for testing

    Session scope: Immutable dataclass, safe to share across all tests.
    """
    return OpeningRange(
        ticker="BHP",
        or_high=47.80,
        or_low=45.90,
        sample_date="2025-11-03T10:10:00",
    )


@pytest.fixture(scope="session")
def sample_tradeable_candidate() -> TradeableCandidate:
    """Sample tradeable candidate for testing

    Session scope: Immutable dataclass, safe to share across all tests.
    """
    return TradeableCandidate(
        ticker="BHP",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=5.0,
        conid=8644,
        headline="Results Released",
        or_high=47.80,
        or_low=45.90,
    )


@pytest.fixture(scope="session")
def sample_position() -> Position:
    """Sample open position for testing

    Session scope: Immutable dataclass, safe to share across all tests.
    """
    return Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
        status="open",
    )


@pytest.fixture(scope="session")
def sample_market_data() -> MarketData:
    """Sample market data for testing

    Session scope: Immutable dataclass, safe to share across all tests.
    """
    return MarketData(
        ticker="BHP",
        conid="8644",
        last_price=46.05,
        high=47.00,
        low=45.50,
        bid=46.00,
        ask=46.10,
        bid_size=100,
        ask_size=200,
        volume=1_000_000,
        open=46.50,
        prior_close=45.80,
        change_percent=0.54,
    )


@pytest.fixture
def mock_ibkr_client(mocker):
    """Mock IBKRClient for testing

    Returns a mock IBKRClient with common success scenarios configured.
    Tests can override specific methods as needed.
    """
    mock_client = mocker.MagicMock()

    # Configure default successful behaviors
    mock_client.is_connected.return_value = True
    mock_client.get_account.return_value = "DUN090463"

    # Mock successful market data response
    mock_market_data = MarketData(
        ticker="BHP",
        conid="8644",
        last_price=46.50,
        high=47.20,
        low=45.80,
        bid=46.45,
        ask=46.55,
        bid_size=150,
        ask_size=250,
        volume=1_000_000,
        open=46.30,
        prior_close=45.90,
        change_percent=1.31,
    )
    mock_client.get_market_data.return_value = mock_market_data

    # Mock successful order placement
    mock_order_result = OrderResult(
        order_id="order_123",
        ticker="BHP",
        action="BUY",
        quantity=100,
        filled_price=46.50,
        status="filled",
    )
    mock_client.place_order.return_value = mock_order_result

    return mock_client


@pytest.fixture
def ibkr_client_mock_oauth():
    """Create real IBKRClient instance with mocked OAuth environment.

    This fixture is used for unit tests that need to test actual IBKRClient
    methods without requiring real OAuth credentials. It sets up dummy OAuth
    environment variables and returns a client instance with mocked connection
    state.

    Returns:
        IBKRClient: Client instance with mocked OAuth env and connection state

    Note:
        This is different from `mock_ibkr_client` which returns a MagicMock.
        Use this when you need to test actual IBKRClient methods.

    Session scope: This fixture is created once per test session and reused
    across all tests. Since tests use @responses.activate to mock HTTP calls,
    shared state is not an issue.
    """
    from skim.brokers.ibkr_client import IBKRClient

    # Store original environment values
    original_env = {}
    required_vars = [
        "OAUTH_CONSUMER_KEY",
        "OAUTH_ACCESS_TOKEN",
        "OAUTH_ACCESS_TOKEN_SECRET",
        "OAUTH_DH_PRIME",
    ]

    for var in required_vars:
        original_env[var] = os.environ.get(var)

    # Set dummy OAuth values (use valid hex for DH prime)
    os.environ["OAUTH_CONSUMER_KEY"] = "test_consumer_key"
    os.environ["OAUTH_ACCESS_TOKEN"] = "test_access_token"
    os.environ["OAUTH_ACCESS_TOKEN_SECRET"] = (
        "dGVzdF9hY2Nlc3NfdG9rZW5fc2VjcmV0X3ZhbGlkX2Jhc2U2NA=="
    )
    os.environ["OAUTH_DH_PRIME"] = (
        "00ffffffffffffffffc90fdaa22168c234c4c6628b80dc1cd129024e088a67cc74020bbea63b139b22514a08798e3404ddef9519b3cd3a431b302b0a6df25f14374fe1356d6d51c245e485b576625e7ec6f44c42e9a637ed6b0bff5cb6f406b7edee386bfb5a899fa5ae9f24117c4b1fe649286651ece65381ffffffffffffffff"
    )

    try:
        client = IBKRClient(paper_trading=True)
        # Mock connection state to avoid actual API calls
        client._connected = True
        client._lst = "test_lst_token"
        client._account_id = "DU1234567"
        yield client
    finally:
        # Restore original environment
        for var, value in original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value


# ==============================================================================
# TradingBot Testing Fixtures
# ==============================================================================


@pytest.fixture
def mock_bot_config():
    """Create mock configuration for TradingBot tests.

    Returns a Mock object configured with standard trading bot parameters.
    Tests can override specific attributes as needed.

    Returns:
        Mock: Mock config with standard bot parameters
    """
    from unittest.mock import Mock

    from skim.core.config import Config, ScannerConfig

    config = Mock(spec=Config)
    config.scanner_config = ScannerConfig(gap_threshold=3.0)
    config.max_positions = 5
    config.max_position_size = 1000
    config.stop_loss_pct = 5.0
    config.paper_trading = True
    config.discord_webhook_url = "https://discord-webhook.com"
    config.db_path = ":memory:"
    config.scanner_config = ScannerConfig()
    return config


@pytest.fixture(scope="session")
def scanner_config():
    """Create ScannerConfig instance for testing

    Session scope: This is a read-only immutable configuration object,
    so it's safe to share across all tests.
    """
    from skim.core.config import ScannerConfig

    return ScannerConfig(
        gap_threshold=3.0,
        volume_filter=10000,
        price_filter=0.05,
        or_duration_minutes=10,
        or_poll_interval_seconds=30,
        gap_fill_tolerance=0.05,
        or_breakout_buffer=0.1,
    )


@pytest.fixture
def mock_trading_bot(mock_bot_config):
    """Create TradingBot instance with all dependencies mocked.

    This fixture patches all external dependencies (Database, IBKRClient,
    IBKRGapScanner, ASXAnnouncementScanner, DiscordNotifier) and returns
    a TradingBot instance ready for testing.

    The bot instance has access to mocked versions of:
    - bot.db (Database)
    - bot.ib_client (IBKRClient)
    - bot.ibkr_scanner (IBKRGapScanner)
    - bot.asx_scanner (ASXAnnouncementScanner)
    - bot.discord (DiscordNotifier)

    Args:
        mock_bot_config: Mock configuration fixture

    Returns:
        TradingBot: Bot instance with all dependencies mocked

    Example:
        def test_something(mock_trading_bot):
            mock_trading_bot.db.get_candidates.return_value = [...]
            result = mock_trading_bot.scan()
            assert result == expected
    """
    from unittest.mock import patch

    from skim.core.bot import TradingBot

    with (
        patch("skim.core.bot.Database"),
        patch("skim.core.bot.IBKRClient"),
        patch("skim.core.bot.IBKRMarketData"),
        patch("skim.core.bot.IBKROrders"),
        patch("skim.core.bot.IBKRGapScanner"),
        patch("skim.core.bot.Scanner"),
        patch("skim.core.bot.Trader"),
        patch("skim.core.bot.Monitor"),
        patch("skim.core.bot.DiscordNotifier"),
    ):
        bot = TradingBot(mock_bot_config)
        yield bot


# ==============================================================================
# OAuth Testing Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def fixtures_dir():
    """Return path to test fixtures directory

    Session scope: This is just a path lookup, immutable across all tests.
    """
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def test_rsa_keys(fixtures_dir):
    """Provide paths to test RSA keys

    These are test-only keys safe to commit to version control.
    They should NEVER be used in production.

    Session scope: These are static paths to test files, immutable
    across all tests.
    """
    sig_key = fixtures_dir / "rsa_keys/test_signature_key.pem"
    enc_key = fixtures_dir / "rsa_keys/test_encryption_key.pem"

    assert sig_key.exists(), f"Test signature key not found: {sig_key}"
    assert enc_key.exists(), f"Test encryption key not found: {enc_key}"

    return str(sig_key), str(enc_key)


@pytest.fixture
def mock_oauth_env(monkeypatch, test_rsa_keys):
    """Set up OAuth environment variables for testing"""
    sig_path, enc_path = test_rsa_keys

    # Test OAuth credentials (not real, safe for testing)
    monkeypatch.setenv("OAUTH_CONSUMER_KEY", "TEST_CONSUMER_KEY")
    monkeypatch.setenv("OAUTH_ACCESS_TOKEN", "test_access_token_123")
    monkeypatch.setenv(
        "OAUTH_ACCESS_TOKEN_SECRET",
        "dGVzdF9lbmNyeXB0ZWRfc2VjcmV0X3Rva2VuXzEyMzQ1Njc4OTA=",
    )
    monkeypatch.setenv(
        "OAUTH_DH_PRIME",
        "00f4c0ac1c6a120cffe7c0438769be9f35a721c6c7aed77a6a676a2811fb4277",
    )
    monkeypatch.setenv("OAUTH_SIGNATURE_PATH", sig_path)
    monkeypatch.setenv("OAUTH_ENCRYPTION_PATH", enc_path)


@pytest.fixture(scope="session")
def load_fixture(fixtures_dir):
    """Helper to load JSON fixture files with caching.

    Session scope: Fixture loading is immutable and cached.
    Implements Phase 3 optimisation: Eliminates repeated file I/O
    by caching loaded fixtures in memory for the entire session.
    """

    def _load(filename):
        return _cached_fixture_load(fixtures_dir, filename)

    return _load


@pytest.fixture(scope="session")
def mock_lst_response(load_fixture):
    """Mock LST generation response from IBKR

    Session scope: Fixture data is immutable.
    """
    return load_fixture("lst_success.json")


@pytest.fixture(scope="session")
def mock_session_init_response(load_fixture):
    """Mock session init response from IBKR

    Session scope: Fixture data is immutable.
    """
    return load_fixture("session_init_success.json")


@pytest.fixture(scope="session")
def mock_account_list_response(load_fixture):
    """Mock account list response from IBKR

    Session scope: Fixture data is immutable.
    """
    return load_fixture("account_list.json")


@pytest.fixture(scope="session")
def mock_contract_search_bhp(load_fixture):
    """Mock contract search response for BHP

    Session scope: Fixture data is immutable.
    """
    return load_fixture("contract_search_bhp.json")


@pytest.fixture(scope="session")
def mock_order_placed_response(load_fixture):
    """Mock order placement response from IBKR

    Session scope: Fixture data is immutable.
    """
    return load_fixture("order_placed.json")


# =============================================================================
# Integration Test Fixtures
# =============================================================================


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

    # Validate OAuth key files exist using the same logic as the main config
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

    # Use the same path detection logic as the main config
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

    # Create and connect client
    client = IBKRClient(paper_trading=True)
    asyncio.run(client.connect())

    yield client

    # Cleanup
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


# =============================================================================
# pytest-timeout Configuration
# =============================================================================


def pytest_configure(config):
    """Configure pytest-timeout to skip integration tests"""
    config.addinivalue_line(
        "markers",
        "timeout: set test timeout in seconds (integration tests have no limit)",
    )


@pytest.fixture
def _disable_timeout_for_integration(request):
    """Disable timeout for integration tests that need real API calls"""
    if "integration" in request.keywords or "manual" in request.keywords:
        request.getfixturevalue("_disallow_timeout")


@pytest.hookimpl
def pytest_collection_modifyitems(config, items):
    """Mark integration tests to not have timeouts"""
    for item in items:
        if item.get_closest_marker("integration") or item.get_closest_marker(
            "manual"
        ):
            # Add a high timeout for integration tests (300 seconds / 5 minutes)
            item.add_marker(pytest.mark.timeout(300))
