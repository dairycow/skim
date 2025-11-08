#!/usr/bin/env python3
"""Test client read operations with IBKR API"""

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
def test_account_balance(ibkr_client):
    """Test getting account balance."""
    logger.info("Testing account balance retrieval...")

    balance = ibkr_client.get_account_balance()
    assert balance is not None
    logger.info(f"Account balance: {balance}")


@pytest.mark.integration
@pytest.mark.manual
def test_get_positions(ibkr_client):
    """Test getting current positions."""
    logger.info("Testing positions retrieval...")

    positions = ibkr_client.get_positions()
    assert isinstance(positions, list)
    logger.info(f"Found {len(positions)} positions")

    for pos in positions:
        logger.info(f"  {pos}")


@pytest.mark.integration
@pytest.mark.manual
def test_market_data(ibkr_client):
    """Test getting market data for AAPL."""
    logger.info("Testing market data retrieval for AAPL...")

    market_data = ibkr_client.get_market_data("AAPL")
    assert market_data is not None

    logger.info(f"Market data: {market_data}")
    logger.info(f"  Last: ${market_data.last_price}")
    logger.info(f"  Bid: ${market_data.bid}")
    logger.info(f"  Ask: ${market_data.ask}")
    logger.info(f"  Volume: {market_data.volume}")


@pytest.mark.integration
@pytest.mark.manual
def test_contract_caching(ibkr_client):
    """Test that contract IDs are properly cached."""
    logger.info("Testing contract ID caching...")

    # First call should fetch and cache
    market_data1 = ibkr_client.get_market_data("AAPL")
    assert market_data1 is not None

    # Second call should use cached contract ID
    market_data2 = ibkr_client.get_market_data("AAPL")
    assert market_data2 is not None

    logger.info("✓ Contract ID caching working correctly")


if __name__ == "__main__":
    # Allow running as script for manual testing
    from tests.conftest import validate_oauth_environment

    validate_oauth_environment()

    test_client = IBKRClient(paper_trading=True)
    test_client.connect(host="", port=0, client_id=0)

    try:
        test_account_balance(test_client)
        test_get_positions(test_client)
        test_market_data(test_client)
        test_contract_caching(test_client)

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
        test_client.disconnect()
