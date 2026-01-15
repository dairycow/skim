"""Tests for IBKRClientFacade as a thin orchestrator"""

from unittest.mock import MagicMock, patch

import pytest

from skim.infrastructure.brokers.ibkr import IBKRClientFacade
from skim.infrastructure.brokers.ibkr.auth import IBKRAuthManager
from skim.infrastructure.brokers.ibkr.connection import IBKRConnectionManager
from skim.infrastructure.brokers.ibkr.requests import IBKRRequestClient


@pytest.mark.unit
def test_facade_initialization():
    """Test that facade properly initializes all manager components"""
    with (
        patch.object(IBKRAuthManager, "__init__", lambda self: None),
        patch.object(IBKRRequestClient, "__init__", lambda self, _: None),
        patch.object(
            IBKRConnectionManager,
            "__init__",
            lambda self, *args, **kwargs: None,
        ),
    ):
        facade = IBKRClientFacade(paper_trading=True)

        assert hasattr(facade, "_auth_manager")
        assert hasattr(facade, "_request_client")
        assert hasattr(facade, "_connection_manager")


@pytest.mark.unit
def test_is_connected_delegates_to_connection_manager():
    """Test that is_connected properly delegates to connection manager"""
    facade = IBKRClientFacade.__new__(IBKRClientFacade)
    mock_connection = MagicMock()
    mock_connection.is_connected = True
    facade._connection_manager = mock_connection

    result = facade.is_connected()

    assert result is True


@pytest.mark.unit
def test_account_id_delegates_to_connection_manager():
    """Test that account_id properly delegates to connection manager"""
    facade = IBKRClientFacade.__new__(IBKRClientFacade)
    mock_connection = MagicMock()
    mock_connection.account_id = "DU1234567"
    facade._connection_manager = mock_connection

    result = facade.account_id

    assert result == "DU1234567"


@pytest.mark.unit
def test_get_account_delegates_to_connection_manager():
    """Test that get_account properly delegates to connection manager"""
    facade = IBKRClientFacade.__new__(IBKRClientFacade)
    mock_connection = MagicMock()
    mock_connection.get_account = MagicMock(return_value="DU1234567")
    facade._connection_manager = mock_connection

    result = facade.get_account()

    assert result == "DU1234567"
    mock_connection.get_account.assert_called_once()


@pytest.mark.unit
def test_auth_manager_property_returns_auth_manager():
    """Test that auth_manager property returns auth_manager instance"""
    facade = IBKRClientFacade.__new__(IBKRClientFacade)
    mock_auth = MagicMock()
    facade._auth_manager = mock_auth

    result = facade.auth_manager

    assert result is mock_auth


@pytest.mark.unit
def test_request_client_property_returns_request_client():
    """Test that request_client property returns request_client instance"""
    facade = IBKRClientFacade.__new__(IBKRClientFacade)
    mock_request = MagicMock()
    facade._request_client = mock_request

    result = facade.request_client

    assert result is mock_request


@pytest.mark.unit
def test_install_logging_bridge_calls_request_client():
    """Test that install_logging_bridge properly delegates to request client"""
    with patch.object(
        IBKRRequestClient, "install_logging_bridge", MagicMock()
    ) as mock_install:
        IBKRClientFacade.install_logging_bridge()

        mock_install.assert_called_once()


@pytest.mark.unit
def test_constants_defined():
    """Test that facade constants are properly defined"""
    assert IBKRClientFacade.BASE_URL == "https://api.ibkr.com/v1/api"
    assert IBKRClientFacade.REALM == "limited_poa"
