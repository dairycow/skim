from unittest.mock import AsyncMock, MagicMock

import pytest

from skim.trading.brokers.ibkr_orders import IBKROrders, IBKROrdersError


@pytest.fixture
def mock_ibkr_client():
    """Fixture for a mocked IBKRClient."""
    client = MagicMock()
    client.get_account.return_value = "DU12345"
    return client


@pytest.fixture
def mock_market_data_provider():
    """Fixture for a mocked MarketDataProvider."""
    provider = MagicMock()
    provider.get_contract_id = AsyncMock(return_value="12345")
    return provider


@pytest.fixture
def orders_service(mock_ibkr_client, mock_market_data_provider):
    """Fixture for the IBKROrders service."""
    return IBKROrders(
        client=mock_ibkr_client, market_data=mock_market_data_provider
    )


# Tests for place_order parameter validation
@pytest.mark.asyncio
async def test_place_order_invalid_order_type(orders_service: IBKROrders):
    """Should raise IBKROrdersError for an unsupported order_type."""
    with pytest.raises(IBKROrdersError, match="Invalid order type: FAKETYPE"):
        await orders_service.place_order(
            ticker="TEST", action="BUY", quantity=10, order_type="FAKETYPE"
        )


@pytest.mark.asyncio
async def test_place_order_stp_missing_stop_price(orders_service: IBKROrders):
    """Should raise IBKROrdersError if order_type is STP and stop_price is None."""
    with pytest.raises(
        IBKROrdersError, match="stop_price required for STP orders"
    ):
        await orders_service.place_order(
            ticker="TEST",
            action="BUY",
            quantity=10,
            order_type="STP",
            stop_price=None,
        )


@pytest.mark.asyncio
async def test_place_order_stp_lmt_missing_prices(orders_service: IBKROrders):
    """Should raise IBKROrdersError for STP LMT orders with missing prices."""
    with pytest.raises(
        IBKROrdersError, match="stop_price required for STP LMT orders"
    ):
        await orders_service.place_order(
            ticker="TEST",
            action="BUY",
            quantity=10,
            order_type="STP LMT",
            stop_price=None,
            limit_price=100.0,
        )

    with pytest.raises(
        IBKROrdersError, match="limit_price required for STP LMT orders"
    ):
        await orders_service.place_order(
            ticker="TEST",
            action="BUY",
            quantity=10,
            order_type="STP LMT",
            stop_price=99.0,
            limit_price=None,
        )


# TODO: Add more unit tests for IBKROrders
# - Test successful order placement for MKT, STP, STP LMT
# - Test order confirmation flow (_confirm_order)
# - Test _parse_order_response with various payloads
# - Test get_open_orders parsing
# - Test get_positions parsing
# - Test get_account_balance parsing
# - Test cancel_order success and failure
