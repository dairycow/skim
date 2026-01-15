"""Pytest fixtures for IBKR broker unit tests"""

import json
import os
from pathlib import Path

import pytest

from skim.domain.models import MarketData, OrderResult


@pytest.fixture
def mock_ibkr_client(mocker):
    """Mock IBKRClient for testing

    Returns a mock IBKRClient with common success scenarios configured.
    Tests can override specific methods as needed.
    """
    mock_client = mocker.MagicMock()

    mock_client.is_connected.return_value = True
    mock_client.get_account.return_value = "DUN090463"

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
    from skim.trading.brokers.ibkr_client import IBKRClient

    original_env = {}
    required_vars = [
        "OAUTH_CONSUMER_KEY",
        "OAUTH_ACCESS_TOKEN",
        "OAUTH_ACCESS_TOKEN_SECRET",
        "OAUTH_DH_PRIME",
    ]

    for var in required_vars:
        original_env[var] = os.environ.get(var)

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
        client._connected = True
        client._lst = "test_lst_token"
        client._account_id = "DU1234567"
        yield client
    finally:
        for var, value in original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value


_FIXTURE_CACHE = {}


def _cached_fixture_load(fixtures_dir: Path, filename: str) -> dict:
    """Load and cache fixture files to avoid repeated file I/O.

    Loads each fixture file only once per session.
    """
    cache_key = str(fixtures_dir / "ibkr_responses" / filename)
    if cache_key not in _FIXTURE_CACHE:
        fixture_path = fixtures_dir / "ibkr_responses" / filename
        with open(fixture_path) as f:
            _FIXTURE_CACHE[cache_key] = json.load(f)
    return _FIXTURE_CACHE[cache_key]


@pytest.fixture(scope="session")
def fixtures_dir():
    """Return path to test fixtures directory

    Session scope: This is just a path lookup, immutable across all tests.
    """
    return Path(__file__).parent.parent.parent / "fixtures"


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
