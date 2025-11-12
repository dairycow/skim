"""Integration tests for penny stock scanning.

Tests end-to-end penny stock scanning functionality with real IBKR API responses.
"""

import pytest
import responses

from skim.scanners.ibkr_gap_scanner import IBKRGapScanner


@pytest.mark.integration
class TestPennyStockScanning:
    """Integration tests for penny stock scanning"""

    @responses.activate
    def test_end_to_end_penny_stock_scanning(self, ibkr_client_mock_oauth):
        """Test complete penny stock scanning workflow"""
        # Mock contract ID lookup for penny stocks
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "123456",
                    "symbol": "CR9",
                    "description": "CROWN RESORTS",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock market data snapshot with penny stock prices
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "0.005",  # last price - 0.5 cents
                    "84": "0.004",  # bid - 0.4 cents
                    "86": "0.006",  # ask - 0.6 cents
                    "87": "1000000",  # volume
                    "7": "0.003",  # daily low - 0.3 cents
                }
            ],
        )

        # Test market data retrieval
        result = ibkr_client_mock_oauth.get_market_data("CR9")

        assert result is not None
        assert result.ticker == "CR9"
        assert result.last_price == 0.005
        assert result.bid == 0.004
        assert result.ask == 0.006
        assert result.volume == 1000000
        assert result.low == 0.003

    @responses.activate
    def test_gap_scanner_with_penny_stocks(self, ibkr_client_mock_oauth):
        """Test gap scanner processing penny stocks"""
        # Mock scanner results with penny stocks
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/scanner/run",
            json=[
                {
                    "conid": "123456",
                    "symbol": "CR9",
                    "companyName": "CROWN RESORTS",
                    "category": "STOCK.HK",
                    "change_percent": 25.0,
                }
            ],
        )

        # Mock contract lookup for scanner
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "123456",
                    "symbol": "CR9",
                    "description": "CROWN RESORTS",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock market data for penny stock
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "0.005",  # last price
                    "84": "0.004",  # bid
                    "86": "0.006",  # ask
                    "87": "1000000",  # volume
                    "7": "0.003",  # low
                }
            ],
        )

        # Test gap scanner
        scanner = IBKRGapScanner(paper_trading=True)
        scanner.connect()

        gap_stocks = scanner.scan_for_gaps(min_gap=20.0)

        assert len(gap_stocks) > 0
        penny_stock = next((s for s in gap_stocks if s.ticker == "CR9"), None)
        assert penny_stock is not None
        assert penny_stock.gap_percent == 25.0
        assert penny_stock.close_price == 0.005

    @responses.activate
    def test_multiple_penny_stock_formats(self, ibkr_client_mock_oauth):
        """Test various penny stock price formats"""
        # Test different penny stocks with different price formats
        test_cases = [
            {
                "symbol": "CR9",
                "price_data": {
                    "31": "0.005",  # Standard decimal
                    "84": "0.004",
                    "86": "0.006",
                    "87": "1000000",
                    "7": "0.003",
                },
            },
            {
                "symbol": "1TT",
                "price_data": {
                    "31": "5e-3",  # Scientific notation
                    "84": "4e-3",
                    "86": "6e-3",
                    "87": "500000",
                    "7": "3e-3",
                },
            },
            {
                "symbol": "BLU",
                "price_data": {
                    "31": "C0.008",  # With IBKR prefix
                    "84": "H0.007",
                    "86": "0.009",
                    "87": "750000",
                    "7": "L0.006",
                },
            },
        ]

        for i, test_case in enumerate(test_cases):
            # Mock contract lookup
            responses.add(
                responses.GET,
                f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
                json=[
                    {
                        "conid": f"12345{i}",
                        "symbol": test_case["symbol"],
                        "description": f"Test Stock {i}",
                        "sections": [{"secType": "STK"}],
                    }
                ],
            )

            # Mock market data
            responses.add(
                responses.GET,
                f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
                json=[test_case["price_data"]],
            )

            # Test market data retrieval
            result = ibkr_client_mock_oauth.get_market_data(test_case["symbol"])

            assert result is not None, (
                f"Failed to get market data for {test_case['symbol']}"
            )
            assert result.ticker == test_case["symbol"]

            # Verify price parsing worked correctly
            expected_last_price = float(
                test_case["price_data"]["31"].lstrip("CHL")
            )
            assert result.last_price == expected_last_price, (
                f"Price parsing failed for {test_case['symbol']}"
            )

    def test_penny_stock_validation_thresholds(self):
        """Test that penny stocks meet minimum price validation"""
        from skim.validation.price_parsing import validate_minimum_price

        # Test various penny stock prices
        penny_prices = [0.001, 0.005, 0.009, 0.0001]

        for price in penny_prices:
            assert validate_minimum_price(price), (
                f"Price {price} should be valid"
            )

        # Test invalid prices
        invalid_prices = [0, -0.001, 0.00005]  # Below minimum threshold

        for price in invalid_prices:
            assert not validate_minimum_price(price), (
                f"Price {price} should be invalid"
            )
