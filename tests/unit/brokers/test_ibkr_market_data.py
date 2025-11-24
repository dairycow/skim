from unittest.mock import AsyncMock, MagicMock

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


@pytest.mark.asyncio
async def test_get_market_data_retries_after_preflight_warmup(mocker):
    """First snapshot can be empty; service should warm up and retry."""
    mock_client = AsyncMock()
    market_data_service = IBKRMarketData(client=mock_client)

    contract_response = [
        {
            "conid": "123",
            "description": "ASX STOCK",
            "sections": [{"secType": "STK"}],
        }
    ]
    preflight_response = [{"conid": "123"}]
    empty_snapshot = [{"31": "0"}]  # invalid last price triggers retry
    valid_snapshot = [
        {
            "conid": "123",
            "31": "1.0",
            "70": "1.2",
            "71": "0.9",
            "84": "0.95",
            "86": "1.05",
            "87": "1000",
            "88": "200",
            "85": "150",
            "7295": "1.0",
            "7741": "0.8",
            "83": "0.1",
        }
    ]

    mock_client._request = AsyncMock(
        side_effect=[
            contract_response,  # contract lookup
            preflight_response,  # initial preflight
            empty_snapshot,  # first snapshot -> invalid
            preflight_response,  # warmup preflight
            valid_snapshot,  # retry snapshot -> valid
        ]
    )

    mocker.patch("asyncio.sleep", AsyncMock())  # skip real wait

    result = await market_data_service.get_market_data("ABC")

    assert result is not None
    assert result.ticker == "ABC"
    assert result.last_price == 1.0
    assert result.high == 1.2
    assert result.low == 0.9
    assert mock_client._request.await_count == 5
    assert "123" in market_data_service._market_data_streams


# TODO: Add more unit tests for IBKRMarketData
# - Test _parse_market_data_fields
# - Test get_market_data for single ticker (mocking _get_contract_id, etc.)
# - Test get_market_data for batch tickers (mocking and verifying asyncio.gather)
# - Test _get_contract_id caching logic
# - Test _establish_market_data_stream
# - Test _fetch_market_snapshot
