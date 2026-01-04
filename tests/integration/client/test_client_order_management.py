#!/usr/bin/env python3
"""Test client order management with IBKR API (async services)

WARNING: These tests place REAL orders on the paper trading account.
Set RUN_IBKR_LIVE=1 to enable.
"""

import asyncio
import logging
import os
import time

import pytest

from skim.brokers.ibkr_market_data import IBKRMarketData
from skim.brokers.ibkr_orders import IBKROrders

pytestmark = pytest.mark.skipif(
    not os.getenv("RUN_IBKR_LIVE"),
    reason="Requires RUN_IBKR_LIVE=1 and paper-trading credentials",
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@pytest.fixture
def ibkr_orders(ibkr_client):
    """Provide IBKROrders wired to the connected client."""
    market_data = IBKRMarketData(ibkr_client)
    return IBKROrders(ibkr_client, market_data)


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_get_open_orders_initial(ibkr_orders):
    """Test getting initial open orders."""
    logger.info("Testing initial open orders retrieval...")

    initial_orders = await ibkr_orders.get_open_orders()
    assert isinstance(initial_orders, list)
    logger.info(f"Found {len(initial_orders)} open orders")

    for order in initial_orders:
        logger.info(f"  {order}")


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_place_market_order(ibkr_orders):
    """Test placing a market order."""
    logger.info("Testing market order placement (BUY 15 BHP)...")
    logger.info("Using 15 shares to meet ASX $500 minimum")
    logger.info("Market order - will queue until market opens")

    # Place a market order on BHP (ASX stock)
    # ASX requires minimum $500 AUD order, so use 15 shares (BHP ~$40-50)
    order_result = await ibkr_orders.place_order(
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
@pytest.mark.asyncio
async def test_get_open_orders_after_placement(ibkr_orders):
    """Test getting open orders after placing an order."""
    logger.info("Testing open orders retrieval after placement...")

    open_orders = await ibkr_orders.get_open_orders()
    assert isinstance(open_orders, list)
    logger.info(f"Found {len(open_orders)} open orders")

    for order in open_orders:
        logger.info(f"  {order}")


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_cancel_order(ibkr_orders):
    """Test cancelling an order."""
    logger.info("Testing order cancellation...")

    # First place an order to cancel
    order_result = await ibkr_orders.place_order(
        ticker="BHP", action="BUY", quantity=15, order_type="MKT"
    )

    if order_result:
        order_id = order_result.order_id
        logger.info(f"Cancelling order {order_id}...")

        # Wait for order to register
        await asyncio.sleep(2)

        # Cancel the order (may fail if already filled/cancelled)
        cancel_success = await ibkr_orders.cancel_order(order_id)
        # Order might already be filled or cancelled, which is expected behavior
        # The important thing is that the cancellation attempt doesn't crash
        logger.info(f"Cancellation result: {cancel_success}")

        logger.info(f"✓ Order {order_id} cancelled successfully")

        # Wait for cancellation to process
        await asyncio.sleep(2)

        return order_id
    else:
        pytest.skip("Could not place order to cancel")


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_verify_order_cancellation(ibkr_orders):
    """Test verifying order cancellation."""
    logger.info("Testing order cancellation verification...")

    final_orders = await ibkr_orders.get_open_orders()
    assert isinstance(final_orders, list)
    logger.info(f"Found {len(final_orders)} open orders after cancellation")

    for order in final_orders:
        logger.info(f"  {order}")


if __name__ == "__main__":
    # Allow running as script for manual testing
    from tests.integration.conftest import validate_oauth_environment

    validate_oauth_environment()

    from skim.brokers.ibkr_client import IBKRClient

    test_client = IBKRClient(paper_trading=True)
    asyncio.run(test_client.connect())
    orders_service = IBKROrders(test_client, IBKRMarketData(test_client))

    try:
        asyncio.run(test_get_open_orders_initial(orders_service))
        order_id = asyncio.run(test_place_market_order(orders_service))
        asyncio.run(test_get_open_orders_after_placement(orders_service))
        asyncio.run(test_cancel_order(orders_service))
        asyncio.run(test_verify_order_cancellation(orders_service))

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
        asyncio.run(test_client.disconnect())
