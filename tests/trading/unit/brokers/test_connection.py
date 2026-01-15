"""Tests for IBKRConnectionManager in isolation"""

from unittest.mock import MagicMock

import pytest

from skim.infrastructure.brokers.ibkr.connection import IBKRConnectionManager
from skim.infrastructure.brokers.ibkr.exceptions import IBKRConnectionError


@pytest.mark.unit
def test_connection_manager_initialization():
    """Test successful initialization of connection manager"""
    mock_auth = MagicMock()
    mock_request = MagicMock()
    mock_auth.lst = None

    connection_manager = IBKRConnectionManager(
        mock_auth, mock_request, paper_trading=True
    )

    assert connection_manager._auth_manager is mock_auth
    assert connection_manager._request_client is mock_request
    assert connection_manager._paper_trading is True
    assert connection_manager._account_id is None
    assert connection_manager._connected is False


@pytest.mark.unit
def test_is_connected_returns_connection_state():
    """Test that is_connected reflects the actual connection state"""
    mock_auth = MagicMock()
    mock_request = MagicMock()
    mock_auth.lst = "valid_lst_token"

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    connection_manager._connected = True

    assert connection_manager.is_connected is True

    connection_manager._connected = False
    assert connection_manager.is_connected is False


@pytest.mark.unit
def test_is_connected_returns_false_when_lst_is_none():
    """Test that is_connected returns False when LST is None"""
    mock_auth = MagicMock()
    mock_request = MagicMock()
    mock_auth.lst = None

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    connection_manager._connected = True

    assert connection_manager.is_connected is False


@pytest.mark.unit
def test_get_account_returns_account_id():
    """Test that get_account returns account ID when connected"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    connection_manager._account_id = "DU1234567"

    result = connection_manager.get_account()

    assert result == "DU1234567"


@pytest.mark.unit
def test_get_account_raises_error_when_not_connected():
    """Test that get_account raises IBKRConnectionError when not connected"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    connection_manager._account_id = None

    with pytest.raises(IBKRConnectionError) as exc_info:
        connection_manager.get_account()

    assert "Not connected" in str(exc_info.value)


@pytest.mark.unit
def test_parse_account_id_from_accounts_list():
    """Test parsing account ID from accounts list format"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    response = {"accounts": ["DU1234567"]}

    result = connection_manager._parse_account_id(response)

    assert result == "DU1234567"


@pytest.mark.unit
def test_parse_account_id_from_account_id_key():
    """Test parsing account ID from accountId key"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    response = {"accountId": "DU1234567"}

    result = connection_manager._parse_account_id(response)

    assert result == "DU1234567"


@pytest.mark.unit
def test_parse_account_id_from_id_key():
    """Test parsing account ID from id key"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    response = {"id": "DU1234567"}

    result = connection_manager._parse_account_id(response)

    assert result == "DU1234567"


@pytest.mark.unit
def test_parse_account_id_from_list_of_dicts():
    """Test parsing account ID from list of account dicts"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    response = [{"accountId": "DU1234567"}]

    result = connection_manager._parse_account_id(response)

    assert result == "DU1234567"


@pytest.mark.unit
def test_parse_account_id_from_list_of_strings():
    """Test parsing account ID from list of account strings"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    response = ["DU1234567", "DU1234568"]

    result = connection_manager._parse_account_id(response)

    assert result == "DU1234567"


@pytest.mark.unit
def test_parse_account_id_returns_none_for_empty_list():
    """Test parsing account ID returns None for empty accounts list"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    response = {"accounts": []}

    result = connection_manager._parse_account_id(response)

    assert result is None


@pytest.mark.unit
def test_parse_account_id_returns_none_for_invalid_response():
    """Test parsing account ID returns None for invalid response"""
    mock_auth = MagicMock()
    mock_request = MagicMock()

    connection_manager = IBKRConnectionManager(mock_auth, mock_request)
    response = {"some_other_key": "value"}

    result = connection_manager._parse_account_id(response)

    assert result is None


@pytest.mark.unit
def test_constants_defined():
    """Test that connection manager constants are properly defined"""
    assert IBKRConnectionManager.BASE_URL == "https://api.ibkr.com/v1/api"
