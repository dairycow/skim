"""Unit tests for trader module - TDD RED phase"""

import pytest

from skim.data.models import Candidate, Position
from skim.trader import Trader


@pytest.fixture
def trader(mocker):
    """Create a Trader instance with mocked IBKR client"""
    mock_ib_client = mocker.Mock()
    mock_db = mocker.Mock()

    # Patch the imports
    mocker.patch("skim.trader.IBKRClient", return_value=mock_ib_client)

    # Create trader
    trader = Trader(ib_client=mock_ib_client, db=mock_db)

    return trader


class TestTraderExecuteBreakouts:
    """Test executing breakout entries"""

    def test_execute_breakouts_returns_int(self, trader):
        """Should return number of breakouts executed"""
        candidates = []
        result = trader.execute_breakouts(candidates)
        assert isinstance(result, int)

    def test_execute_breakouts_skips_candidates_with_price_not_above_orh(
        self, trader, mocker
    ):
        """Should skip candidates where current price <= or_high"""
        candidate = Candidate(
            ticker="BHP",
            or_high=50.0,
            or_low=48.0,
            scan_date="2025-11-21",
            status="watching",
        )

        # Mock market data with price not above ORH
        market_data = mocker.Mock()
        market_data.last_price = 49.50  # Below or_high of 50.0
        trader.ib_client.get_market_data.return_value = market_data

        result = trader.execute_breakouts([candidate])

        assert result == 0
        assert not trader.db.create_position.called

    def test_execute_breakouts_buys_when_price_above_orh(self, trader, mocker):
        """Should buy when current price > or_high"""
        candidate = Candidate(
            ticker="BHP",
            or_high=50.0,
            or_low=48.0,
            scan_date="2025-11-21",
            status="watching",
        )

        # Mock market data with price above ORH
        market_data = mocker.Mock()
        market_data.last_price = 50.50  # Above or_high of 50.0
        trader.ib_client.get_market_data.return_value = market_data

        # Mock order placement
        order_result = mocker.Mock()
        order_result.filled_price = 50.50
        order_result.status = "filled"
        trader.ib_client.place_order.return_value = order_result

        # Mock position creation
        trader.db.create_position.return_value = 1

        result = trader.execute_breakouts([candidate])

        assert result == 1
        assert trader.db.create_position.called

    def test_execute_breakouts_sets_stop_loss_to_or_low(self, trader, mocker):
        """Stop loss should be set to or_low"""
        candidate = Candidate(
            ticker="BHP",
            or_high=50.0,
            or_low=48.0,
            scan_date="2025-11-21",
            status="watching",
        )

        market_data = mocker.Mock()
        market_data.last_price = 50.50
        trader.ib_client.get_market_data.return_value = market_data

        order_result = mocker.Mock()
        order_result.filled_price = 50.50
        order_result.status = "filled"
        trader.ib_client.place_order.return_value = order_result

        trader.db.create_position.return_value = 1

        trader.execute_breakouts([candidate])

        # Verify create_position was called with or_low as stop_loss
        call_args = trader.db.create_position.call_args
        assert call_args[1]["stop_loss"] == 48.0

    def test_execute_breakouts_updates_candidate_status(self, trader, mocker):
        """Candidate status should be updated to 'entered'"""
        candidate = Candidate(
            ticker="BHP",
            or_high=50.0,
            or_low=48.0,
            scan_date="2025-11-21",
            status="watching",
        )

        market_data = mocker.Mock()
        market_data.last_price = 50.50
        trader.ib_client.get_market_data.return_value = market_data

        order_result = mocker.Mock()
        order_result.filled_price = 50.50
        trader.ib_client.place_order.return_value = order_result

        trader.db.create_position.return_value = 1

        trader.execute_breakouts([candidate])

        # Verify candidate status was updated
        trader.db.update_candidate_status.assert_called_with("BHP", "entered")

    def test_execute_breakouts_returns_zero_when_no_candidates(self, trader):
        """Should return 0 when no candidates"""
        result = trader.execute_breakouts([])
        assert result == 0

    def test_execute_breakouts_handles_missing_market_data(
        self, trader, mocker
    ):
        """Should skip candidates with missing market data"""
        candidate = Candidate(
            ticker="BHP",
            or_high=50.0,
            or_low=48.0,
            scan_date="2025-11-21",
            status="watching",
        )

        # Market data is None
        trader.ib_client.get_market_data.return_value = None

        result = trader.execute_breakouts([candidate])

        assert result == 0
        assert not trader.db.create_position.called


class TestTraderExecuteStops:
    """Test executing stop loss exits"""

    def test_execute_stops_returns_int(self, trader):
        """Should return number of stops executed"""
        positions = []
        result = trader.execute_stops(positions)
        assert isinstance(result, int)

    def test_execute_stops_sells_when_price_below_stop(self, trader, mocker):
        """Should sell when current price < stop_loss"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        # Mock market data with price below stop
        market_data = mocker.Mock()
        market_data.last_price = 47.50  # Below stop_loss of 48.0
        trader.ib_client.get_market_data.return_value = market_data

        # Mock order placement
        order_result = mocker.Mock()
        order_result.filled_price = 47.50
        order_result.status = "filled"
        trader.ib_client.place_order.return_value = order_result

        result = trader.execute_stops([position])

        assert result == 1
        assert trader.ib_client.place_order.called

    def test_execute_stops_skips_when_price_above_stop(self, trader, mocker):
        """Should not sell when current price >= stop_loss"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        # Mock market data with price above stop
        market_data = mocker.Mock()
        market_data.last_price = 48.50  # Above stop_loss of 48.0
        trader.ib_client.get_market_data.return_value = market_data

        result = trader.execute_stops([position])

        assert result == 0
        assert not trader.ib_client.place_order.called

    def test_execute_stops_closes_position(self, trader, mocker):
        """Position should be marked as closed after stop hit"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=50.50,
            stop_loss=48.0,
            entry_date="2025-11-21T10:15:00",
            status="open",
            id=1,
        )

        market_data = mocker.Mock()
        market_data.last_price = 47.50
        trader.ib_client.get_market_data.return_value = market_data

        order_result = mocker.Mock()
        order_result.filled_price = 47.50
        trader.ib_client.place_order.return_value = order_result

        trader.execute_stops([position])

        # Verify close_position was called
        trader.db.close_position.assert_called_once()
        call_args = trader.db.close_position.call_args
        assert call_args[1]["position_id"] == 1
        assert call_args[1]["exit_price"] == 47.50

    def test_execute_stops_returns_zero_when_no_positions(self, trader):
        """Should return 0 when no positions"""
        result = trader.execute_stops([])
        assert result == 0

    def test_execute_stops_handles_missing_market_data(self, trader, mocker):
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

        # Market data is None
        trader.ib_client.get_market_data.return_value = None

        result = trader.execute_stops([position])

        assert result == 0
        assert not trader.db.close_position.called

    def test_execute_stops_handles_multiple_positions(self, trader, mocker):
        """Should process multiple positions independently"""
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

        # Position 1 hits stop (below), Position 2 doesn't (above)
        market_data_1 = mocker.Mock()
        market_data_1.last_price = 47.50  # Below stop

        market_data_2 = mocker.Mock()
        market_data_2.last_price = 119.0  # Above stop

        trader.ib_client.get_market_data.side_effect = [
            market_data_1,
            market_data_2,
        ]

        order_result = mocker.Mock()
        order_result.filled_price = 47.50
        trader.ib_client.place_order.return_value = order_result

        result = trader.execute_stops([position1, position2])

        assert result == 1
        assert trader.db.close_position.called
