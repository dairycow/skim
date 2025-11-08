#!/usr/bin/env python3
"""Test full OAuth flow with IBKR API

This test combines OAuth LST generation with client connection
to test complete authentication and connection workflow.
"""

import logging

import pytest

from skim.brokers.ibkr_client import IBKRClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.manual
def test_oauth_lst_generation(oauth_config):
    """Test OAuth LST generation as part of full flow."""
    logger.info("Testing OAuth LST generation in full flow...")

    # This test would normally call by OAuth LST generation logic
    # For now, we'll test that IBKRClient can handle OAuth internally
    # when connecting

    # The actual LST generation is handled internally by IBKRClient.connect()
    # So we just need to verify configuration is valid
    assert oauth_config["consumer_key"] is not None
    assert oauth_config["access_token"] is not None
    assert oauth_config["access_token_secret"] is not None
    assert oauth_config["dh_prime_hex"] is not None

    logger.info("✓ OAuth configuration validated")


@pytest.mark.integration
@pytest.mark.manual
def test_client_creation_with_oauth(oauth_config):
    """Test IBKR client creation with OAuth configuration."""
    logger.info("Testing IBKR client creation with OAuth...")

    client = IBKRClient(paper_trading=True)

    assert client is not None
    assert hasattr(client, "connect")
    assert hasattr(client, "disconnect")

    logger.info("✓ Client created with OAuth configuration")


@pytest.mark.integration
@pytest.mark.manual
def test_oauth_connection_workflow(oauth_config):
    """Test complete OAuth connection workflow."""
    logger.info("Testing complete OAuth connection workflow...")

    client = IBKRClient(paper_trading=True)

    # Test connection (this will internally handle OAuth LST generation)
    logger.info("Connecting to IBKR using OAuth...")
    client.connect(host="", port=0, client_id=0)

    assert client.is_connected(), "Failed to connect using OAuth"

    logger.info("✓ OAuth connection successful")

    # Test basic operations to verify authentication works
    account_id = client.get_account()
    assert account_id is not None, (
        "Failed to get account (authentication may have failed)"
    )

    logger.info(f"✓ Account retrieved: {account_id}")

    # Test a simple read operation
    try:
        balance = client.get_account_balance()
        logger.info(f"✓ Account balance retrieved: {balance is not None}")
    except Exception as e:
        logger.warning(f"Could not retrieve account balance: {e}")

    # Cleanup
    client.disconnect()
    assert not client.is_connected(), "Failed to disconnect"

    logger.info("✓ OAuth workflow completed successfully")


@pytest.mark.integration
@pytest.mark.manual
def test_oauth_session_persistence(oauth_config):
    """Test OAuth session persistence and reconnection."""
    logger.info("Testing OAuth session persistence...")

    client = IBKRClient(paper_trading=True)

    # First connection
    client.connect(host="", port=0, client_id=0)
    assert client.is_connected(), "Initial connection failed"

    account_id_1 = client.get_account()

    # Disconnect
    client.disconnect()
    assert not client.is_connected(), "Disconnection failed"

    # Reconnect (should generate new LST)
    client.connect(host="", port=0, client_id=0)
    assert client.is_connected(), "Reconnection failed"

    account_id_2 = client.get_account()

    # Should get same account
    assert account_id_1 == account_id_2, (
        "Account ID mismatch after reconnection"
    )

    logger.info("✓ OAuth session persistence working correctly")

    # Cleanup
    client.disconnect()


if __name__ == "__main__":
    # Allow running as script for manual testing
    import os

    from tests.conftest import validate_oauth_environment

    validate_oauth_environment()

    config = {
        "consumer_key": os.getenv("OAUTH_CONSUMER_KEY"),
        "access_token": os.getenv("OAUTH_ACCESS_TOKEN"),
        "access_token_secret": os.getenv("OAUTH_ACCESS_TOKEN_SECRET"),
        "dh_prime_hex": os.getenv("OAUTH_DH_PRIME"),
        "signature_key_path": os.getenv("OAUTH_SIGNATURE_PATH", ""),
        "encryption_key_path": os.getenv("OAUTH_ENCRYPTION_PATH", ""),
    }

    try:
        test_oauth_lst_generation(config)
        test_client_creation_with_oauth(config)
        test_oauth_connection_workflow(config)
        test_oauth_session_persistence(config)

        logger.info("\n✓ All OAuth full flow tests completed successfully!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
