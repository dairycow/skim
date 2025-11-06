"""Pytest fixtures for Skim trading bot tests"""

import json
from datetime import datetime
from pathlib import Path

import pytest

from skim.brokers.ib_interface import OrderResult
from skim.data.database import Database
from skim.data.models import Candidate, MarketData, Position, Trade


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
        "dGVzdF9lbmNyeXB0ZWRfc2VjcmV0X3Rva2VuXzEyMzQ1Njc4OTA="
    )
    monkeypatch.setenv(
        "OAUTH_DH_PRIME",
        "00f4c0ac1c6a120cffe7c0438769be9f35a721c6c7aed77a6a676a2811fb4277"
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
