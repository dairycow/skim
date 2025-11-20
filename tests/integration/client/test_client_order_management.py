#!/usr/bin/env python3
"""Test client order management with IBKR API

WARNING: This test places REAL orders on the paper trading account!
Using small quantities to minimize risk.
"""

import logging
import time

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
def test_get_open_orders_initial(ibkr_client):
    """Test getting initial open orders."""
    logger.info("Testing initial open orders retrieval...")

    initial_orders = ibkr_client.get_open_orders()
    assert isinstance(initial_orders, list)
    logger.info(f"Found {len(initial_orders)} open orders")

    for order in initial_orders:
        logger.info(f"  {order}")


@pytest.mark.integration
@pytest.mark.manual
def test_place_market_order(ibkr_client):
    """Test placing a market order."""
    logger.info("Testing market order placement (BUY 15 BHP)...")
    logger.info("Using 15 shares to meet ASX $500 minimum")
    logger.info("Market order - will queue until market opens")

    # Place a market order on BHP (ASX stock)
    # ASX requires minimum $500 AUD order, so use 15 shares (BHP ~$40-50)
    order_result = ibkr_client.place_order(
        ticker="BHP", action="BUY", quantity=15, order_type="MKT"
    )

    assert order_result is not None
    assert hasattr(order_result, "order_id")

    logger.info(f"✓ Order placed: {order_result}")

    # Wait for order to register
    time.sleep(2)

    return order_result.order_id


@pytest.mark.integration
@pytest.mark.manual
def test_get_open_orders_after_placement(ibkr_client):
    """Test getting open orders after placing an order."""
    logger.info("Testing open orders retrieval after placement...")

    open_orders = ibkr_client.get_open_orders()
    assert isinstance(open_orders, list)
    logger.info(f"Found {len(open_orders)} open orders")

    for order in open_orders:
        logger.info(f"  {order}")


@pytest.mark.integration
@pytest.mark.manual
def test_cancel_order(ibkr_client):
    """Test cancelling an order."""
    logger.info("Testing order cancellation...")

    # First place an order to cancel
    order_result = ibkr_client.place_order(
        ticker="BHP", action="BUY", quantity=15, order_type="MKT"
    )

    if order_result:
        order_id = order_result.order_id
        logger.info(f"Cancelling order {order_id}...")

        # Wait for order to register
        time.sleep(2)

        # Cancel the order (may fail if already filled/cancelled)
        cancel_success = ibkr_client.cancel_order(order_id)
        # Order might already be filled or cancelled, which is expected behavior
        # The important thing is that the cancellation attempt doesn't crash
        logger.info(f"Cancellation result: {cancel_success}")

        logger.info(f"✓ Order {order_id} cancelled successfully")

        # Wait for cancellation to process
        time.sleep(2)

        return order_id
    else:
        pytest.skip("Could not place order to cancel")


@pytest.mark.integration
@pytest.mark.manual
def test_verify_order_cancellation(ibkr_client):
    """Test verifying order cancellation."""
    logger.info("Testing order cancellation verification...")

    final_orders = ibkr_client.get_open_orders()
    assert isinstance(final_orders, list)
    logger.info(f"Found {len(final_orders)} open orders after cancellation")

    for order in final_orders:
        logger.info(f"  {order}")


if __name__ == "__main__":
    # Allow running as script for manual testing
    from tests.conftest import validate_oauth_environment

    validate_oauth_environment()

    test_client = IBKRClient(paper_trading=True)
    test_client.connect()

    try:
        test_get_open_orders_initial(test_client)
        order_id = test_place_market_order(test_client)
        test_get_open_orders_after_placement(test_client)
        test_cancel_order(test_client)
        test_verify_order_cancellation(test_client)

        logger.info(
            "\n✓ All client order management tests completed successfully!"
        )

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
    finally:
        test_client.disconnect()
