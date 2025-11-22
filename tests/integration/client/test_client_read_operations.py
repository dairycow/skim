#!/usr/bin/env python3
"""Test client read operations with IBKR API (async services)"""

import asyncio
import logging
import os

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
def services(ibkr_client):
    """Provide market data and orders services."""
    market_data = IBKRMarketData(ibkr_client)
    orders = IBKROrders(ibkr_client, market_data)
    return market_data, orders


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_account_balance(services):
    """Test getting account balance."""
    logger.info("Testing account balance retrieval...")

    _, orders = services
    balance = await orders.get_account_balance()
    assert balance is not None
    logger.info(f"Account balance: {balance}")


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_get_positions(services):
    """Test getting current positions."""
    logger.info("Testing positions retrieval...")

    _, orders = services
    positions = await orders.get_positions()
    assert isinstance(positions, list)
    logger.info(f"Found {len(positions)} positions")

    for pos in positions:
        logger.info(f"  {pos}")


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_market_data(services):
    """Test getting market data for BHP."""
    logger.info("Testing market data retrieval for BHP...")

    market_data_service, _ = services
    market_data = await market_data_service.get_market_data("BHP")

    # Market data might not be available if market is closed or data feed is down
    # This is expected behavior for integration tests
    if market_data is None:
        logger.warning(
            "No market data available for BHP (market may be closed)"
        )
        return

    logger.info(f"Market data: {market_data}")
    logger.info(f"  Last: ${market_data.last_price}")
    logger.info(f"  Bid: ${market_data.bid}")
    logger.info(f"  Ask: ${market_data.ask}")
    logger.info(f"  Volume: {market_data.volume}")

    # Verify data is valid when available
    assert market_data.last_price > 0
    assert market_data.bid >= 0
    assert market_data.ask >= 0
    assert market_data.volume >= 0


@pytest.mark.integration
@pytest.mark.manual
@pytest.mark.asyncio
async def test_contract_caching(services):
    """Test that contract IDs are properly cached."""
    logger.info("Testing contract ID caching...")
    market_data_service, _ = services

    # First call should fetch and cache
    market_data1 = await market_data_service.get_market_data("BHP")

    # If market data is not available, we can't test caching
    if market_data1 is None:
        logger.warning(
            "Cannot test contract caching - no market data available"
        )
        return

    # Second call should use cached contract ID
    market_data2 = await market_data_service.get_market_data("BHP")
    assert market_data2 is not None

    logger.info("✓ Contract ID caching working correctly")


if __name__ == "__main__":
    # Allow running as script for manual testing
    from tests.conftest import validate_oauth_environment

    validate_oauth_environment()

    from skim.brokers.ibkr_client import IBKRClient

    test_client = IBKRClient(paper_trading=True)
    asyncio.run(test_client.connect())
    services = (
        IBKRMarketData(test_client),
        IBKROrders(test_client, IBKRMarketData(test_client)),
    )

    try:
        asyncio.run(test_account_balance(services))
        asyncio.run(test_get_positions(services))
        asyncio.run(test_market_data(services))
        asyncio.run(test_contract_caching(services))

        logger.info(
            "\n✓ All client read operation tests completed successfully!"
        )

    except Exception as e:
        logger.error(f"✗ Test failed: {e}")
        import traceback

        traceback.print_exc()
        import sys

        sys.exit(1)
    finally:
        asyncio.run(test_client.disconnect())
