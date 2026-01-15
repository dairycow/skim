"""Tests for domain models"""

from datetime import datetime

import pytest

from skim.domain.models.candidate import Candidate, GapCandidate, NewsCandidate
from skim.domain.models.event import Event, EventType
from skim.domain.models.position import Position
from skim.domain.models.price import Price
from skim.domain.models.signal import Signal
from skim.domain.models.ticker import Ticker


class TestTicker:
    """Tests for Ticker value object"""

    def test_ticker_creation(self):
        """Test creating a valid ticker"""
        ticker = Ticker(symbol="BHP")
        assert ticker.symbol == "BHP"

    def test_ticker_str(self):
        """Test ticker string representation"""
        ticker = Ticker(symbol="CBA")
        assert str(ticker) == "CBA"

    def test_ticker_empty_invalid(self):
        """Test that empty ticker raises error"""
        with pytest.raises(ValueError):
            Ticker(symbol="")

    def test_ticker_to_persistence(self):
        """Test ticker serialization to string"""
        ticker = Ticker(symbol="BHP")
        assert ticker.to_persistence() == "BHP"

    def test_ticker_from_persistence(self):
        """Test ticker deserialization from string"""
        ticker = Ticker.from_persistence("CBA")
        assert ticker.symbol == "CBA"

    def test_ticker_round_trip(self):
        """Test ticker serialization round trip"""
        original = Ticker(symbol="RIO")
        persisted = original.to_persistence()
        restored = Ticker.from_persistence(persisted)
        assert restored == original


class TestPrice:
    """Tests for Price value object"""

    def test_price_creation(self):
        """Test creating a valid price"""
        price = Price(value=100.50, timestamp=datetime.now())
        assert price.value == 100.50

    def test_price_valid(self):
        """Test price validation"""
        price = Price(value=50.0, timestamp=datetime.now())
        assert price.is_valid is True

    def test_price_invalid(self):
        """Test invalid price"""
        price = Price(value=-10.0, timestamp=datetime.now())
        assert price.is_valid is False

    def test_price_zero(self):
        """Test zero price is invalid"""
        price = Price(value=0.0, timestamp=datetime.now())
        assert price.is_valid is False

    def test_price_to_persistence(self):
        """Test price serialization to float"""
        price = Price(value=100.50, timestamp=datetime.now())
        assert price.to_persistence() == 100.50

    def test_price_from_persistence(self):
        """Test price deserialization from float"""
        price = Price.from_persistence(46.75)
        assert price.value == 46.75
        assert price.timestamp is not None

    def test_price_round_trip(self):
        """Test price serialization round trip (value only)"""
        original = Price(value=123.45, timestamp=datetime.now())
        persisted = original.to_persistence()
        restored = Price.from_persistence(persisted)
        assert restored.value == original.value


class TestPosition:
    """Tests for Position domain model"""

    def test_position_creation(self):
        """Test creating a position"""
        ticker = Ticker(symbol="RIO")
        entry_price = Price(value=120.0, timestamp=datetime.now())
        stop_loss = Price(value=115.0, timestamp=datetime.now())

        position = Position(
            id=1,
            ticker=ticker,
            quantity=100,
            entry_price=entry_price,
            stop_loss=stop_loss,
            entry_date=datetime.now(),
        )

        assert position.id == 1
        assert str(position.ticker) == "RIO"
        assert position.quantity == 100
        assert position.is_open is True

    def test_position_pnl_none_when_open(self):
        """Test PnL is None when position is open"""
        ticker = Ticker(symbol="BHP")
        position = Position(
            ticker=ticker,
            quantity=50,
            entry_price=Price(value=100.0, timestamp=datetime.now()),
            stop_loss=Price(value=95.0, timestamp=datetime.now()),
            entry_date=datetime.now(),
        )

        assert position.pnl is None


class TestCandidate:
    """Tests for Candidate domain model"""

    def test_candidate_creation(self):
        """Test creating a basic candidate"""
        ticker = Ticker(symbol="NST")
        candidate = Candidate(
            ticker=ticker,
            scan_date=datetime.now(),
            strategy_name="orh_breakout",
        )

        assert str(candidate.ticker) == "NST"
        assert candidate.status == "watching"

    def test_gap_candidate(self):
        """Test creating a gap candidate"""
        ticker = Ticker(symbol="IMD")
        candidate = GapCandidate(
            ticker=ticker,
            scan_date=datetime.now(),
            gap_percent=5.5,
            conid=12345,
        )

        assert candidate.gap_percent == 5.5
        assert candidate.conid == 12345

    def test_news_candidate(self):
        """Test creating a news candidate"""
        ticker = Ticker(symbol="ANN")
        candidate = NewsCandidate(
            ticker=ticker,
            scan_date=datetime.now(),
            headline="Company announces record profits",
        )

        assert "record profits" in candidate.headline


class TestSignal:
    """Tests for Signal domain model"""

    def test_signal_creation(self):
        """Test creating a trading signal"""
        ticker = Ticker(symbol="WES")
        signal = Signal(
            ticker=ticker,
            action="BUY",
            quantity=100,
            price=Price(value=50.0, timestamp=datetime.now()),
            reason="Price above ORH",
        )

        assert signal.action == "BUY"
        assert signal.quantity == 100
        assert signal.reason == "Price above ORH"


class TestEvent:
    """Tests for Event domain model"""

    def test_event_creation(self):
        """Test creating an event"""
        event = Event(
            type=EventType.SCAN,
            data={"candidates_found": 5},
        )

        assert event.type == EventType.SCAN
        assert event.data["candidates_found"] == 5  # type: ignore[reportOptionalSubscript]
        assert event.data["ticker"] == "BHP"  # type: ignore[reportOptionalSubscript]
        assert event.data["action"] == "BUY"  # type: ignore[reportOptionalSubscript]

        assert event.timestamp is not None  # type: ignore[reportOptionalSubscript]

    def test_event_types(self):
        """Test all event types exist"""
        assert EventType.SCAN.value == "scan"
        assert EventType.TRADE.value == "trade"
        assert EventType.MANAGE.value == "manage"
        assert EventType.ALERT.value == "alert"
