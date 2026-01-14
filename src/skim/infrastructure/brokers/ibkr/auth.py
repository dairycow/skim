"""IBKRAuthManager - OAuth LST generation and validation"""

import os
from datetime import datetime
from typing import cast

from loguru import logger

from skim.trading.core.config import Config

from .exceptions import IBKRAuthenticationError


class IBKRAuthManager:
    """Manages OAuth authentication for IBKR Client Portal API

    Responsibilities:
    - OAuth LST generation via generate_lst()
    - LST expiration checking
    - OAuth key path management
    """

    def __init__(self) -> None:
        """Initialize auth manager with OAuth credentials from environment

        Raises:
            ValueError: If required OAuth environment variables are missing
        """
        self._consumer_key = os.getenv("OAUTH_CONSUMER_KEY")
        self._access_token = os.getenv("OAUTH_ACCESS_TOKEN")
        self._access_token_secret = os.getenv("OAUTH_ACCESS_TOKEN_SECRET")
        self._dh_prime_hex = os.getenv("OAUTH_DH_PRIME")

        config = Config.from_env()
        self._signature_key_path = config.oauth_signature_key_path
        self._encryption_key_path = config.oauth_encryption_key_path

        required_vars = {
            "OAUTH_CONSUMER_KEY": self._consumer_key,
            "OAUTH_ACCESS_TOKEN": self._access_token,
            "OAUTH_ACCESS_TOKEN_SECRET": self._access_token_secret,
            "OAUTH_DH_PRIME": self._dh_prime_hex,
            "signature_key_path": self._signature_key_path,
            "encryption_key_path": self._encryption_key_path,
        }
        missing = [k for k, v in required_vars.items() if v is None]
        if missing:
            raise ValueError(f"Missing OAuth configuration: {missing}")

        self._lst: str | None = None
        self._lst_expiration: int | None = None

    @property
    def lst(self) -> str | None:
        """Get current LST"""
        return self._lst

    @lst.setter
    def lst(self, value: str) -> None:
        """Set current LST"""
        self._lst = value

    @property
    def lst_expiration(self) -> int | None:
        """Get LST expiration timestamp in milliseconds"""
        return self._lst_expiration

    @lst_expiration.setter
    def lst_expiration(self, value: int) -> None:
        """Set LST expiration timestamp in milliseconds"""
        self._lst_expiration = value

    @property
    def consumer_key(self) -> str:
        """Get OAuth consumer key"""
        return cast(str, self._consumer_key)

    @property
    def access_token(self) -> str:
        """Get OAuth access token"""
        return cast(str, self._access_token)

    @property
    def access_token_secret(self) -> str:
        """Get OAuth access token secret"""
        return cast(str, self._access_token_secret)

    @property
    def dh_prime_hex(self) -> str:
        """Get OAuth DH prime hex"""
        return cast(str, self._dh_prime_hex)

    @property
    def signature_key_path(self) -> str:
        """Get OAuth signature key path"""
        return cast(str, self._signature_key_path)

    @property
    def encryption_key_path(self) -> str:
        """Get OAuth encryption key path"""
        return cast(str, self._encryption_key_path)

    def generate_lst(self, realm: str = "limited_poa") -> None:
        """Generate new Live Session Token via OAuth flow

        Updates self._lst and self._lst_expiration

        Args:
            realm: OAuth realm (default: "limited_poa")

        Raises:
            IBKRAuthenticationError: If LST generation fails
        """
        from skim.trading.brokers.ibkr_oauth import generate_lst

        logger.info("Generating new Live Session Token...")

        try:
            self._lst, self._lst_expiration = generate_lst(
                self.consumer_key,
                self.access_token,
                self.access_token_secret,
                self.dh_prime_hex,
                self.signature_key_path,
                self.encryption_key_path,
                realm=realm,
            )
            expiration_dt = datetime.fromtimestamp(self._lst_expiration / 1000)
            logger.info(
                f"LST generated successfully, expires at {expiration_dt}"
            )

        except Exception as e:
            raise IBKRAuthenticationError(f"LST generation failed: {e}") from e

    def is_expiring(self, skew_seconds: int = 300) -> bool:
        """Check if current LST is close to expiring

        Args:
            skew_seconds: Seconds before expiration to consider as "expiring"

        Returns:
            True if close to expiration (within skew_seconds)
        """
        if self._lst_expiration is None:
            return False
        now_ms = int(datetime.now().timestamp() * 1000)
        return self._lst_expiration <= now_ms + (skew_seconds * 1000)
