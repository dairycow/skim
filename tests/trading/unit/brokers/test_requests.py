"""Tests for IBKRRequestClient in isolation"""

from unittest.mock import MagicMock

import pytest

from skim.infrastructure.brokers.ibkr.requests import IBKRRequestClient


@pytest.mark.unit
def test_request_client_initialization():
    """Test successful initialization of request client"""
    mock_auth = MagicMock()
    mock_auth.lst = None

    request_client = IBKRRequestClient(mock_auth)

    assert request_client._auth_manager is mock_auth
    assert request_client._http_client is None


@pytest.mark.unit
def test_set_http_client():
    """Test setting HTTP client"""
    mock_auth = MagicMock()
    mock_auth.lst = None
    mock_http_client = MagicMock()

    request_client = IBKRRequestClient(mock_auth)
    request_client.set_http_client(mock_http_client)

    assert request_client._http_client is mock_http_client


@pytest.mark.unit
def test_constants_defined():
    """Test that request client constants are properly defined"""
    assert IBKRRequestClient.BASE_URL == "https://api.ibkr.com/v1/api"
    assert IBKRRequestClient.REALM == "limited_poa"
