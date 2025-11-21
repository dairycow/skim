"""Unit tests for monitor module - TDD RED phase"""

import pytest

from skim.data.models import Position
from skim.monitor import Monitor


@pytest.fixture
def monitor(mocker):
    """Create a Monitor instance with mocked IBKR client"""
    mock_ib_client = mocker.Mock()

    # Patch the imports
    mocker.patch("skim.monitor.IBKRClient", return_value=mock_ib_client)

    # Create monitor
    monitor = Monitor(ib_client=mock_ib_client)

    return monitor


class TestMonitorGetCurrentPrice:
    """Test getting current prices for stocks"""

    def test_get_current_price_returns_float(self, monitor, mocker):
        """Should return current price as float"""
        market_data = mocker.Mock()
        market_data.last_price = 50.50
        monitor.ib_client.get_market_data.return_value = market_data

        price = monitor.get_current_price("BHP")

        assert isinstance(price, float)
        assert price == 50.50

    def test_get_current_price_returns_none_when_market_data_unavailable(
        self, monitor
    ):
        """Should return None when market data unavailable"""
        monitor.ib_client.get_market_data.return_value = None

        price = monitor.get_current_price("BHP")

        assert price is None

    def test_get_current_price_handles_market_data_with_zero_price(
        self, monitor, mocker
    ):
        """Should return None when price is 0 or invalid"""
        market_data = mocker.Mock()
        market_data.last_price = 0.0
        monitor.ib_client.get_market_data.return_value = market_data

        price = monitor.get_current_price("BHP")

        assert price is None

    def test_get_current_price_returns_none_on_exception(self, monitor):
        """Should return None if price fetch fails"""
        monitor.ib_client.get_market_data.side_effect = Exception(
            "Market data error"
        )

        price = monitor.get_current_price("BHP")

        assert price is None


class TestMonitorCheckStops:
    """Test checking which positions have hit stops"""

    def test_check_stops_returns_list(self, monitor):
        """Should return list of positions with stops hit"""
        positions = []
        result = monitor.check_stops(positions)
        assert isinstance(result, list)

    def test_check_stops_identifies_stop_hits(self, monitor, mocker):
        """Should identify positions where price < stop_loss"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        # Mock current price below stop
        market_data = mocker.Mock()
        market_data.last_price = 47.50
        monitor.ib_client.get_market_data.return_value = market_data

        result = monitor.check_stops([position])

        assert len(result) == 1
        assert result[0].ticker == "BHP"

    def test_check_stops_excludes_positions_above_stop(self, monitor, mocker):
        """Should exclude positions where price >= stop_loss"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        # Mock current price above stop
        market_data = mocker.Mock()
        market_data.last_price = 49.50
        monitor.ib_client.get_market_data.return_value = market_data

        result = monitor.check_stops([position])

        assert len(result) == 0

    def test_check_stops_handles_multiple_positions(self, monitor, mocker):
        """Should process multiple positions and identify which hit stops"""
        position1 = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        position2 = Position(
            ticker="RIO",
            quantity=50,
            entry_price=120.0,
            stop_loss=118.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=2,
        )

        # Position 1 hits stop, Position 2 doesn't
        market_data_1 = mocker.Mock()
        market_data_1.last_price = 47.50  # Below stop

        market_data_2 = mocker.Mock()
        market_data_2.last_price = 119.0  # Above stop

        monitor.ib_client.get_market_data.side_effect = [
            market_data_1,
            market_data_2,
        ]

        result = monitor.check_stops([position1, position2])

        assert len(result) == 1
        assert result[0].ticker == "BHP"

    def test_check_stops_returns_empty_when_no_positions(self, monitor):
        """Should return empty list when no positions provided"""
        result = monitor.check_stops([])
        assert result == []

    def test_check_stops_handles_missing_market_data(self, monitor, mocker):
        """Should skip positions with missing market data"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        # Market data unavailable
        monitor.ib_client.get_market_data.return_value = None

        result = monitor.check_stops([position])

        assert len(result) == 0

    def test_check_stops_handles_price_exactly_at_stop(self, monitor, mocker):
        """Should not trigger when price equals stop (>= check)"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        # Price exactly at stop
        market_data = mocker.Mock()
        market_data.last_price = 48.0
        monitor.ib_client.get_market_data.return_value = market_data

        result = monitor.check_stops([position])

        # Should not include (price not below stop)
        assert len(result) == 0

    def test_check_stops_handles_exception_for_single_position(self, monitor):
        """Should skip position if price fetch fails"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        monitor.ib_client.get_market_data.side_effect = Exception(
            "Market error"
        )

        result = monitor.check_stops([position])

        assert len(result) == 0
