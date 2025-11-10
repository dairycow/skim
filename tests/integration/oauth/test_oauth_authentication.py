#!/usr/bin/env python3
"""Test OAuth authentication and connection with IBKR API"""

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
def test_client_creation():
    """Test IBKR client creation."""
    logger.info("Testing IBKR client creation...")

    client = IBKRClient(paper_trading=True)

    assert client is not None
    assert hasattr(client, "connect")
    assert hasattr(client, "disconnect")
    assert hasattr(client, "is_connected")

    logger.info("✓ Client created successfully")


@pytest.mark.integration
@pytest.mark.manual
def test_connection(ibkr_client):
    """Test connecting to IBKR."""
    logger.info("Testing connection to IBKR...")

    ibkr_client.connect()

    assert ibkr_client.is_connected(), "Failed to connect to IBKR"

    logger.info("✓ Successfully connected to IBKR")


@pytest.mark.integration
@pytest.mark.manual
def test_get_account(ibkr_client):
    """Test getting account information."""
    logger.info("Testing account information retrieval...")

    account_id = ibkr_client.get_account()

    assert account_id is not None, "Failed to get account ID"
    assert isinstance(account_id, str), "Account ID should be a string"

    logger.info(f"Account ID: {account_id}")

    # Verify it's a paper account
    if account_id.startswith("DU"):
        logger.info("✓ Successfully connected to paper trading account")
    else:
        logger.warning(f"⚠ Connected to non-paper account: {account_id}")


@pytest.mark.integration
@pytest.mark.manual
def test_session_keepalive(ibkr_client):
    """Test session keepalive (tickle)."""
    logger.info("Testing session keepalive...")

    # Verify tickle thread is started
    assert ibkr_client._tickle_thread is not None, (
        "Tickle thread should be created"
    )
    assert ibkr_client._tickle_thread.is_alive(), (
        "Tickle thread should be running"
    )

    # Verify session is still connected (tickle should maintain connection)
    assert ibkr_client.is_connected(), "Session should be connected"

    # Test that we can make a request after tickle thread has been running
    # This indirectly verifies the tickle is working
    account_id = ibkr_client.get_account()
    assert account_id is not None, "Should still be able to make API requests"

    logger.info("✓ Session keepalive working correctly")


@pytest.mark.integration
@pytest.mark.manual
def test_disconnection(ibkr_client):
    """Test disconnecting from IBKR."""
    logger.info("Testing disconnection from IBKR...")

    ibkr_client.disconnect()

    assert not ibkr_client.is_connected(), "Client should be disconnected"

    logger.info("✓ Successfully disconnected from IBKR")


if __name__ == "__main__":
    # Allow running as script for manual testing
    from tests.conftest import validate_oauth_environment

    validate_oauth_environment()

    test_client = IBKRClient(paper_trading=True)

    try:
        test_client_creation()
        test_connection(test_client)
        test_get_account(test_client)
        test_session_keepalive(test_client)
        test_disconnection(test_client)

        logger.info(
            "\n✓ All OAuth authentication tests completed successfully!"
        )

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
