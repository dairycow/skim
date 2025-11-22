"""Tests for IBKRMarketData handling of daily low field."""

import pytest

from skim.brokers.ib_interface import MarketData


@pytest.mark.unit
class TestIBKRMarketDataWithLow:
    """Tests for IBKRMarketData market data parsing."""

    def test_market_data_dataclass_includes_low_field(self):
        """MarketData should include the daily low field."""
        market_data = MarketData(
            ticker="AAPL",
            conid="265598",
            last_price=150.0,
            high=152.0,
            low=148.0,
            bid=149.5,
            ask=150.5,
            bid_size=100,
            ask_size=200,
            volume=1000,
            open=149.0,
            prior_close=147.0,
            change_percent=2.04,
        )

        assert market_data.ticker == "AAPL"
        assert market_data.last_price == 150.0
        assert market_data.bid == 149.5
        assert market_data.ask == 150.5
        assert market_data.volume == 1000
        assert market_data.low == 148.0

    @pytest.mark.asyncio
    async def test_get_market_data_includes_daily_low(self, mocker):
        """get_market_data should surface the daily low when provided."""
        from skim.brokers.ibkr_market_data import IBKRMarketData

        mock_client = mocker.AsyncMock()
        market_data_service = IBKRMarketData(mock_client)
        market_data_service._establish_market_data_stream = mocker.AsyncMock()

        contract_response = [
            {
                "conid": "265598",
                "symbol": "AAPL",
                "description": "APPLE INC",
                "sections": [{"secType": "STK"}],
            }
        ]
        snapshot_response = [
            {
                "31": "150.0",
                "71": "148.0",
                "84": "149.5",
                "86": "150.5",
                "87": "1000",
            }
        ]

        mock_client._request = mocker.AsyncMock(
            side_effect=[contract_response, snapshot_response]
        )

        result = await market_data_service.get_market_data("AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.last_price == 150.0
        assert result.bid == 149.5
        assert result.ask == 150.5
        assert result.volume == 1000
        assert result.low == 148.0

    @pytest.mark.asyncio
    async def test_get_market_data_handles_missing_daily_low(self, mocker):
        """get_market_data should default low to 0.0 when missing."""
        from skim.brokers.ibkr_market_data import IBKRMarketData

        mock_client = mocker.AsyncMock()
        market_data_service = IBKRMarketData(mock_client)
        market_data_service._establish_market_data_stream = mocker.AsyncMock()

        contract_response = [
            {
                "conid": "265598",
                "symbol": "AAPL",
                "description": "APPLE INC",
                "sections": [{"secType": "STK"}],
            }
        ]
        snapshot_response = [
            {
                "31": "150.0",
                "84": "149.5",
                "86": "150.5",
                "87": "1000",
            }
        ]

        mock_client._request = mocker.AsyncMock(
            side_effect=[contract_response, snapshot_response]
        )

        result = await market_data_service.get_market_data("AAPL")

        assert result is not None
        assert result.ticker == "AAPL"
        assert result.last_price == 150.0
        assert result.bid == 149.5
        assert result.ask == 150.5
        assert result.volume == 1000
        assert result.low == 0.0
