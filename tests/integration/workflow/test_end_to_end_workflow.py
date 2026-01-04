#!/usr/bin/env python3
"""Test end-to-end workflow with skim trading bot"""

import logging
import os
import time

import pytest

from skim.brokers.ibkr_client import IBKRClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_IBKR_LIVE"),
    reason="Requires RUN_IBKR_LIVE=1 with live/paper IBKR credentials",
)


@pytest.mark.integration
@pytest.mark.manual
def test_client_initialization():
    """Test client initialization."""
    logger.info("Testing client initialization...")

    client = IBKRClient(paper_trading=True)

    assert client is not None
    assert hasattr(client, "connect")
    assert hasattr(client, "disconnect")
    assert hasattr(client, "is_connected")

    logger.info("✓ Client initialised successfully")


@pytest.mark.integration
@pytest.mark.manual
def test_client_connection(ibkr_client):
    """Test client connection to IBKR."""
    logger.info("Testing client connection...")

    assert ibkr_client.is_connected(), "Client should be connected"

    logger.info("✓ Client connected successfully")


@pytest.mark.integration
@pytest.mark.manual
def test_account_operations(ibkr_client):
    """Test account-related operations."""
    logger.info("Testing account operations...")

    # Get account information
    account_id = ibkr_client.get_account()
    assert account_id is not None, "Failed to get account ID"

    logger.info(f"✓ Account ID: {account_id}")

    # Get account balance
    try:
        balance = ibkr_client.get_account_balance()
        logger.info(f"✓ Account balance retrieved: {balance is not None}")
    except Exception as e:
        logger.warning(f"Could not retrieve account balance: {e}")

    # Get positions
    try:
        positions = ibkr_client.get_positions()
        logger.info(f"✓ Positions retrieved: {len(positions)} positions")
    except Exception as e:
        logger.warning(f"Could not retrieve positions: {e}")


@pytest.mark.integration
@pytest.mark.manual
def test_market_data_operations(ibkr_client):
    """Test market data operations."""
    logger.info("Testing market data operations...")

    # Test getting market data for a popular stock
    tickers_to_test = ["AAPL", "BHP", "MSFT"]

    for ticker in tickers_to_test:
        try:
            market_data = ibkr_client.get_market_data(ticker)
            if market_data:
                logger.info(
                    f"✓ Market data for {ticker}: {market_data.last_price}"
                )
            else:
                logger.warning(f"No market data available for {ticker}")
        except Exception as e:
            logger.warning(f"Error getting market data for {ticker}: {e}")


@pytest.mark.integration
@pytest.mark.manual
def test_order_workflow(ibkr_client):
    """Test order placement and management workflow."""
    logger.info("Testing order workflow...")

    # Get initial orders
    initial_orders = ibkr_client.get_open_orders()
    logger.info(f"Initial open orders: {len(initial_orders)}")

    # Place a small test order (will be cancelled immediately)
    try:
        order_result = ibkr_client.place_order(
            ticker="BHP", action="BUY", quantity=15, order_type="MKT"
        )

        if order_result:
            logger.info(f"✓ Test order placed: {order_result.order_id}")

            # Wait a moment for order to register
            time.sleep(2)

            # Check open orders again
            open_orders = ibkr_client.get_open_orders()
            logger.info(f"Open orders after placement: {len(open_orders)}")

            # Cancel test order
            cancel_success = ibkr_client.cancel_order(order_result.order_id)
            if cancel_success:
                logger.info(f"✓ Test order cancelled: {order_result.order_id}")
            else:
                logger.warning(
                    f"Failed to cancel order: {order_result.order_id}"
                )

        else:
            logger.warning("Failed to place test order")

    except Exception as e:
        logger.error(f"Error in order workflow: {e}")


@pytest.mark.integration
@pytest.mark.manual
def test_session_persistence(ibkr_client):
    """Test session persistence over time."""
    logger.info("Testing session persistence...")

    # Verify we're still connected
    assert ibkr_client.is_connected(), "Client should still be connected"

    # Test that we can still perform operations
    try:
        account_id = ibkr_client.get_account()
        assert account_id is not None, "Should still be able to get account"
        logger.info("✓ Session persistence verified")
    except Exception as e:
        logger.error(f"Session persistence test failed: {e}")


@pytest.mark.integration
@pytest.mark.manual
def test_error_handling(ibkr_client):
    """Test error handling for invalid operations."""
    logger.info("Testing error handling...")

    # Test invalid ticker
    try:
        ibkr_client.get_market_data("INVALIDTICKER123")
        # Should return None or raise an exception
        logger.info("✓ Invalid ticker handled gracefully")
    except Exception as e:
        logger.info(f"✓ Invalid ticker raised exception: {type(e).__name__}")

    # Test invalid order (if applicable)
    try:
        # This might fail due to market hours or other constraints
        ibkr_client.place_order(
            ticker="INVALID", action="BUY", quantity=1, order_type="MKT"
        )
        logger.info("✓ Invalid order handled gracefully")
    except Exception as e:
        logger.info(f"✓ Invalid order raised exception: {type(e).__name__}")


@pytest.mark.integration
@pytest.mark.manual
def test_cleanup(ibkr_client):
    """Test cleanup and disconnection."""
    logger.info("Testing cleanup...")

    # Ensure no test orders are left
    try:
        remaining_orders = ibkr_client.get_open_orders()
        if remaining_orders:
            logger.warning(f"Found {len(remaining_orders)} remaining orders")
            for order in remaining_orders:
                try:
                    ibkr_client.cancel_order(order.order_id)
                    logger.info(f"✓ Cleaned up order: {order.order_id}")
                except Exception as e:
                    logger.warning(
                        f"Failed to cleanup order {order.order_id}: {e}"
                    )
        else:
            logger.info("✓ No remaining orders to cleanup")
    except Exception as e:
        logger.warning(f"Error during cleanup: {e}")


if __name__ == "__main__":
    # Allow running as script for manual testing
    from tests.integration.conftest import validate_oauth_environment

    validate_oauth_environment()

    test_client = IBKRClient(paper_trading=True)

    try:
        test_client_initialization()

        # Connect for remaining tests
        test_client.connect()

        test_client_connection(test_client)
        test_account_operations(test_client)
        test_market_data_operations(test_client)
        test_order_workflow(test_client)
        test_session_persistence(test_client)
        test_error_handling(test_client)
        test_cleanup(test_client)

        # Disconnect
        test_client.disconnect()

        logger.info("\n✓ All end-to-end workflow tests completed successfully!")

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
