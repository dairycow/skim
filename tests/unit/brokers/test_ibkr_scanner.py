from unittest.mock import MagicMock

import pytest

from skim.brokers.ibkr_gap_scanner import IBKRGapScanner
from skim.core.config import ScannerConfig
from skim.validation.scanners import GapStock


@pytest.fixture
def mock_ibkr_client():
    """Fixture for a mocked IBKRClient."""
    client = MagicMock()
    client.is_connected.return_value = True
    return client


@pytest.fixture
def scanner_service(mock_ibkr_client):
    """Fixture for the IBKRGapScanner service."""
    return IBKRGapScanner(
        client=mock_ibkr_client, scanner_config=ScannerConfig()
    )


# Tests for _parse_scanner_response
def test_parse_scanner_response_success(scanner_service: IBKRGapScanner):
    response = {
        "contracts": [
            {
                "con_id": 123,
                "symbol": "TEST",
                "company_name": "Test Company",
                "scan_data": "+5.50%",
            }
        ]
    }
    expected = [
        {
            "conid": 123,
            "symbol": "TEST",
            "companyHeader": "Test Company",
            "change_percent": 5.50,
        }
    ]
    assert scanner_service._parse_scanner_response(response) == expected


def test_parse_scanner_response_invalid_format(scanner_service: IBKRGapScanner):
    """Response must be a dict, not a list or string."""
    assert scanner_service._parse_scanner_response("not a dict") == []
    assert (
        scanner_service._parse_scanner_response(["list", "not", "dict"]) == []
    )


def test_parse_scanner_response_empty_contracts(
    scanner_service: IBKRGapScanner,
):
    """Handle empty contracts gracefully."""
    assert scanner_service._parse_scanner_response({"contracts": []}) == []
    assert scanner_service._parse_scanner_response({}) == []


# Tests for _validate_and_create_gap_stock
def test_validate_gap_stock_success(scanner_service: IBKRGapScanner):
    result = {"symbol": "BHP", "conid": 555, "change_percent": 5.0}
    gap_stock = scanner_service._validate_and_create_gap_stock(
        result, min_gap=4.0
    )
    assert isinstance(gap_stock, GapStock)
    assert gap_stock.ticker == "BHP"
    assert gap_stock.gap_percent == 5.0
    assert gap_stock.conid == 555


def test_validate_gap_stock_below_min_gap(scanner_service: IBKRGapScanner):
    result = {"symbol": "BHP", "conid": 555, "change_percent": 3.0}
    gap_stock = scanner_service._validate_and_create_gap_stock(
        result, min_gap=4.0
    )
    assert gap_stock is None


def test_validate_gap_stock_missing_data(scanner_service: IBKRGapScanner):
    result = {"symbol": "BHP"}  # Missing conid
    gap_stock = scanner_service._validate_and_create_gap_stock(
        result, min_gap=4.0
    )
    assert gap_stock is None


def test_validate_gap_stock_pydantic_error(scanner_service: IBKRGapScanner):
    # conid should be an int, pass a string to trigger ValueError on int() conversion
    result = {"symbol": "BHP", "conid": "not-an-int", "change_percent": 5.0}
    with pytest.raises(ValueError):
        scanner_service._validate_and_create_gap_stock(result, min_gap=4.0)


# TODO: Add more unit tests for IBKRGapScanner
# - Test run_scanner method (mocking _request)
# - Test scan_for_gaps method (mocking run_scanner)
# - Test get_scanner_params method
# - Test _create_gap_scan_params
# - Test _parse_scanner_response with malformed scan_data
# - Test _parse_scanner_response with missing fields in contracts
