from unittest.mock import MagicMock

import pytest

from skim.brokers.ibkr_market_data import IBKRMarketData


@pytest.fixture
def mock_ibkr_client():
    """Fixture for a mocked IBKRClient."""
    return MagicMock()


@pytest.fixture
def market_data_service(mock_ibkr_client):
    """Fixture for the IBKRMarketData service."""
    return IBKRMarketData(client=mock_ibkr_client)


# Tests for _parse_contract_response
def test_parse_contract_response_prefers_asx(
    market_data_service: IBKRMarketData,
):
    """Should return the conid of the contract with 'ASX' in the description."""
    response = [
        {
            "conid": 123,
            "description": "SOME OTHER EXCHANGE",
            "sections": [{"secType": "STK"}],
        },
        {
            "conid": 456,
            "description": "COMPANY NAME ASX",
            "sections": [{"secType": "STK"}],
        },
    ]
    assert (
        market_data_service._parse_contract_response(response, "TEST") == "456"
    )


def test_parse_contract_response_fallback_to_first_stk(
    market_data_service: IBKRMarketData,
):
    """Should return the first STK conid if no ASX contract is found."""
    response = [
        {"conid": 789, "description": "NYSE", "sections": [{"secType": "STK"}]},
        {
            "conid": 101,
            "description": "NASDAQ",
            "sections": [{"secType": "STK"}],
        },
    ]
    assert (
        market_data_service._parse_contract_response(response, "TEST") == "789"
    )


def test_parse_contract_response_ignores_non_stk(
    market_data_service: IBKRMarketData,
):
    """Should ignore contracts that are not of secType 'STK'."""
    response = [
        {
            "conid": 222,
            "description": "A FUTURES CONTRACT",
            "sections": [{"secType": "FUT"}],
        },
        {
            "conid": 333,
            "description": "AN ASX STOCK",
            "sections": [{"secType": "STK"}],
        },
    ]
    assert (
        market_data_service._parse_contract_response(response, "TEST") == "333"
    )


def test_parse_contract_response_returns_none_if_no_stk(
    market_data_service: IBKRMarketData,
):
    """Should return None if no STK contracts are found."""
    response = [
        {
            "conid": 444,
            "description": "AN OPTIONS CONTRACT",
            "sections": [{"secType": "OPT"}],
        }
    ]
    assert (
        market_data_service._parse_contract_response(response, "TEST") is None
    )


def test_parse_contract_response_returns_none_for_invalid_format(
    market_data_service: IBKRMarketData,
):
    """Should return None if the response is not a list or is empty."""
    assert market_data_service._parse_contract_response({}, "TEST") is None
    assert market_data_service._parse_contract_response([], "TEST") is None
    assert market_data_service._parse_contract_response(None, "TEST") is None


# TODO: Add more unit tests for IBKRMarketData
# - Test _parse_market_data_fields
# - Test get_market_data for single ticker (mocking _get_contract_id, etc.)
# - Test get_market_data for batch tickers (mocking and verifying asyncio.gather)
# - Test _get_contract_id caching logic
# - Test _establish_market_data_stream
# - Test _fetch_market_snapshot
