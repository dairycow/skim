import logging
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from skim.brokers.ibkr_client import IBKRAuthenticationError, IBKRClient


# Fixture to create a client instance without calling __init__
@pytest.fixture
def client_no_init() -> IBKRClient:
    return IBKRClient.__new__(IBKRClient)


def test_parse_account_id_from_accounts_list(client_no_init: IBKRClient):
    """Test parsing from the {'accounts': ['U123']} format."""
    response = {"accounts": ["U12345"]}
    assert client_no_init._parse_account_id(response) == "U12345"


def test_parse_account_id_from_accountid_key(client_no_init: IBKRClient):
    """Test parsing from the {'accountId': 'U123'} format."""
    response = {"accountId": "U67890"}
    assert client_no_init._parse_account_id(response) == "U67890"


def test_parse_account_id_from_list_of_dicts(client_no_init: IBKRClient):
    """Test parsing from a list of account dicts."""
    response = [{"id": "U54321", "account": "some_alias"}]
    assert client_no_init._parse_account_id(response) == "U54321"


def test_parse_account_id_from_list_of_strings(client_no_init: IBKRClient):
    """Test parsing from a simple list of strings."""
    response = ["U99999", "U88888"]
    assert client_no_init._parse_account_id(response) == "U99999"


def test_parse_account_id_from_id_key(client_no_init: IBKRClient):
    """Test parsing from a response with just an 'id' key."""
    response = {"id": "U11111"}
    assert client_no_init._parse_account_id(response) == "U11111"


def test_parse_account_id_empty_accounts_list(client_no_init: IBKRClient):
    """Test it returns None for an empty accounts list."""
    response = {"accounts": []}
    assert client_no_init._parse_account_id(response) is None


def test_parse_account_id_empty_list(client_no_init: IBKRClient):
    """Test it returns None for an empty list response."""
    response = []
    assert client_no_init._parse_account_id(response) is None


def test_parse_account_id_no_relevant_keys(client_no_init: IBKRClient):
    """Test it returns None when no relevant keys are in the dict."""
    response = {"some_other_key": "some_value"}
    assert client_no_init._parse_account_id(response) is None


@pytest.fixture
def minimal_client(monkeypatch) -> IBKRClient:
    """Create a minimally initialised IBKRClient for request-level tests."""
    client = IBKRClient.__new__(IBKRClient)

    # OAuth/session state
    client._consumer_key = "ck"
    client._access_token = "at"
    client._access_token_secret = "ats"
    client._dh_prime_hex = "01"
    client._signature_key_path = "sig"
    client._encryption_key_path = "enc"
    client._lst = "aW5pdGlhbA=="  # "initial" base64
    client._lst_expiration = None
    client._account_id = "DU123"
    client._connected = True
    client._paper_trading = True

    # Tickle thread state
    client._tickle_thread = None
    client._tickle_stop_event = None

    # HTTP client will be injected per test
    client._http_client = None
    return client


@pytest.mark.asyncio
async def test_request_recovers_from_410_with_lst_regeneration(
    minimal_client: IBKRClient, monkeypatch
):
    """Ensure 410 triggers LST regeneration and the request is retried successfully."""
    url = f"{minimal_client.BASE_URL}/iserver/test"

    resp_410 = httpx.Response(
        status_code=410,
        request=httpx.Request("GET", url),
        json={"error": "expired"},
    )
    resp_ok = httpx.Response(
        status_code=200,
        request=httpx.Request("GET", url),
        json={"result": "ok"},
    )

    http_client = AsyncMock()
    http_client.get = AsyncMock(side_effect=[resp_410, resp_ok])
    minimal_client._http_client = http_client

    regenerate = Mock(
        side_effect=lambda: setattr(minimal_client, "_lst", "bmV3bHN0")
    )  # "newlst" base64
    monkeypatch.setattr(minimal_client, "_generate_lst", regenerate)

    result = await minimal_client._request("GET", "/iserver/test")

    assert result == {"result": "ok"}
    regenerate.assert_called_once()
    assert minimal_client._lst == "bmV3bHN0"
    assert http_client.get.call_count == 2


@pytest.mark.asyncio
async def test_request_refreshes_expiring_lst_before_signing(
    minimal_client: IBKRClient, monkeypatch
):
    """LST should be proactively refreshed when expiration is near/past before sending the request."""
    minimal_client._lst_expiration = 0  # already expired
    url = f"{minimal_client.BASE_URL}/iserver/test"
    resp_ok = httpx.Response(
        status_code=200,
        request=httpx.Request("GET", url),
        headers={"Content-Length": "0"},
    )

    http_client = AsyncMock()
    http_client.get = AsyncMock(return_value=resp_ok)
    minimal_client._http_client = http_client

    regenerate = Mock(
        side_effect=lambda: setattr(minimal_client, "_lst", "cmVmcmVzaGVk")
    )  # "refreshed" base64
    monkeypatch.setattr(minimal_client, "_generate_lst", regenerate)

    result = await minimal_client._request("GET", "/iserver/test")

    assert result == {}
    regenerate.assert_called_once()
    assert minimal_client._lst == "cmVmcmVzaGVk"
    http_client.get.assert_called_once()


@pytest.mark.asyncio
async def test_request_raises_auth_error_after_failed_retry(
    minimal_client: IBKRClient, monkeypatch
):
    """If regeneration does not clear a 410/401, raise an authentication error with context."""
    url = f"{minimal_client.BASE_URL}/iserver/test"
    resp_410_a = httpx.Response(
        status_code=410,
        request=httpx.Request("GET", url),
        json={"error": "expired"},
    )
    resp_410_b = httpx.Response(
        status_code=410,
        request=httpx.Request("GET", url),
        json={"error": "still expired"},
    )

    http_client = AsyncMock()
    http_client.get = AsyncMock(side_effect=[resp_410_a, resp_410_b])
    minimal_client._http_client = http_client

    regenerate = Mock(
        side_effect=lambda: setattr(minimal_client, "_lst", "bmV3bHN0")
    )  # "newlst" base64
    monkeypatch.setattr(minimal_client, "_generate_lst", regenerate)

    with pytest.raises(IBKRAuthenticationError) as excinfo:
        await minimal_client._request("GET", "/iserver/test")

    assert "410" in str(excinfo.value)
    regenerate.assert_called_once()
    assert http_client.get.call_count == 2


def test_logging_bridge_routes_stdlib_to_loguru(monkeypatch):
    """Ensure the stdlib logging bridge forwards messages into loguru."""
    from loguru import logger

    messages: list[str] = []
    token = logger.add(messages.append, format="{message}")

    try:
        IBKRClient.install_logging_bridge()
        std_logger = logging.getLogger("skim.brokers.ibkr_client")
        std_logger.setLevel(logging.DEBUG)
        std_logger.info("bridge %s", "ok")
    finally:
        logger.remove(token)

    assert any("bridge ok" in message for message in messages)


@pytest.mark.asyncio
async def test_httpx_event_hooks_log_request_and_response(
    minimal_client: IBKRClient,
):
    """HTTPX request/response logs should flow into loguru."""
    from loguru import logger

    messages: list[str] = []
    token = logger.add(messages.append, format="{message}")

    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            status_code=200,
            json={"ok": True},
            request=request,
            headers={"x-test": "yes"},
        )
    )

    http_client = minimal_client._build_http_client(
        timeout=5, transport=transport
    )
    minimal_client._http_client = http_client

    try:
        await minimal_client._request("GET", "/iserver/test")
    finally:
        logger.remove(token)
        await http_client.aclose()

    assert any("GET" in msg and "/iserver/test" in msg for msg in messages)
    assert any("status=200" in msg for msg in messages)


# TODO: Add more unit tests for IBKRClient
# - Test __init__ raises ValueError if env vars are missing
# - Test connect() flow by mocking _request and _generate_lst
# - Test disconnect() calls _stop_tickle_thread and http_client.aclose
# - Test _request() retry logic with mocked httpx.AsyncClient responses
# - Test _request() LST regeneration on 401
# - Test _tickle_worker logic
