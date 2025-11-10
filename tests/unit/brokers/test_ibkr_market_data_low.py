"""Tests for IBKR client market data functionality with daily low support.

Tests the enhanced market data methods that include daily low price (field 7).
Follows TDD approach - tests are written first, then implementation.
"""

import pytest
import responses

from skim.brokers.ib_interface import MarketData
from skim.brokers.ibkr_client import IBKRClient


@pytest.mark.unit
class TestIBKRMarketDataWithLow:
    """Tests for IBKR client market data methods with daily low field"""

    def test_market_data_dataclass_includes_low_field(self):
        """Test that MarketData dataclass includes low field"""
        # This test should fail initially because low field doesn't exist yet
        market_data = MarketData(
            ticker="AAPL",
            last_price=150.0,
            bid=149.5,
            ask=150.5,
            volume=1000,
            low=148.0,  # This should cause the test to fail initially
        )

        assert market_data.ticker == "AAPL"
        assert market_data.last_price == 150.0
        assert market_data.bid == 149.5
        assert market_data.ask == 150.5
        assert market_data.volume == 1000
        assert market_data.low == 148.0  # This assertion should fail initially

    @responses.activate
    def test_get_market_data_includes_daily_low(self, ibkr_client_mock_oauth):
        """Test that get_market_data returns daily low price (field 7)"""
        # Mock the contract ID lookup
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "265598",
                    "symbol": "AAPL",
                    "description": "APPLE INC",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock the market data snapshot with field 7 (daily low)
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "150.0",  # last price
                    "84": "149.5",  # bid
                    "86": "150.5",  # ask
                    "87": "1000",  # volume
                    "7": "148.0",  # daily low - this should be captured
                }
            ],
        )

        result = ibkr_client_mock_oauth.get_market_data("AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.last_price == 150.0
        assert result.bid == 149.5
        assert result.ask == 150.5
        assert result.volume == 1000
        assert result.low == 148.0  # This should fail initially

    @responses.activate
    def test_get_market_data_handles_missing_daily_low(self, ibkr_client_mock_oauth):
        """Test that get_market_data handles missing daily low gracefully"""
        # Mock the contract ID lookup
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/secdef/search",
            json=[
                {
                    "conid": "265598",
                    "symbol": "AAPL",
                    "description": "APPLE INC",
                    "sections": [{"secType": "STK"}],
                }
            ],
        )

        # Mock the market data snapshot WITHOUT field 7
        responses.add(
            responses.GET,
            f"{ibkr_client_mock_oauth.BASE_URL}/iserver/marketdata/snapshot",
            json=[
                {
                    "31": "150.0",  # last price
                    "84": "149.5",  # bid
                    "86": "150.5",  # ask
                    "87": "1000",  # volume
                    # Missing field 7 (daily low)
                }
            ],
        )

        result = ibkr_client_mock_oauth.get_market_data("AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.last_price == 150.0
        assert result.low == 0.0  # Should default to 0.0 when missing
