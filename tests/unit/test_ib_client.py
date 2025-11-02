"""Unit tests for IB client"""

import socket
from unittest.mock import MagicMock, Mock, call, patch

import pytest
from ib_insync import IB, MarketOrder, Stock, Trade

from skim.brokers.ib_client import IBClient
from skim.brokers.ib_interface import MarketData


class TestIBClient:
    """Tests for IBClient"""

    @pytest.fixture
    def mock_ib(self, mocker):
        """Mock IB instance"""
        mock = mocker.MagicMock(spec=IB)
        mock.isConnected.return_value = False
        mock.managedAccounts.return_value = ["DU12345"]
        return mock

    @pytest.fixture
    def client(self, mocker, mock_ib):
        """IBClient with mocked IB instance"""
        client = IBClient(paper_trading=True)
        client.ib = mock_ib
        return client

    def test_init_paper_trading(self):
        """Test initialization in paper trading mode"""
        client = IBClient(paper_trading=True)
        assert client.paper_trading is True
        assert client._connected is False

    def test_init_live_trading(self):
        """Test initialization in live trading mode"""
        client = IBClient(paper_trading=False)
        assert client.paper_trading is False
        assert client._connected is False

    def test_connect_success_paper_account(self, client, mock_ib, mocker):
        """Test successful connection to paper account"""
        # Mock network test
        mocker.patch.object(client, "_test_network_connectivity", return_value=True)

        # Execute
        client.connect(host="localhost", port=4002, client_id=1, timeout=20)

        # Assert
        mock_ib.connect.assert_called_once_with(
            "localhost", 4002, clientId=1, timeout=20
        )
        assert client._connected is True

    def test_connect_fails_with_live_account_in_paper_mode(
        self, client, mock_ib, mocker
    ):
        """Test connection fails when live account detected in paper mode"""
        # Mock network test
        mocker.patch.object(client, "_test_network_connectivity", return_value=True)

        # Mock live account
        mock_ib.managedAccounts.return_value = ["U12345"]  # Live account

        # Execute and assert
        with pytest.raises(ValueError, match="Not a paper trading account"):
            client.connect(host="localhost", port=4002, client_id=1)

        assert client._connected is False

    def test_connect_success_live_account_in_live_mode(self, mock_ib, mocker):
        """Test successful connection to live account in live mode"""
        client = IBClient(paper_trading=False)
        client.ib = mock_ib

        # Mock network test and live account
        mocker.patch.object(client, "_test_network_connectivity", return_value=True)
        mock_ib.managedAccounts.return_value = ["U12345"]  # Live account

        # Execute
        client.connect(host="localhost", port=4001, client_id=1)

        # Assert
        assert client._connected is True

    def test_connect_already_connected(self, client, mock_ib, mocker):
        """Test connect when already connected"""
        client._connected = True
        mock_ib.isConnected.return_value = True

        # Execute
        client.connect(host="localhost", port=4002, client_id=1)

        # Assert - should not attempt to reconnect
        mock_ib.connect.assert_not_called()

    def test_connect_retry_on_network_failure(self, client, mock_ib, mocker):
        """Test connection retries when network test fails initially"""
        # Network fails twice, then succeeds
        mocker.patch.object(
            client,
            "_test_network_connectivity",
            side_effect=[False, False, True],
        )

        # Mock time.sleep to avoid actual delays
        mocker.patch("time.sleep")

        # Execute
        client.connect(host="localhost", port=4002, client_id=1)

        # Assert - should have retried
        assert mock_ib.connect.call_count == 1
        assert client._connected is True

    def test_connect_fails_after_max_retries(self, client, mock_ib, mocker):
        """Test connection fails after maximum retries"""
        # Network test always fails
        mocker.patch.object(client, "_test_network_connectivity", return_value=False)
        mocker.patch("time.sleep")

        # Execute and assert
        with pytest.raises(RuntimeError, match="Failed to connect"):
            client.connect(host="localhost", port=4002, client_id=1)

        assert client._connected is False

    def test_connect_client_id_already_in_use(self, client, mock_ib, mocker):
        """Test connection fails immediately when client ID in use"""
        mocker.patch.object(client, "_test_network_connectivity", return_value=True)

        # Mock connection failure with client ID error
        mock_ib.connect.side_effect = Exception("clientid already in use")

        # Execute and assert - should not retry
        with pytest.raises(Exception, match="clientid already in use"):
            client.connect(host="localhost", port=4002, client_id=1)

        # Should fail immediately without retries
        assert mock_ib.connect.call_count == 1

    def test_test_network_connectivity_success(self, client, mocker):
        """Test successful network connectivity check"""
        # Mock socket operations
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 0  # Success
        mock_socket.close = Mock()

        mocker.patch("socket.gethostbyname", return_value="127.0.0.1")
        mocker.patch("socket.socket", return_value=mock_socket)

        result = client._test_network_connectivity("localhost", 4002)

        assert result is True
        mock_socket.connect_ex.assert_called_once_with(("localhost", 4002))
        mock_socket.close.assert_called_once()

    def test_test_network_connectivity_connection_refused(self, client, mocker):
        """Test network connectivity check with connection refused"""
        mock_socket = Mock()
        mock_socket.connect_ex.return_value = 61  # Connection refused
        mock_socket.close = Mock()

        mocker.patch("socket.gethostbyname", return_value="127.0.0.1")
        mocker.patch("socket.socket", return_value=mock_socket)

        result = client._test_network_connectivity("localhost", 4002)

        assert result is False

    def test_test_network_connectivity_dns_failure(self, client, mocker):
        """Test network connectivity check with DNS failure"""
        mocker.patch(
            "socket.gethostbyname", side_effect=socket.gaierror("DNS lookup failed")
        )

        result = client._test_network_connectivity("invalid.host", 4002)

        assert result is False

    def test_is_connected_when_connected(self, client, mock_ib):
        """Test is_connected returns True when connected"""
        client._connected = True
        mock_ib.isConnected.return_value = True

        assert client.is_connected() is True

    def test_is_connected_when_not_connected(self, client, mock_ib):
        """Test is_connected returns False when not connected"""
        client._connected = False
        mock_ib.isConnected.return_value = False

        assert client.is_connected() is False

    def test_is_connected_when_ib_disconnected(self, client, mock_ib):
        """Test is_connected returns False when IB reports disconnected"""
        client._connected = True
        mock_ib.isConnected.return_value = False

        assert client.is_connected() is False

    def test_place_order_success(self, client, mock_ib, mocker):
        """Test successful order placement"""
        # Mock contract and trade
        mock_contract = Mock(spec=Stock)
        mock_trade = Mock(spec=Trade)
        mock_trade.isDone.return_value = True
        mock_trade.orderStatus.avgFillPrice = 45.50

        mocker.patch("skim.brokers.ib_client.Stock", return_value=mock_contract)
        mock_ib.qualifyContracts.return_value = None
        mock_ib.placeOrder.return_value = mock_trade
        mock_ib.sleep = Mock()

        # Execute
        result = client.place_order("BHP", "BUY", 100, wait_for_fill=True)

        # Assert
        assert result == mock_trade
        mock_ib.qualifyContracts.assert_called_once_with(mock_contract)
        assert mock_ib.placeOrder.called

    def test_place_order_timeout(self, client, mock_ib, mocker):
        """Test order placement with timeout"""
        mock_contract = Mock(spec=Stock)
        mock_trade = Mock(spec=Trade)
        mock_trade.isDone.return_value = False  # Never fills
        mock_trade.orderStatus.status = "Submitted"

        mocker.patch("skim.brokers.ib_client.Stock", return_value=mock_contract)
        mock_ib.qualifyContracts.return_value = None
        mock_ib.placeOrder.return_value = mock_trade
        mock_ib.sleep = Mock()

        # Mock time to force timeout
        start_time = 1000.0
        mocker.patch("time.time", side_effect=[start_time, start_time + 31])

        # Execute
        result = client.place_order("BHP", "BUY", 100, wait_for_fill=True)

        # Assert - should return trade even if not filled
        assert result == mock_trade

    def test_place_order_without_waiting(self, client, mock_ib, mocker):
        """Test order placement without waiting for fill"""
        mock_contract = Mock(spec=Stock)
        mock_trade = Mock(spec=Trade)

        mocker.patch("skim.brokers.ib_client.Stock", return_value=mock_contract)
        mock_ib.qualifyContracts.return_value = None
        mock_ib.placeOrder.return_value = mock_trade

        # Execute
        result = client.place_order("BHP", "BUY", 100, wait_for_fill=False)

        # Assert
        assert result == mock_trade
        mock_ib.sleep.assert_not_called()

    def test_place_order_failure(self, client, mock_ib, mocker):
        """Test order placement failure"""
        mock_contract = Mock(spec=Stock)

        mocker.patch("skim.brokers.ib_client.Stock", return_value=mock_contract)
        mock_ib.qualifyContracts.side_effect = Exception("Contract not found")

        # Execute
        result = client.place_order("INVALID", "BUY", 100)

        # Assert
        assert result is None

    def test_get_market_data_success(self, client, mock_ib, mocker):
        """Test successful market data retrieval"""
        mock_contract = Mock(spec=Stock)
        mock_ticker = Mock()
        mock_ticker.last = 45.50

        mocker.patch("skim.brokers.ib_client.Stock", return_value=mock_contract)
        mocker.patch("time.sleep")
        mock_ib.qualifyContracts.return_value = None
        mock_ib.reqMktData.return_value = mock_ticker

        # Execute
        result = client.get_market_data("BHP")

        # Assert
        assert isinstance(result, MarketData)
        assert result.ticker == "BHP"
        assert result.last_price == 45.50
        assert result.contract == mock_contract

    def test_get_market_data_no_price(self, client, mock_ib, mocker):
        """Test market data retrieval with no valid price"""
        mock_contract = Mock(spec=Stock)
        mock_ticker = Mock()
        mock_ticker.last = 0  # Invalid price

        mocker.patch("skim.brokers.ib_client.Stock", return_value=mock_contract)
        mocker.patch("time.sleep")
        mock_ib.qualifyContracts.return_value = None
        mock_ib.reqMktData.return_value = mock_ticker

        # Execute
        result = client.get_market_data("BHP")

        # Assert
        assert result is None

    def test_get_market_data_failure(self, client, mock_ib, mocker):
        """Test market data retrieval failure"""
        mock_contract = Mock(spec=Stock)

        mocker.patch("skim.brokers.ib_client.Stock", return_value=mock_contract)
        mock_ib.qualifyContracts.side_effect = Exception("Contract not found")

        # Execute
        result = client.get_market_data("INVALID")

        # Assert
        assert result is None

    def test_disconnect_when_connected(self, client, mock_ib):
        """Test disconnect when connected"""
        client._connected = True
        mock_ib.isConnected.return_value = True

        # Execute
        client.disconnect()

        # Assert
        mock_ib.disconnect.assert_called_once()
        assert client._connected is False

    def test_disconnect_when_not_connected(self, client, mock_ib):
        """Test disconnect when not connected"""
        client._connected = False
        mock_ib.isConnected.return_value = False

        # Execute
        client.disconnect()

        # Assert
        mock_ib.disconnect.assert_not_called()

    def test_get_account_success(self, client, mock_ib):
        """Test get_account when connected"""
        client._connected = True
        mock_ib.isConnected.return_value = True
        mock_ib.managedAccounts.return_value = ["DU12345"]

        result = client.get_account()

        assert result == "DU12345"

    def test_get_account_not_connected(self, client, mock_ib):
        """Test get_account when not connected"""
        client._connected = False
        mock_ib.isConnected.return_value = False

        with pytest.raises(RuntimeError, match="Not connected"):
            client.get_account()

    def test_get_account_no_accounts(self, client, mock_ib):
        """Test get_account when no accounts available"""
        client._connected = True
        mock_ib.isConnected.return_value = True
        mock_ib.managedAccounts.return_value = []

        with pytest.raises(RuntimeError, match="No managed accounts"):
            client.get_account()

    def test_ensure_connection_when_disconnected(self, client, mock_ib):
        """Test ensure_connection raises when disconnected"""
        client._connected = False
        mock_ib.isConnected.return_value = False

        with pytest.raises(RuntimeError, match="Connection lost"):
            client.ensure_connection()

    def test_ensure_connection_when_connected(self, client, mock_ib):
        """Test ensure_connection passes when connected"""
        client._connected = True
        mock_ib.isConnected.return_value = True

        # Should not raise
        client.ensure_connection()


class TestMarketData:
    """Tests for MarketData class"""

    def test_market_data_creation(self):
        """Test MarketData object creation"""
        mock_contract = Mock(spec=Stock)
        market_data = MarketData(
            ticker="BHP", last_price=45.50, contract=mock_contract
        )

        assert market_data.ticker == "BHP"
        assert market_data.last_price == 45.50
        assert market_data.contract == mock_contract
