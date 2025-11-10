"""Pytest fixtures for Skim trading bot tests"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest
from dotenv import load_dotenv

from skim.brokers.ib_interface import OrderResult
from skim.data.database import Database
from skim.data.models import Candidate, MarketData, Position, Trade

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


@pytest.fixture
def test_db():
    """In-memory SQLite database for testing"""
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture
def sample_candidate() -> Candidate:
    """Sample candidate for testing"""
    return Candidate(
        ticker="BHP",
        headline="Strong earnings report",
        scan_date="2025-11-03",
        status="watching",
        gap_percent=3.5,
        prev_close=45.20,
    )


@pytest.fixture
def sample_position() -> Position:
    """Sample open position for testing"""
    return Position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
        entry_date="2025-11-03T10:15:00",
        status="open",
        half_sold=False,
    )


@pytest.fixture
def sample_trade() -> Trade:
    """Sample trade for testing"""
    return Trade(
        ticker="BHP",
        action="BUY",
        quantity=100,
        price=46.50,
        timestamp="2025-11-03T10:15:00",
        position_id=1,
    )


@pytest.fixture
def sample_market_data() -> MarketData:
    """Sample market data for testing"""
    return MarketData(
        ticker="BHP",
        bid=46.00,
        ask=46.10,
        last=46.05,
        high=47.00,
        low=45.50,
        volume=1_000_000,
        timestamp=datetime.now(),
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
    from skim.brokers.ib_interface import MarketData as IBMarketData

    mock_market_data = IBMarketData(
        ticker="BHP",
        last_price=46.50,
        bid=46.45,
        ask=46.55,
        volume=1_000_000,
        low=45.80,
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
    """
    from skim.brokers.ibkr_client import IBKRClient

    # Store original environment values
    original_env = {}
    required_vars = [
        "OAUTH_CONSUMER_KEY",
        "OAUTH_ACCESS_TOKEN",
        "OAUTH_ACCESS_TOKEN_SECRET",
        "OAUTH_DH_PRIME",
        "OAUTH_SIGNATURE_PATH",
        "OAUTH_ENCRYPTION_PATH",
    ]

    for var in required_vars:
        original_env[var] = os.environ.get(var)
        os.environ[var] = "test_value"

    # Set dummy file paths for keys
    os.environ["OAUTH_SIGNATURE_PATH"] = "/tmp/test_signature.pem"
    os.environ["OAUTH_ENCRYPTION_PATH"] = "/tmp/test_encryption.pem"

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
    config.gap_threshold = 3.0
    config.max_positions = 5
    config.max_position_size = 1000
    config.stop_loss_pct = 5.0
    config.paper_trading = True
    config.discord_webhook_url = "https://discord-webhook.com"
    config.db_path = ":memory:"
    config.scanner_config = ScannerConfig()
    return config


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
        patch("skim.core.bot.IBKRGapScanner"),
        patch("skim.core.bot.ASXAnnouncementScanner"),
        patch("skim.core.bot.DiscordNotifier"),
    ):
        bot = TradingBot(mock_bot_config)
        yield bot


# ==============================================================================
# OAuth Testing Fixtures
# ==============================================================================


@pytest.fixture
def fixtures_dir():
    """Return path to test fixtures directory"""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def test_rsa_keys(fixtures_dir):
    """Provide paths to test RSA keys

    These are test-only keys safe to commit to version control.
    They should NEVER be used in production.
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


@pytest.fixture
def load_fixture(fixtures_dir):
    """Helper to load JSON fixture files"""

    def _load(filename):
        fixture_path = fixtures_dir / "ibkr_responses" / filename
        with open(fixture_path) as f:
            return json.load(f)

    return _load


@pytest.fixture
def mock_lst_response(load_fixture):
    """Mock LST generation response from IBKR"""
    return load_fixture("lst_success.json")


@pytest.fixture
def mock_session_init_response(load_fixture):
    """Mock session init response from IBKR"""
    return load_fixture("session_init_success.json")


@pytest.fixture
def mock_account_list_response(load_fixture):
    """Mock account list response from IBKR"""
    return load_fixture("account_list.json")


@pytest.fixture
def mock_contract_search_bhp(load_fixture):
    """Mock contract search response for BHP"""
    return load_fixture("contract_search_bhp.json")


@pytest.fixture
def mock_order_placed_response(load_fixture):
    """Mock order placement response from IBKR"""
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
        "OAUTH_SIGNATURE_PATH",
        "OAUTH_ENCRYPTION_PATH",
    ]

    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        raise ValueError(
            f"Missing required environment variables: {missing_vars}"
        )

    # Validate key files exist
    signature_path = Path(os.getenv("OAUTH_SIGNATURE_PATH", ""))
    encryption_path = Path(os.getenv("OAUTH_ENCRYPTION_PATH", ""))

    if not signature_path.exists():
        raise ValueError(f"Signature key file not found: {signature_path}")
    if not encryption_path.exists():
        raise ValueError(f"Encryption key file not found: {encryption_path}")


@pytest.fixture(scope="module")
def oauth_config():
    """Load real OAuth configuration from environment for integration tests."""
    validate_oauth_environment()

    return {
        "consumer_key": os.getenv("OAUTH_CONSUMER_KEY"),
        "access_token": os.getenv("OAUTH_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("OAUTH_ACCESS_TOKEN_SECRET"),
        "dh_prime_hex": os.getenv("OAUTH_DH_PRIME"),
        "signature_key_path": Path(os.getenv("OAUTH_SIGNATURE_PATH", "")),
        "encryption_key_path": Path(os.getenv("OAUTH_ENCRYPTION_PATH", "")),
    }


@pytest.fixture(scope="module")
def ibkr_client():
    """Create and connect IBKR client for integration testing."""
    validate_oauth_environment()

    from skim.brokers.ibkr_client import IBKRClient

    # Create and connect client
    client = IBKRClient(paper_trading=True)
    client.connect(host="", port=0, client_id=0)

    yield client

    # Cleanup
    if client.is_connected():
        client.disconnect()
