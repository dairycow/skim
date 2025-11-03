"""Unit tests for OAuth 1.0a configuration validation

These tests verify that OAuth credentials are properly configured
for connecting to IBKR API via IBind.
"""

import os
import re
from pathlib import Path

import pytest


class TestOAuthConfiguration:
    """Test OAuth 1.0a configuration"""

    def test_oauth_enabled(self):
        """Test that IBIND_USE_OAUTH is set to True"""
        use_oauth = os.getenv("IBIND_USE_OAUTH", "").lower()
        assert use_oauth == "true", "IBIND_USE_OAUTH must be set to 'True'"

    def test_consumer_key_present(self):
        """Test that consumer key is set"""
        consumer_key = os.getenv("IBIND_OAUTH1A_CONSUMER_KEY")
        assert consumer_key, "IBIND_OAUTH1A_CONSUMER_KEY is required"
        assert len(consumer_key) > 0, "Consumer key must not be empty"

    def test_consumer_key_format(self):
        """Test consumer key format (should be alphanumeric, typically 9 chars)"""
        consumer_key = os.getenv("IBIND_OAUTH1A_CONSUMER_KEY")
        if consumer_key:
            # Consumer keys are typically uppercase alphanumeric
            assert consumer_key.isupper(), (
                "Consumer key should be uppercase (IBind auto-converts)"
            )
            assert consumer_key.isalnum(), "Consumer key should be alphanumeric"

    def test_access_token_present(self):
        """Test that access token is set"""
        access_token = os.getenv("IBIND_OAUTH1A_ACCESS_TOKEN")
        assert access_token, "IBIND_OAUTH1A_ACCESS_TOKEN is required"
        assert len(access_token) > 0, "Access token must not be empty"

    def test_access_token_secret_present(self):
        """Test that access token secret is set"""
        secret = os.getenv("IBIND_OAUTH1A_ACCESS_TOKEN_SECRET")
        assert secret, "IBIND_OAUTH1A_ACCESS_TOKEN_SECRET is required"
        assert len(secret) > 0, "Access token secret must not be empty"

    def test_signature_key_path_set(self):
        """Test that signature key file path is set"""
        sig_path = os.getenv("IBIND_OAUTH1A_SIGNATURE_KEY_FP")
        assert sig_path, "IBIND_OAUTH1A_SIGNATURE_KEY_FP is required"

    def test_signature_key_file_exists(self):
        """Test that signature key file exists"""
        sig_path = os.getenv("IBIND_OAUTH1A_SIGNATURE_KEY_FP")
        if sig_path:
            assert Path(sig_path).exists(), (
                f"Signature key file not found: {sig_path}"
            )

    def test_signature_key_is_private_key(self):
        """Test that signature key file contains a private key"""
        sig_path = os.getenv("IBIND_OAUTH1A_SIGNATURE_KEY_FP")
        if sig_path and Path(sig_path).exists():
            content = Path(sig_path).read_text()
            assert "-----BEGIN RSA PRIVATE KEY-----" in content or (
                "-----BEGIN PRIVATE KEY-----" in content
            ), "Signature key must be a private RSA key"
            assert "-----END" in content, "Signature key file appears incomplete"

    def test_encryption_key_path_set(self):
        """Test that encryption key file path is set"""
        enc_path = os.getenv("IBIND_OAUTH1A_ENCRYPTION_KEY_FP")
        assert enc_path, "IBIND_OAUTH1A_ENCRYPTION_KEY_FP is required"

    def test_encryption_key_file_exists(self):
        """Test that encryption key file exists"""
        enc_path = os.getenv("IBIND_OAUTH1A_ENCRYPTION_KEY_FP")
        if enc_path:
            assert Path(enc_path).exists(), (
                f"Encryption key file not found: {enc_path}"
            )

    def test_encryption_key_is_private_key(self):
        """Test that encryption key file contains a private key"""
        enc_path = os.getenv("IBIND_OAUTH1A_ENCRYPTION_KEY_FP")
        if enc_path and Path(enc_path).exists():
            content = Path(enc_path).read_text()
            assert "-----BEGIN RSA PRIVATE KEY-----" in content or (
                "-----BEGIN PRIVATE KEY-----" in content
            ), "Encryption key must be a private RSA key"
            assert "-----END" in content, "Encryption key file appears incomplete"

    def test_dh_prime_present(self):
        """Test that DH prime is set"""
        dh_prime = os.getenv("IBIND_OAUTH1A_DH_PRIME")
        assert dh_prime, "IBIND_OAUTH1A_DH_PRIME is required"
        assert len(dh_prime) > 0, "DH prime must not be empty"

    def test_dh_prime_format(self):
        """Test that DH prime is valid hex string without spaces/colons"""
        dh_prime = os.getenv("IBIND_OAUTH1A_DH_PRIME")
        if dh_prime:
            # Should be hex characters only (no spaces, no colons)
            assert re.match(r"^[0-9a-fA-F]+$", dh_prime), (
                "DH prime must be hex string without spaces or colons"
            )
            # DH primes are typically very long (2048-bit = 512 hex chars)
            assert len(dh_prime) >= 256, (
                f"DH prime seems too short ({len(dh_prime)} chars), "
                "expected 512+ for 2048-bit"
            )

    def test_all_required_oauth_vars_present(self):
        """Test that all required OAuth environment variables are set"""
        required_vars = [
            "IBIND_USE_OAUTH",
            "IBIND_OAUTH1A_CONSUMER_KEY",
            "IBIND_OAUTH1A_ACCESS_TOKEN",
            "IBIND_OAUTH1A_ACCESS_TOKEN_SECRET",
            "IBIND_OAUTH1A_SIGNATURE_KEY_FP",
            "IBIND_OAUTH1A_ENCRYPTION_KEY_FP",
            "IBIND_OAUTH1A_DH_PRIME",
        ]

        missing = []
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)

        assert not missing, f"Missing required OAuth variables: {missing}"

    def test_pem_files_are_readable(self):
        """Test that .pem key files are readable"""
        sig_path = os.getenv("IBIND_OAUTH1A_SIGNATURE_KEY_FP")
        enc_path = os.getenv("IBIND_OAUTH1A_ENCRYPTION_KEY_FP")

        if sig_path and Path(sig_path).exists():
            assert os.access(sig_path, os.R_OK), (
                f"Signature key file is not readable: {sig_path}"
            )

        if enc_path and Path(enc_path).exists():
            assert os.access(enc_path, os.R_OK), (
                f"Encryption key file is not readable: {enc_path}"
            )

    def test_pem_files_have_minimum_size(self):
        """Test that .pem files are not empty or corrupted"""
        sig_path = os.getenv("IBIND_OAUTH1A_SIGNATURE_KEY_FP")
        enc_path = os.getenv("IBIND_OAUTH1A_ENCRYPTION_KEY_FP")

        # 2048-bit RSA private keys are typically 1600-1800 bytes
        MIN_PEM_SIZE = 1000

        if sig_path and Path(sig_path).exists():
            size = Path(sig_path).stat().st_size
            assert size >= MIN_PEM_SIZE, (
                f"Signature key file seems too small ({size} bytes), "
                f"expected at least {MIN_PEM_SIZE} bytes"
            )

        if enc_path and Path(enc_path).exists():
            size = Path(enc_path).stat().st_size
            assert size >= MIN_PEM_SIZE, (
                f"Encryption key file seems too small ({size} bytes), "
                f"expected at least {MIN_PEM_SIZE} bytes"
            )


@pytest.mark.skipif(
    os.getenv("IBIND_USE_OAUTH", "").lower() != "true",
    reason="OAuth not enabled (IBIND_USE_OAUTH != True)",
)
class TestOAuthPaperTradingSetup:
    """Test OAuth is configured for paper trading account"""

    def test_consumer_key_for_paper_account(self):
        """Test that consumer key is likely for paper account

        Note: This is a warning test - there's no definitive way to tell
        if a consumer key is for paper vs live without connecting.
        """
        consumer_key = os.getenv("IBIND_OAUTH1A_CONSUMER_KEY")

        # This is just a sanity check - we can't definitively determine
        # if a consumer key is for paper vs live without trying to connect
        # The user should verify this manually

        assert consumer_key, "Consumer key required"

        # Log a warning that user should verify this
        print(
            f"\nWARNING: Please verify consumer key '{consumer_key}' "
            "is for your PAPER trading account (DU prefix)"
        )


class TestOAuthConfigurationIntegration:
    """Integration tests for OAuth configuration with IBind client"""

    def test_ibind_client_initializes_with_oauth(self):
        """Test that IBind client can initialize with OAuth configuration"""
        # This test requires ibind to be installed
        pytest.importorskip("ibind")

        from skim.brokers.ibind_client import IBIndClient

        # Should not raise any exceptions during initialization
        client = IBIndClient(paper_trading=True)

        # Verify OAuth mode was detected
        assert hasattr(client, "client"), "Client should have IBind client instance"
