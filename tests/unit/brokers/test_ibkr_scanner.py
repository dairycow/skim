"""Unit tests for IBKR scanner methods

Tests the scanner functionality without requiring real IBKR API access.
Follows TDD approach - tests are written first, then implementation.
"""

import pytest
import responses

from skim.core.config import ScannerConfig


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

    def test_get_market_data_extended_not_connected(
        self, ibkr_client_mock_oauth
    ):
        """Test extended market data retrieval when not connected"""
        ibkr_client_mock_oauth._connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            ibkr_client_mock_oauth.get_market_data_extended("6793599")

    @responses.activate
    def test_get_market_data_extended_empty_response(
        self, ibkr_client_mock_oauth
    ):
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
    def test_get_market_data_extended_type_conversion(
        self, ibkr_client_mock_oauth
    ):
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


class TestIBKRGapScannerConfig:
    """Tests for IBKRGapScanner configuration integration"""

    def test_ibkr_scanner_init_with_config(self):
        """Test scanner accepts ScannerConfig parameter"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner_config = ScannerConfig(
            volume_filter=25000,
            price_filter=0.10,
            or_duration_minutes=15,
            or_poll_interval_seconds=45,
            gap_fill_tolerance=1.5,
            or_breakout_buffer=0.2,
        )

        scanner = IBKRGapScanner(
            paper_trading=True, scanner_config=scanner_config
        )

        assert scanner.scanner_config.volume_filter == 25000
        assert scanner.scanner_config.price_filter == 0.10
        assert scanner.scanner_config.or_duration_minutes == 15
        assert scanner.scanner_config.or_poll_interval_seconds == 45
        assert scanner.scanner_config.gap_fill_tolerance == 1.5
        assert scanner.scanner_config.or_breakout_buffer == 0.2

    def test_create_gap_scan_params_uses_config(self):
        """Test scan parameters use config values instead of hardcoded"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner_config = ScannerConfig(
            volume_filter=15000,
            price_filter=0.08,
        )

        scanner = IBKRGapScanner(
            paper_trading=True, scanner_config=scanner_config
        )

        scan_params = scanner._create_gap_scan_params(min_gap=3.0)

        # Check that config values are used in scan parameters
        price_filter = next(
            (f for f in scan_params["filter"] if f["code"] == "price"), None
        )
        volume_filter = next(
            (f for f in scan_params["filter"] if f["code"] == "volume"), None
        )

        assert price_filter is not None
        assert price_filter["value"] == 0.08
        assert volume_filter is not None
        assert volume_filter["value"] == 15000

    def test_scan_for_gaps_with_custom_config(self):
        """Test scanning respects config price and volume filters"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner_config = ScannerConfig(
            volume_filter=5000,
            price_filter=0.03,
        )

        scanner = IBKRGapScanner(
            paper_trading=True, scanner_config=scanner_config
        )

        # Mock connection state
        scanner._connected = True

        # Test that scan parameters use config values
        scan_params = scanner._create_gap_scan_params(min_gap=2.0)

        price_filter = next(
            (f for f in scan_params["filter"] if f["code"] == "price"), None
        )
        volume_filter = next(
            (f for f in scan_params["filter"] if f["code"] == "volume"), None
        )

        assert price_filter is not None
        assert price_filter["value"] == 0.03
        assert volume_filter is not None
        assert volume_filter["value"] == 5000

    def test_track_opening_range_uses_config_timing(self):
        """Test OR tracking uses config duration and interval"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner_config = ScannerConfig(
            or_duration_minutes=20,
            or_poll_interval_seconds=60,
        )

        scanner = IBKRGapScanner(
            paper_trading=True, scanner_config=scanner_config
        )

        # Mock connection state
        scanner._connected = True
        scanner.client._connected = True

        # Test that config values are available for OR tracking
        assert scanner.scanner_config.or_duration_minutes == 20
        assert scanner.scanner_config.or_poll_interval_seconds == 60

    def test_filter_breakouts_uses_config_buffer(self):
        """Test breakout filtering uses config buffer values"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner_config = ScannerConfig(
            or_breakout_buffer=0.25,
        )

        scanner = IBKRGapScanner(
            paper_trading=True, scanner_config=scanner_config
        )

        # Test that config buffer value is available
        assert scanner.scanner_config.or_breakout_buffer == 0.25

    def test_ibkr_scanner_default_config_when_not_provided(self):
        """Test scanner uses default config when none provided"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner = IBKRGapScanner(paper_trading=True)

        # Should have default scanner_config with ASX-optimized values
        assert hasattr(scanner, "scanner_config") is True
        assert scanner.scanner_config.volume_filter == 10000
        assert scanner.scanner_config.price_filter == 0.05
        assert scanner.scanner_config.or_duration_minutes == 10
        assert scanner.scanner_config.or_poll_interval_seconds == 30
        assert scanner.scanner_config.gap_fill_tolerance == 1.0
        assert scanner.scanner_config.or_breakout_buffer == 0.1
