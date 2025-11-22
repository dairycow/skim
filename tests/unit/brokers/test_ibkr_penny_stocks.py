"""Tests for IBKRMarketData handling of penny stock prices."""

import pytest

from skim.brokers.ib_interface import MarketData
from skim.validation.price_parsing import validate_minimum_price


@pytest.mark.unit
class TestIBKRPennyStockParsing:
    """Tests for IBKRMarketData with sub-cent prices."""

    def test_market_data_dataclass_handles_penny_stock_prices(self):
        """MarketData should support sub-cent values."""
        market_data = MarketData(
            ticker="CR9",
            conid="123456",
            last_price=0.005,
            high=0.007,
            low=0.003,
            bid=0.004,
            ask=0.006,
            bid_size=5000,
            ask_size=5000,
            volume=1000000,
            open=0.004,
            prior_close=0.004,
            change_percent=25.0,
        )

        assert market_data.ticker == "CR9"
        assert market_data.last_price == 0.005
        assert market_data.bid == 0.004
        assert market_data.ask == 0.006
        assert market_data.volume == 1000000
        assert market_data.low == 0.003

    @pytest.mark.asyncio
    async def test_get_market_data_handles_penny_stock_prices(self, mocker):
        """get_market_data should parse penny stock prices accurately."""
        from skim.brokers.ibkr_market_data import IBKRMarketData

        mock_client = mocker.AsyncMock()
        market_data_service = IBKRMarketData(mock_client)
        market_data_service._establish_market_data_stream = mocker.AsyncMock()

        contract_response = [
            {
                "conid": "123456",
                "symbol": "CR9",
                "description": "CROWN RESORTS",
                "sections": [{"secType": "STK"}],
            }
        ]
        snapshot_response = [
            {
                "55": "TEST",
                "31": "0.005",
                "70": "0.007",
                "71": "0.003",
                "84": "0.004",
                "85": "5000",
                "86": "0.006",
                "87": "1000000",
                "88": "5000",
                "7295": "0.004",
                "7741": "0.004",
                "83": "25.0",
            }
        ]

        mock_client._request = mocker.AsyncMock(
            side_effect=[contract_response, snapshot_response]
        )

        result = await market_data_service.get_market_data("123456")

        assert result is not None
        assert validate_minimum_price(result.last_price)
        assert result.last_price == 0.005
        assert result.bid == 0.004
        assert result.ask == 0.006
        assert result.volume == 1000000
        assert result.low == 0.003
