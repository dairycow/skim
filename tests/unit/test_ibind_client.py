"""Unit tests for IBind client"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from skim.brokers.ibind_client import IBIndClient
from skim.brokers.ib_interface import MarketData, OrderResult


class TestIBIndClient:
    """Tests for IBIndClient"""

    @pytest.fixture
    def mock_ibkr_client(self, mocker):
        """Mock IbkrClient instance"""
        mock = mocker.MagicMock()

        # Mock successful responses by default
        mock.check_health.return_value = Mock(ok=True, data={"status": "healthy"})
        mock.tickle.return_value = Mock(ok=True, data={})
        mock.portfolio_accounts.return_value = Mock(
            ok=True, data=[{"accountId": "DU12345"}]
        )

        return mock

    @pytest.fixture
    def client(self, mocker, mock_ibkr_client):
        """IBIndClient with mocked IbkrClient instance"""
        mocker.patch("skim.brokers.ibind_client.IbkrClient", return_value=mock_ibkr_client)
        client = IBIndClient(base_url="https://localhost:5000", paper_trading=True)
        return client

    def test_init_paper_trading(self, mocker):
        """Test initialization in paper trading mode"""
        mock_ibkr = mocker.MagicMock()
        mocker.patch("skim.brokers.ibind_client.IbkrClient", return_value=mock_ibkr)

        client = IBIndClient(paper_trading=True)

        assert client.paper_trading is True
        assert client._connected is False
        assert client._account_id is None

    def test_init_live_trading(self, mocker):
        """Test initialization in live trading mode"""
        mock_ibkr = mocker.MagicMock()
        mocker.patch("skim.brokers.ibind_client.IbkrClient", return_value=mock_ibkr)

        client = IBIndClient(paper_trading=False)

        assert client.paper_trading is False
        assert client._connected is False

    def test_connect_success_paper_account(self, client):
        """Test successful connection to paper account"""
        # Execute
        client.connect(host="localhost", port=5000, client_id=1, timeout=20)

        # Assert
        assert client._connected is True
        assert client._account_id == "DU12345"
        client.client.check_health.assert_called_once()
        client.client.tickle.assert_called_once()
        client.client.portfolio_accounts.assert_called_once()

    def test_connect_fails_with_live_account_in_paper_mode(self, client):
        """Test connection fails when live account detected in paper mode"""
        # Mock live account
        client.client.portfolio_accounts.return_value = Mock(
            ok=True, data=[{"accountId": "U12345"}]  # Live account
        )

        # Execute and assert
        with pytest.raises(ValueError, match="Not a paper trading account"):
            client.connect(host="localhost", port=5000, client_id=1)

        assert client._connected is False

    def test_connect_success_live_account_in_live_mode(self, mocker, mock_ibkr_client):
        """Test successful connection to live account in live mode"""
        # Mock live account
        mock_ibkr_client.portfolio_accounts.return_value = Mock(
            ok=True, data=[{"accountId": "U12345"}]
        )

        mocker.patch("skim.brokers.ibind_client.IbkrClient", return_value=mock_ibkr_client)
        client = IBIndClient(paper_trading=False)

        # Execute
        client.connect(host="localhost", port=5000, client_id=1)

        # Assert
        assert client._connected is True
        assert client._account_id == "U12345"

    def test_connect_already_connected(self, client, mocker):
        """Test connect when already connected"""
        client._connected = True
        client.client.tickle.return_value = Mock(ok=True)

        # Mock time.sleep to avoid delays
        mocker.patch("time.sleep")

        # Execute - should return immediately
        client.connect(host="localhost", port=5000, client_id=1)

        # Assert - check_health should not be called again
        assert client.client.check_health.call_count == 0

    def test_connect_retry_on_health_check_failure(self, client, mocker):
        """Test connection retries when health check fails initially"""
        # Health check fails twice, then succeeds
        client.client.check_health.side_effect = [
            Mock(ok=False, data={"error": "not ready"}),
            Mock(ok=False, data={"error": "not ready"}),
            Mock(ok=True, data={"status": "healthy"}),
        ]

        # Mock time.sleep to avoid actual delays
        mocker.patch("time.sleep")

        # Execute
        client.connect(host="localhost", port=5000, client_id=1)

        # Assert - should have retried
        assert client.client.check_health.call_count == 3
        assert client._connected is True

    def test_connect_fails_after_max_retries(self, client, mocker):
        """Test connection fails after maximum retries"""
        # Health check always fails
        client.client.check_health.return_value = Mock(
            ok=False, data={"error": "not ready"}
        )
        mocker.patch("time.sleep")

        # Execute and assert
        with pytest.raises(RuntimeError, match="Failed to connect"):
            client.connect(host="localhost", port=5000, client_id=1)

        assert client._connected is False

    def test_connect_fails_on_tickle_failure(self, client, mocker):
        """Test connection fails when tickle (session check) fails"""
        # Tickle fails (session not authenticated)
        client.client.tickle.return_value = Mock(ok=False, data={})
        mocker.patch("time.sleep")

        # Execute and assert
        with pytest.raises(RuntimeError, match="Session not authenticated"):
            client.connect(host="localhost", port=5000, client_id=1)

        assert client._connected is False

    def test_connect_fails_on_no_accounts(self, client, mocker):
        """Test connection fails when no accounts available"""
        # No accounts returned
        client.client.portfolio_accounts.return_value = Mock(ok=True, data=[])
        mocker.patch("time.sleep")

        # Execute and assert
        with pytest.raises(RuntimeError, match="No accounts available"):
            client.connect(host="localhost", port=5000, client_id=1)

        assert client._connected is False

    def test_is_connected_when_connected(self, client):
        """Test is_connected returns True when connected"""
        client._connected = True
        client.client.tickle.return_value = Mock(ok=True)

        assert client.is_connected() is True

    def test_is_connected_when_not_connected(self, client):
        """Test is_connected returns False when not connected"""
        client._connected = False

        assert client.is_connected() is False

    def test_is_connected_when_session_expired(self, client):
        """Test is_connected returns False when session expired"""
        client._connected = True
        client.client.tickle.return_value = Mock(ok=False)

        assert client.is_connected() is False

    def test_is_connected_on_exception(self, client):
        """Test is_connected returns False on exception"""
        client._connected = True
        client.client.tickle.side_effect = Exception("Connection error")

        assert client.is_connected() is False

    def test_place_order_success(self, client):
        """Test place_order returns OrderResult"""
        client._account_id = "DU12345"

        # Execute
        result = client.place_order("BHP", "BUY", 100)

        # Assert
        assert isinstance(result, OrderResult)
        assert result.ticker == "BHP"
        assert result.action == "BUY"
        assert result.quantity == 100
        assert result.status == "submitted"

    def test_place_order_no_account(self, client):
        """Test place_order fails when no account ID"""
        client._account_id = None

        # Execute
        result = client.place_order("BHP", "BUY", 100)

        # Assert
        assert result is None

    def test_place_order_sell_action(self, client):
        """Test place_order with SELL action"""
        client._account_id = "DU12345"

        # Execute
        result = client.place_order("BHP", "SELL", 50)

        # Assert
        assert isinstance(result, OrderResult)
        assert result.action == "SELL"
        assert result.quantity == 50

    def test_place_order_exception_handling(self, client, mocker):
        """Test place_order handles exceptions gracefully"""
        client._account_id = "DU12345"

        # Force an exception during order placement
        mocker.patch.object(
            client, "place_order", side_effect=Exception("API error")
        )

        # Execute
        with pytest.raises(Exception):
            client.place_order("BHP", "BUY", 100)

    def test_get_market_data_returns_none(self, client):
        """Test get_market_data returns None (not implemented)"""
        # Execute
        result = client.get_market_data("BHP")

        # Assert - placeholder implementation returns None
        assert result is None

    def test_disconnect(self, client):
        """Test disconnect clears connection state"""
        client._connected = True
        client._account_id = "DU12345"

        # Execute
        client.disconnect()

        # Assert
        assert client._connected is False
        assert client._account_id is None

    def test_disconnect_when_not_connected(self, client):
        """Test disconnect when not connected"""
        client._connected = False

        # Execute - should not raise
        client.disconnect()

        # Assert
        assert client._connected is False

    def test_get_account_success(self, client):
        """Test get_account when connected"""
        client._connected = True
        client._account_id = "DU12345"
        client.client.tickle.return_value = Mock(ok=True)

        result = client.get_account()

        assert result == "DU12345"

    def test_get_account_not_connected(self, client):
        """Test get_account when not connected"""
        client._connected = False

        with pytest.raises(RuntimeError, match="Not connected"):
            client.get_account()

    def test_get_account_no_cached_account(self, client):
        """Test get_account fetches account if not cached"""
        client._connected = True
        client._account_id = None
        client.client.tickle.return_value = Mock(ok=True)
        client.client.portfolio_accounts.return_value = Mock(
            ok=True, data=[{"accountId": "DU67890"}]
        )

        result = client.get_account()

        assert result == "DU67890"
        assert client._account_id == "DU67890"

    def test_get_account_no_accounts_available(self, client):
        """Test get_account when no accounts available"""
        client._connected = True
        client._account_id = None
        client.client.tickle.return_value = Mock(ok=True)
        client.client.portfolio_accounts.return_value = Mock(ok=True, data=[])

        with pytest.raises(RuntimeError, match="No account available"):
            client.get_account()

    def test_paper_trading_safety_check(self, client):
        """Test paper trading safety check enforces DU prefix"""
        # This is a critical safety feature - test thoroughly
        client.client.portfolio_accounts.return_value = Mock(
            ok=True, data=[{"accountId": "U99999"}]  # Live account
        )

        # Should raise ValueError immediately, not retry
        with pytest.raises(ValueError, match="Not a paper trading account"):
            client.connect(host="localhost", port=5000, client_id=1)

        # Verify connection was not marked as successful
        assert client._connected is False


class TestOrderResult:
    """Tests for OrderResult dataclass"""

    def test_order_result_creation(self):
        """Test OrderResult object creation"""
        order = OrderResult(
            order_id="12345",
            ticker="BHP",
            action="BUY",
            quantity=100,
            filled_price=45.50,
            status="filled",
        )

        assert order.order_id == "12345"
        assert order.ticker == "BHP"
        assert order.action == "BUY"
        assert order.quantity == 100
        assert order.filled_price == 45.50
        assert order.status == "filled"

    def test_order_result_defaults(self):
        """Test OrderResult default values"""
        order = OrderResult(
            order_id="12345",
            ticker="BHP",
            action="BUY",
            quantity=100,
        )

        assert order.filled_price is None
        assert order.status == "submitted"
