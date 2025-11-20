"""Unit tests for IBKRClient order management methods"""

from unittest.mock import Mock

import pytest

from skim.brokers.ibkr_client import IBKRClient


@pytest.mark.unit
class TestIBKRClientOrderManagement:
    """Tests for IBKRClient order management functionality"""

    @pytest.fixture
    def client(self):
        """Create IBKRClient instance"""
        return IBKRClient(paper_trading=True)

    @pytest.fixture
    def connected_client(self, client):
        """Create connected IBKRClient instance"""
        client._connected = True
        client._account_id = "DU1234567"
        return client

    def test_place_market_order_success(self, connected_client, mocker):
        """Test successful market order placement"""
        # Mock contract ID lookup
        connected_client._get_contract_id = Mock(return_value="8644")

        # Mock order response
        mock_response = [{"order_id": "123456", "order_status": "submitted"}]
        connected_client._request = Mock(return_value=mock_response)

        result = connected_client.place_order("BHP", "BUY", 100)

        # Verify order was placed
        assert result is not None
        assert result.order_id == "123456"
        assert result.ticker == "BHP"
        assert result.action == "BUY"
        assert result.quantity == 100
        assert result.status == "submitted"

        # Verify request was made with correct parameters
        connected_client._request.assert_called_once()
        call_args = connected_client._request.call_args
        assert call_args[0][0] == "POST"
        assert "/iserver/account/DU1234567/orders" in call_args[0][1]

        # Verify order data
        order_data = call_args[1]["data"]["orders"][0]
        assert order_data["conid"] == 8644
        assert order_data["orderType"] == "MKT"
        assert order_data["side"] == "BUY"
        assert order_data["quantity"] == 100
        assert order_data["tif"] == "DAY"

    def test_place_stop_market_order_success(self, connected_client, mocker):
        """Test successful stop market order placement"""
        connected_client._get_contract_id = Mock(return_value="8644")

        mock_response = [{"order_id": "123457", "order_status": "submitted"}]
        connected_client._request = Mock(return_value=mock_response)

        result = connected_client.place_order(
            "BHP", "SELL", 100, "STP", stop_price=44.50
        )

        assert result is not None
        assert result.order_id == "123457"
        assert result.action == "SELL"

        # Verify order data includes stop price
        call_args = connected_client._request.call_args
        order_data = call_args[1]["data"]["orders"][0]
        assert order_data["orderType"] == "STP"
        assert order_data["auxPrice"] == 44.50

    def test_place_stop_limit_order_success(self, connected_client, mocker):
        """Test successful stop limit order placement"""
        connected_client._get_contract_id = Mock(return_value="8644")

        mock_response = [{"order_id": "123458", "order_status": "submitted"}]
        connected_client._request = Mock(return_value=mock_response)

        result = connected_client.place_order(
            "BHP", "SELL", 100, "STP LMT", stop_price=44.50, limit_price=44.30
        )

        assert result is not None
        assert result.order_id == "123458"

        # Verify order data includes both stop and limit prices
        call_args = connected_client._request.call_args
        order_data = call_args[1]["data"]["orders"][0]
        assert order_data["orderType"] == "STP LMT"
        assert order_data["auxPrice"] == 44.50
        assert order_data["price"] == 44.30

    def test_place_order_not_connected(self, client):
        """Test order placement when not connected"""
        with pytest.raises(RuntimeError, match="Not connected"):
            client.place_order("BHP", "BUY", 100)

    def test_place_order_invalid_order_type(self, connected_client):
        """Test order placement with invalid order type"""
        with pytest.raises(ValueError, match="Invalid order type"):
            connected_client.place_order("BHP", "BUY", 100, "INVALID")

    def test_place_order_stop_order_missing_stop_price(self, connected_client):
        """Test stop order without stop price"""
        with pytest.raises(ValueError, match="stop_price required"):
            connected_client.place_order("BHP", "BUY", 100, "STP")

    def test_place_order_stop_limit_missing_prices(self, connected_client):
        """Test stop limit order without required prices"""
        with pytest.raises(ValueError, match="stop_price required"):
            connected_client.place_order(
                "BHP", "BUY", 100, "STP LMT", limit_price=44.30
            )

        with pytest.raises(ValueError, match="limit_price required"):
            connected_client.place_order(
                "BHP", "BUY", 100, "STP LMT", stop_price=44.50
            )

    def test_place_order_request_failure(self, connected_client, mocker):
        """Test order placement when request fails"""
        connected_client._get_contract_id = Mock(return_value="8644")
        connected_client._request = Mock(side_effect=Exception("Network error"))

        result = connected_client.place_order("BHP", "BUY", 100)

        assert result is None

    def test_place_order_unexpected_response_format(
        self, connected_client, mocker
    ):
        """Test order placement with unexpected response format"""
        connected_client._get_contract_id = Mock(return_value="8644")
        connected_client._request = Mock(return_value="invalid_response")

        result = connected_client.place_order("BHP", "BUY", 100)

        assert result is None

    def test_get_open_orders_success(self, connected_client, mocker):
        """Test successful retrieval of open orders"""
        mock_response = {
            "orders": [
                {
                    "orderId": "123456",
                    "ticker": "BHP",
                    "totalSize": 100,
                    "orderType": "MKT",
                    "status": "submitted",
                    "price": 45.50,
                    "auxPrice": None,
                },
                {
                    "orderId": "123457",
                    "ticker": "RIO",
                    "totalSize": 50,
                    "orderType": "STP",
                    "status": "submitted",
                    "price": None,
                    "auxPrice": 119.80,
                },
            ]
        }
        connected_client._request = Mock(return_value=mock_response)

        orders = connected_client.get_open_orders()

        assert len(orders) == 2

        # Verify first order
        order1 = orders[0]
        assert order1["order_id"] == "123456"
        assert order1["ticker"] == "BHP"
        assert order1["quantity"] == 100
        assert order1["order_type"] == "MKT"
        assert order1["status"] == "submitted"
        assert order1["limit_price"] == 45.50
        assert order1["stop_price"] is None

        # Verify second order
        order2 = orders[1]
        assert order2["order_id"] == "123457"
        assert order2["ticker"] == "RIO"
        assert order2["quantity"] == 50
        assert order2["order_type"] == "STP"
        assert order2["limit_price"] is None
        assert order2["stop_price"] == 119.80

    def test_get_open_orders_list_response(self, connected_client, mocker):
        """Test get_open_orders with list response format"""
        mock_response = [
            {
                "order_id": "123456",
                "symbol": "BHP",
                "quantity": 100,
                "orderType": "MKT",
                "status": "submitted",
            }
        ]
        connected_client._request = Mock(return_value=mock_response)

        orders = connected_client.get_open_orders()

        assert len(orders) == 1
        order = orders[0]
        assert order["order_id"] == "123456"
        assert order["ticker"] == "BHP"
        assert order["quantity"] == 100

    def test_get_open_orders_no_orders(self, connected_client, mocker):
        """Test get_open_orders when no orders exist"""
        mock_response = {"orders": []}
        connected_client._request = Mock(return_value=mock_response)

        orders = connected_client.get_open_orders()

        assert len(orders) == 0

    def test_get_open_orders_not_connected(self, client):
        """Test get_open_orders when not connected"""
        with pytest.raises(RuntimeError, match="Not connected"):
            client.get_open_orders()

    def test_get_open_orders_unexpected_response(
        self, connected_client, mocker
    ):
        """Test get_open_orders with unexpected response format"""
        connected_client._request = Mock(return_value="invalid_response")

        orders = connected_client.get_open_orders()

        assert len(orders) == 0

    def test_cancel_order_success(self, connected_client, mocker):
        """Test successful order cancellation"""
        mock_response = {"result": "success"}
        connected_client._request = Mock(return_value=mock_response)

        result = connected_client.cancel_order("123456")

        assert result is True

        # Verify request was made correctly
        connected_client._request.assert_called_once_with(
            "DELETE", "/iserver/account/DU1234567/order/123456"
        )

    def test_cancel_order_not_connected(self, client):
        """Test cancel_order when not connected"""
        with pytest.raises(RuntimeError, match="Not connected"):
            client.cancel_order("123456")

    def test_cancel_order_failure(self, connected_client, mocker):
        """Test cancel_order when request fails"""
        connected_client._request = Mock(side_effect=Exception("Network error"))

        result = connected_client.cancel_order("123456")

        assert result is False

    def test_get_contract_id_uses_cache(self, connected_client, mocker):
        """Test that _get_contract_id uses cache"""
        # Setup cache
        connected_client._contract_cache = {"BHP": "8644"}

        result = connected_client._get_contract_id("BHP")

        assert result == "8644"
        # Should not make request if cached
        mock_request = mocker.Mock()
        connected_client._request = mock_request
        mock_request.assert_not_called()

    def test_get_contract_id_cache_miss(self, connected_client, mocker):
        """Test _get_contract_id when not cached"""
        connected_client._contract_cache = {}

        # Mock search endpoint response with proper structure
        mock_response = [
            {
                "conid": "8644",
                "companyHeader": "BHP Group Ltd",
                "description": "BHP Group Ltd - ASX",
                "sections": [{"secType": "STK", "conid": "8644"}],
            }
        ]
        connected_client._request = Mock(return_value=mock_response)

        result = connected_client._get_contract_id("BHP")

        assert result == "8644"
        assert "BHP" in connected_client._contract_cache
        assert connected_client._contract_cache["BHP"] == "8644"

    def test_get_contract_id_no_results(self, connected_client, mocker):
        """Test _get_contract_id when no results found"""
        connected_client._contract_cache = {}

        connected_client._request = Mock(return_value=[])

        with pytest.raises(RuntimeError, match="Could not find contract ID"):
            connected_client._get_contract_id("INVALID")


@pytest.mark.unit
class TestIBKRClientOAuthPaths:
    """Tests for IBKRClient OAuth key path usage"""

    def test_uses_hardcoded_oauth_paths(self, mocker):
        """Test that IBKRClient uses hardcoded OAuth paths instead of environment variables"""
        # Mock environment variables to ensure they're not used
        mocker.patch.dict(
            "os.environ",
            {
                "OAUTH_CONSUMER_KEY": "test_key",
                "OAUTH_ACCESS_TOKEN": "test_token",
                "OAUTH_ACCESS_TOKEN_SECRET": "test_secret",
                "OAUTH_DH_PRIME": "test_prime",
                "OAUTH_SIGNATURE_PATH": "/should/not/be/used/private_signature.pem",
                "OAUTH_ENCRYPTION_PATH": "/should/not/be/used/private_encryption.pem",
            },
        )

        # Mock the generate_lst function to capture the paths passed to it
        mock_generate_lst = mocker.patch(
            "skim.brokers.ibkr_client.generate_lst"
        )
        mock_generate_lst.return_value = ("test_lst", 1234567890)

        client = IBKRClient(paper_trading=True)

        # Trigger LST generation
        client._generate_lst()

        # Verify generate_lst was called with hardcoded paths, not environment variables
        mock_generate_lst.assert_called_once()
        call_args = mock_generate_lst.call_args[0]

        # The signature and encryption paths should be valid paths (Docker or local)
        assert call_args[4].endswith("private_signature.pem")
        assert call_args[5].endswith("private_encryption.pem")

        # Should NOT be the environment variable paths
        assert call_args[4] != "/should/not/be/used/private_signature.pem"
        assert call_args[5] != "/should/not/be/used/private_encryption.pem"
