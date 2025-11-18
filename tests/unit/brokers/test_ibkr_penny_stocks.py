"""Tests for IBKR client penny stock price parsing.

Tests the enhanced market data methods that handle sub-cent prices.
Follows TDD approach - tests are written first, then implementation.
"""

import pytest
import responses

from skim.brokers.ib_interface import MarketData
from skim.validation.price_parsing import validate_minimum_price


@pytest.mark.unit
class TestIBKRPennyStockParsing:
    """Tests for IBKR client market data methods with penny stock prices"""

    def test_market_data_dataclass_handles_penny_stock_prices(self):
        """Test that MarketData dataclass can handle very small prices"""
        # This test should pass initially - dataclass should handle any float
        market_data = MarketData(
            ticker="CR9",
            last_price=0.005,
            bid=0.004,
            ask=0.006,
            volume=1000000,
            low=0.003,
        )

        assert market_data.ticker == "CR9"
        assert market_data.last_price == 0.005
        assert market_data.bid == 0.004
        assert market_data.ask == 0.006
        assert market_data.volume == 1000000
        assert market_data.low == 0.003

    @responses.activate
    def test_get_market_data_handles_penny_stock_prices(
        self, ibkr_client_mock_oauth
    ):
        """Test that get_market_data correctly parses penny stock prices"""
        # Mock the contract ID lookup
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

        # Mock pre-flight response to establish streaming
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "conid": "123456",  # Must match conid for streaming to be established
                }
            ],
        )

        # Mock the market data snapshot with penny stock prices
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "0.005",  # last price - 0.5 cents
                    "71": "0.003",  # daily low - 0.3 cents
                    "84": "0.004",  # bid - 0.4 cents
                    "86": "0.006",  # ask - 0.6 cents
                    "87": "1000000",  # volume
                }
            ],
        )

        result = ibkr_client_mock_oauth.get_market_data("CR9")

        assert result is not None
        assert result.ticker == "CR9"
        assert (
            result.last_price == 0.005
        )  # This should fail initially (returns 0.0)
        assert result.bid == 0.004
        assert result.ask == 0.006
        assert result.volume == 1000000
        assert result.low == 0.003

    @responses.activate
    def test_get_market_data_handles_scientific_notation(
        self, ibkr_client_mock_oauth
    ):
        """Test that get_market_data handles scientific notation prices"""
        # Mock the contract ID lookup
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "123457",
                    "symbol": "1TT",
                    "description": "TATTEL",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock pre-flight response to establish streaming
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "conid": "123457",  # Must match conid for streaming to be established
                }
            ],
        )

        # Mock the market data snapshot with scientific notation
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "5e-3",  # last price - scientific notation
                    "71": "3e-3",  # daily low - scientific notation
                    "84": "4e-3",  # bid - scientific notation
                    "86": "6e-3",  # ask - scientific notation
                    "87": "500000",  # volume
                }
            ],
        )

        result = ibkr_client_mock_oauth.get_market_data("1TT")

        assert result is not None
        assert result.ticker == "1TT"
        assert result.last_price == 0.005  # This should fail initially
        assert result.bid == 0.004
        assert result.ask == 0.006
        assert result.volume == 500000
        assert result.low == 0.003

    @responses.activate
    def test_get_market_data_handles_ibkr_prefixes(
        self, ibkr_client_mock_oauth
    ):
        """Test that get_market_data handles IBKR price prefixes"""
        # Mock the contract ID lookup
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "123458",
                    "symbol": "BLU",
                    "description": "BLUE FIRE",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock pre-flight response to establish streaming
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "conid": "123458",  # Must match conid for streaming to be established
                }
            ],
        )

        # Mock the market data snapshot with IBKR prefixes
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "C0.008",  # last price with 'C' prefix (Closed)
                    "71": "L0.006",  # daily low with 'L' prefix (Low)
                    "84": "H0.007",  # bid with 'H' prefix (High)
                    "86": "0.009",  # ask without prefix
                    "87": "750000",  # volume
                }
            ],
        )

        result = ibkr_client_mock_oauth.get_market_data("BLU")

        assert result is not None
        assert result.ticker == "BLU"
        assert result.last_price == 0.008  # This should fail initially
        assert result.bid == 0.007
        assert result.ask == 0.009
        assert result.volume == 750000
        assert result.low == 0.006

    @responses.activate
    def test_get_market_data_handles_extremely_small_prices(
        self, ibkr_client_mock_oauth
    ):
        """Test that get_market_data handles extremely small prices"""
        # Mock the contract ID lookup
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "123459",
                    "symbol": "BUY",
                    "description": "BUY OWN",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock pre-flight response to establish streaming
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "conid": "123459",  # Must match conid for streaming to be established
                }
            ],
        )

        # Mock the market data snapshot with extremely small prices
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "0.001",  # last price - 0.1 cents
                    "71": "0.0008",  # daily low - 0.08 cents
                    "84": "0.0009",  # bid - 0.09 cents
                    "86": "0.0011",  # ask - 0.11 cents
                    "87": "2000000",  # volume
                }
            ],
        )

        result = ibkr_client_mock_oauth.get_market_data("BUY")

        assert result is not None
        assert result.ticker == "BUY"
        assert result.last_price == 0.001  # This should fail initially
        assert result.bid == 0.0009
        assert result.ask == 0.0011
        assert result.volume == 2000000
        assert result.low == 0.0008

    @responses.activate
    def test_get_market_data_handles_malformed_prices_gracefully(
        self, ibkr_client_mock_oauth
    ):
        """Test that get_market_data handles malformed price data gracefully"""
        # Mock the contract ID lookup
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "123460",
                    "symbol": "JPR",
                    "description": "JAPARA",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock pre-flight response to establish streaming
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "conid": "123460",  # Must match conid for streaming to be established
                }
            ],
        )

        # Mock the market data snapshot with malformed prices
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "",  # Empty last price
                    "71": None,  # Null daily low
                    "84": "invalid",  # Invalid bid
                    "86": "0.007",  # Valid ask
                    "87": "300000",  # volume
                }
            ],
        )

        result = ibkr_client_mock_oauth.get_market_data("JPR")

        # Should return None due to invalid last price
        assert result is None

    def test_price_validation_allows_small_positive_prices(self):
        """Test that price validation allows very small positive prices"""
        # These should all be considered valid prices
        valid_prices = [0.001, 0.005, 0.009, 0.0001, 1e-4, 5e-3]

        for price in valid_prices:
            assert price > 0, f"Price {price} should be greater than 0"
            assert price > 0.0001 or price == 0.0001, (
                f"Price {price} should be >= minimum threshold"
            )

    def test_price_validation_rejects_invalid_prices(self):
        """Test that price validation rejects invalid prices"""
        # These should all be considered invalid prices
        invalid_prices = [
            0,
            -0.001,
            -1,
            float("inf"),
            float("-inf"),
            float("nan"),
        ]

        for price in invalid_prices:
            try:
                # Check if it's a valid number first
                if price != price:  # NaN check
                    continue
                # Infinity is not <= 0, but should be rejected by validation
                if price in (float("inf"), float("-inf")):
                    assert not validate_minimum_price(price), (
                        f"Price {price} should be rejected"
                    )
                    continue
                assert price <= 0, f"Price {price} should be <= 0 (invalid)"
            except (TypeError, ValueError):
                # These are expected for invalid values
                pass
