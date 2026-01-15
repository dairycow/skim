"""Tests for IBKRAuthManager in isolation"""

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from skim.infrastructure.brokers.ibkr.auth import IBKRAuthManager
from skim.trading.core.config import Config


@pytest.mark.unit
def test_auth_manager_initialization_success():
    """Test successful initialization with all required OAuth credentials"""
    with (
        patch.dict(
            os.environ,
            {
                "OAUTH_CONSUMER_KEY": "test_key",
                "OAUTH_ACCESS_TOKEN": "test_token",
                "OAUTH_ACCESS_TOKEN_SECRET": "test_secret",
                "OAUTH_DH_PRIME": "test_prime",
            },
            clear=True,
        ),
        patch.object(Config, "from_env") as mock_config,
    ):
        mock_config.return_value = MagicMock(
            oauth_signature_key_path="/path/to/sig.pem",
            oauth_encryption_key_path="/path/to/enc.pem",
        )
        auth_manager = IBKRAuthManager()

        assert auth_manager.consumer_key == "test_key"
        assert auth_manager.access_token == "test_token"
        assert auth_manager.access_token_secret == "test_secret"
        assert auth_manager.dh_prime_hex == "test_prime"
        assert auth_manager.signature_key_path == "/path/to/sig.pem"
        assert auth_manager.encryption_key_path == "/path/to/enc.pem"
        assert auth_manager.lst is None
        assert auth_manager.lst_expiration is None


@pytest.mark.unit
def test_auth_manager_initialization_missing_credentials():
    """Test that initialization fails with missing OAuth credentials"""
    with (
        patch.dict(os.environ, {}, clear=True),
        patch.object(Config, "from_env") as mock_config,
    ):
        mock_config.return_value = MagicMock(
            oauth_signature_key_path="/path/to/sig.pem",
            oauth_encryption_key_path="/path/to/enc.pem",
        )
        with pytest.raises(ValueError) as exc_info:
            IBKRAuthManager()

        assert "Missing OAuth configuration" in str(exc_info.value)


@pytest.mark.unit
def test_lst_property_setter():
    """Test LST property getter and setter"""
    with (
        patch.dict(
            os.environ,
            {
                "OAUTH_CONSUMER_KEY": "test_key",
                "OAUTH_ACCESS_TOKEN": "test_token",
                "OAUTH_ACCESS_TOKEN_SECRET": "test_secret",
                "OAUTH_DH_PRIME": "test_prime",
            },
            clear=True,
        ),
        patch.object(Config, "from_env") as mock_config,
    ):
        mock_config.return_value = MagicMock(
            oauth_signature_key_path="/path/to/sig.pem",
            oauth_encryption_key_path="/path/to/enc.pem",
        )
        auth_manager = IBKRAuthManager()

        auth_manager.lst = "test_lst_token"
        assert auth_manager.lst == "test_lst_token"


@pytest.mark.unit
def test_lst_expiration_property_setter():
    """Test LST expiration property getter and setter"""
    with (
        patch.dict(
            os.environ,
            {
                "OAUTH_CONSUMER_KEY": "test_key",
                "OAUTH_ACCESS_TOKEN": "test_token",
                "OAUTH_ACCESS_TOKEN_SECRET": "test_secret",
                "OAUTH_DH_PRIME": "test_prime",
            },
            clear=True,
        ),
        patch.object(Config, "from_env") as mock_config,
    ):
        mock_config.return_value = MagicMock(
            oauth_signature_key_path="/path/to/sig.pem",
            oauth_encryption_key_path="/path/to/enc.pem",
        )
        auth_manager = IBKRAuthManager()

        expiration = 1234567890000
        auth_manager.lst_expiration = expiration
        assert auth_manager.lst_expiration == expiration


@pytest.mark.unit
def test_is_expiring_with_no_expiration():
    """Test is_expiring returns False when no expiration is set"""
    with (
        patch.dict(
            os.environ,
            {
                "OAUTH_CONSUMER_KEY": "test_key",
                "OAUTH_ACCESS_TOKEN": "test_token",
                "OAUTH_ACCESS_TOKEN_SECRET": "test_secret",
                "OAUTH_DH_PRIME": "test_prime",
            },
            clear=True,
        ),
        patch.object(Config, "from_env") as mock_config,
    ):
        mock_config.return_value = MagicMock(
            oauth_signature_key_path="/path/to/sig.pem",
            oauth_encryption_key_path="/path/to/enc.pem",
        )
        auth_manager = IBKRAuthManager()

        assert auth_manager.is_expiring() is False


@pytest.mark.unit
def test_is_expiring_when_expiring_soon():
    """Test is_expiring returns True when LST is close to expiration"""

    with (
        patch.dict(
            os.environ,
            {
                "OAUTH_CONSUMER_KEY": "test_key",
                "OAUTH_ACCESS_TOKEN": "test_token",
                "OAUTH_ACCESS_TOKEN_SECRET": "test_secret",
                "OAUTH_DH_PRIME": "test_prime",
            },
            clear=True,
        ),
        patch.object(Config, "from_env") as mock_config,
    ):
        mock_config.return_value = MagicMock(
            oauth_signature_key_path="/path/to/sig.pem",
            oauth_encryption_key_path="/path/to/enc.pem",
        )
        auth_manager = IBKRAuthManager()

        # Set expiration to 5 minutes from now (within 5 minute default skew)
        expiration = int(
            (datetime.now() + timedelta(minutes=5)).timestamp() * 1000
        )
        auth_manager.lst_expiration = expiration

        assert auth_manager.is_expiring() is True


@pytest.mark.unit
def test_is_expiring_when_not_expiring():
    """Test is_expiring returns False when LST is not close to expiration"""

    with (
        patch.dict(
            os.environ,
            {
                "OAUTH_CONSUMER_KEY": "test_key",
                "OAUTH_ACCESS_TOKEN": "test_token",
                "OAUTH_ACCESS_TOKEN_SECRET": "test_secret",
                "OAUTH_DH_PRIME": "test_prime",
            },
            clear=True,
        ),
        patch.object(Config, "from_env") as mock_config,
    ):
        mock_config.return_value = MagicMock(
            oauth_signature_key_path="/path/to/sig.pem",
            oauth_encryption_key_path="/path/to/enc.pem",
        )
        auth_manager = IBKRAuthManager()

        # Set expiration to 1 hour from now (outside 5 minute default skew)
        expiration = int(
            (datetime.now() + timedelta(hours=1)).timestamp() * 1000
        )
        auth_manager.lst_expiration = expiration

        assert auth_manager.is_expiring() is False
