"""Unit tests for IBKR scanner methods

Tests the scanner functionality without requiring real IBKR API access.
Follows TDD approach - tests are written first, then implementation.
"""

import pytest
import responses

from skim.brokers.ibkr_client import IBKRClient


@pytest.mark.unit
class TestIBKRScanner:
    """Tests for IBKR scanner methods"""

    @responses.activate
    def test_run_scanner_success(self, ibkr_client_mock_oauth):
        """Test successful scanner execution"""
        # Mock scanner run response
        scanner_response = [
            {
                "conid": "6793599",
                "companyHeader": "BHP Group Ltd - ASX",
                "symbol": "BHP",
                "31": 45.50,  # Last price
                "70": 2.5,  # Change % from close
                "86": 44.40,  # Previous close
                "88": 45.00,  # Today's open
                "7295": 1000000,  # Volume
            },
            {
                "conid": "8714",
                "companyHeader": "Commonwealth Bank of Australia - ASX",
                "symbol": "CBA",
                "31": 95.25,
                "70": -1.2,
                "86": 96.40,
                "88": 96.00,
                "7295": 750000,
            },
        ]

        responses.post(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/run",
            json=scanner_response,
            status=200,
        )

        scan_params = {
            "instrument": "STK",
            "scan_code": "TOP_PERC_GAIN",
            "filter": [
                {"name": "price", "value": "5", "type": "price"},
                {"name": "volume", "value": "100000", "type": "volume"},
            ],
            "location": "ASX",
        }

        result = ibkr_client_mock_oauth.run_scanner(scan_params)

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["conid"] == "6793599"
        assert result[0]["symbol"] == "BHP"
        assert result[0]["last_price"] == 45.50
        assert result[0]["change_percent"] == 2.5
        assert result[0]["previous_close"] == 44.40
        assert result[0]["today_open"] == 45.00
        assert result[0]["volume"] == 1000000

    @responses.activate
    def test_run_scanner_api_error(self, ibkr_client_mock_oauth):
        """Test scanner execution with API error"""
        responses.post(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/run",
            json={"error": "Invalid scan parameters"},
            status=400,
        )

        scan_params = {"instrument": "STK"}

        with pytest.raises(RuntimeError, match="Request failed: 400"):
            ibkr_client_mock_oauth.run_scanner(scan_params)

    def test_run_scanner_not_connected(self, ibkr_client_mock_oauth):
        """Test scanner execution when not connected"""
        ibkr_client_mock_oauth._connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            ibkr_client_mock_oauth.run_scanner({})

    @responses.activate
    def test_get_scanner_params_success(self, ibkr_client_mock_oauth):
        """Test successful retrieval of scanner parameters"""
        params_response = {
            "STK": {
                "filter": [
                    {"name": "price", "type": "price", "min": 0, "max": 10000},
                    {
                        "name": "volume",
                        "type": "volume",
                        "min": 0,
                        "max": 999999999,
                    },
                    {
                        "name": "market_cap",
                        "type": "market_cap",
                        "min": 0,
                        "max": 999999999,
                    },
                ],
                "location": ["ASX", "NASDAQ", "NYSE"],
            }
        }

        responses.get(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/params",
            json=params_response,
            status=200,
        )

        result = ibkr_client_mock_oauth.get_scanner_params()

        assert isinstance(result, dict)
        assert "STK" in result
        assert "filter" in result["STK"]
        assert "location" in result["STK"]
        assert len(result["STK"]["filter"]) == 3

    @responses.activate
    def test_get_scanner_params_api_error(self, ibkr_client_mock_oauth):
        """Test scanner parameters retrieval with API error"""
        responses.get(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/params",
            json={"error": "Service unavailable"},
            status=500,
        )

        with pytest.raises(RuntimeError):
            ibkr_client_mock_oauth.get_scanner_params()

    def test_get_scanner_params_not_connected(self, ibkr_client_mock_oauth):
        """Test scanner parameters retrieval when not connected"""
        ibkr_client_mock_oauth._connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            ibkr_client_mock_oauth.get_scanner_params()

    @responses.activate
    def test_get_market_data_extended_success(self, ibkr_client_mock_oauth):
        """Test successful extended market data retrieval"""
        market_data_response = {
            "6793599": {
                "31": 45.50,  # Last price
                "70": 2.5,  # Change % from close
                "86": 44.40,  # Previous close price
                "88": 45.00,  # Today's open price
                "7295": 1000000,  # Volume
            }
        }

        responses.get(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=market_data_response,
            status=200,
        )

        result = ibkr_client_mock_oauth.get_market_data_extended("6793599")

        assert isinstance(result, dict)
        assert result["last_price"] == 45.50
        assert result["change_percent"] == 2.5
        assert result["previous_close"] == 44.40
        assert result["today_open"] == 45.00
        assert result["volume"] == 1000000

    @responses.activate
    def test_get_market_data_extended_not_found(self, ibkr_client_mock_oauth):
        """Test extended market data retrieval for non-existent contract"""
        responses.get(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json={"error": "Contract not found"},
            status=404,
        )

        with pytest.raises(RuntimeError, match="Request failed: 404"):
            ibkr_client_mock_oauth.get_market_data_extended("9999999")

    def test_get_market_data_extended_not_connected(self, ibkr_client_mock_oauth):
        """Test extended market data retrieval when not connected"""
        ibkr_client_mock_oauth._connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            ibkr_client_mock_oauth.get_market_data_extended("6793599")

    @responses.activate
    def test_get_market_data_extended_empty_response(self, ibkr_client_mock_oauth):
        """Test extended market data retrieval with empty response"""
        responses.get(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json={},
            status=200,
        )

        result = ibkr_client_mock_oauth.get_market_data_extended("6793599")

        # Should return empty dict when no data found
        assert result == {}

    @responses.activate
    def test_run_scanner_empty_response(self, ibkr_client_mock_oauth):
        """Test scanner execution with empty response"""
        responses.post(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/run",
            json=[],
            status=200,
        )

        result = ibkr_client_mock_oauth.run_scanner({"instrument": "STK"})

        assert isinstance(result, list)
        assert len(result) == 0

    def test_run_scanner_empty_params(self, ibkr_client_mock_oauth):
        """Test scanner execution with empty parameters"""
        with pytest.raises(ValueError, match="Scan parameters cannot be empty"):
            ibkr_client_mock_oauth.run_scanner({})

    @responses.activate
    def test_run_scanner_missing_required_params(self, ibkr_client_mock_oauth):
        """Test scanner execution with missing required parameters"""
        # Mock 400 response for missing parameters
        responses.post(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/run",
            json={
                "error": "Bad Request: instrument and type params expected.",
                "statusCode": 400,
            },
            status=400,
        )

        # Missing instrument and type parameters
        scan_params = {
            "filter": [
                {"name": "price", "value": "5", "type": "price"},
            ],
            "location": "ASX",
        }

        with pytest.raises(RuntimeError, match="Request failed: 400"):
            ibkr_client_mock_oauth.run_scanner(scan_params)

    def test_get_market_data_extended_empty_conid(self, ibkr_client_mock_oauth):
        """Test extended market data with empty contract ID"""
        with pytest.raises(ValueError, match="Contract ID .* cannot be empty"):
            ibkr_client_mock_oauth.get_market_data_extended("")

        with pytest.raises(ValueError, match="Contract ID .* cannot be empty"):
            ibkr_client_mock_oauth.get_market_data_extended(None)

    @responses.activate
    def test_run_scanner_invalid_response_format(self, ibkr_client_mock_oauth):
        """Test scanner with invalid response format"""
        responses.post(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/run",
            json={"invalid": "format"},
            status=200,
        )

        result = ibkr_client_mock_oauth.run_scanner({"instrument": "STK"})

        assert isinstance(result, list)
        assert len(result) == 0

    @responses.activate
    def test_get_market_data_extended_type_conversion(self, ibkr_client_mock_oauth):
        """Test extended market data with type conversion"""
        market_data_response = {
            "6793599": {
                "31": "45.50",  # String that should convert to float
                "70": "2.5",  # String that should convert to float
                "86": "44.40",  # String that should convert to float
                "88": "45.00",  # String that should convert to float
                "7295": "1000000",  # String that should convert to int
            }
        }

        responses.get(
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=market_data_response,
            status=200,
        )

        result = ibkr_client_mock_oauth.get_market_data_extended("6793599")

        assert isinstance(result["last_price"], float)
        assert isinstance(result["change_percent"], float)
        assert isinstance(result["previous_close"], float)
        assert isinstance(result["today_open"], float)
        assert isinstance(result["volume"], int)
        assert result["last_price"] == 45.50
        assert result["volume"] == 1000000
