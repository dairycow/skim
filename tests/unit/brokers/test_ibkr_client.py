import pytest

from skim.brokers.ibkr_client import IBKRClient


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


# TODO: Add more unit tests for IBKRClient
# - Test __init__ raises ValueError if env vars are missing
# - Test connect() flow by mocking _request and _generate_lst
# - Test disconnect() calls _stop_tickle_thread and http_client.aclose
# - Test _request() retry logic with mocked httpx.AsyncClient responses
# - Test _request() LST regeneration on 401
# - Test _tickle_worker logic
