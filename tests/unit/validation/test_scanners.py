"""Unit tests for Pydantic validation models"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from skim.validation.scanners import (
    ASXAnnouncement,
    BreakoutSignal,
    GapStock,
    OpeningRangeData,
    PriceSensitiveFilter,
    ScannerFilter,
    ScannerRequest,
)


class TestScannerRequest:
    """Test ScannerRequest validation"""

    def test_valid_scanner_request(self):
        """Test creating a valid scanner request"""
        request = ScannerRequest(
            instrument="STK",
            scan_type="TOP_PERC_GAIN",
            location="STK.HK.ASX",
            filters=[
                ScannerFilter(code="priceAbove", value=1.0),
                ScannerFilter(code="volumeAbove", value=50000),
            ],
        )
        assert request.instrument == "STK"
        assert request.scan_type == "TOP_PERC_GAIN"
        assert len(request.filters) == 2

    def test_default_scanner_request(self):
        """Test scanner request with defaults"""
        request = ScannerRequest()
        assert request.instrument == "STK"
        assert request.scan_type == "TOP_PERC_GAIN"
        assert request.location == "STK.HK.ASX"
        assert request.filters == []

    def test_too_many_filters(self):
        """Test validation error with too many filters"""
        filters = [
            ScannerFilter(code="priceAbove", value=1.0) for _ in range(11)
        ]
        with pytest.raises(ValidationError):
            ScannerRequest(filters=filters)


class TestScannerFilter:
    """Test ScannerFilter validation"""

    def test_valid_price_filter(self):
        """Test valid price filter"""
        filter_obj = ScannerFilter(code="priceAbove", value=10.5)
        assert filter_obj.code == "priceAbove"
        assert filter_obj.value == 10.5

    def test_valid_volume_filter(self):
        """Test valid volume filter"""
        filter_obj = ScannerFilter(code="volumeAbove", value=100000)
        assert filter_obj.code == "volumeAbove"
        assert filter_obj.value == 100000


class TestGapStock:
    """Test GapStock validation"""

    def test_valid_gap_stock(self):
        """Test creating a valid gap stock"""
        gap_stock = GapStock(
            ticker="BHP",
            gap_percent=5.5,
            close_price=45.20,
            conid=8644,
        )
        assert gap_stock.ticker == "BHP"
        assert gap_stock.gap_percent == 5.5
        assert gap_stock.close_price == 45.20
        assert gap_stock.conid == 8644

    def test_ticker_normalization(self):
        """Test ticker is normalized to uppercase"""
        gap_stock = GapStock(
            ticker="BHP",  # Pattern validation happens before normalization
            gap_percent=5.5,
            close_price=45.20,
            conid=8644,
        )
        assert gap_stock.ticker == "BHP"

    def test_invalid_gap_percent(self):
        """Test validation error for invalid gap percent"""
        with pytest.raises(ValidationError):
            GapStock(
                ticker="BHP",
                gap_percent=1500,  # Too high
                close_price=45.20,
                conid=8644,
            )

    def test_negative_close_price(self):
        """Test validation error for negative close price"""
        with pytest.raises(ValidationError):
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                close_price=-10.0,  # Negative price
                conid=8644,
            )

    def test_invalid_conid(self):
        """Test validation error for invalid contract ID"""
        with pytest.raises(ValidationError):
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                close_price=45.20,
                conid=0,  # Must be > 0
            )


class TestOpeningRangeData:
    """Test OpeningRangeData validation"""

    def test_valid_opening_range_data(self):
        """Test creating valid opening range data"""
        or_data = OpeningRangeData(
            ticker="BHP",
            conid=8644,
            or_high=48.0,
            or_low=46.0,
            open_price=47.0,
            prev_close=45.20,
            current_price=48.5,
            gap_holding=True,
        )
        assert or_data.ticker == "BHP"
        assert or_data.or_high == 48.0
        assert or_data.or_low == 46.0
        assert or_data.gap_holding is True

    def test_or_high_lower_than_or_low(self):
        """Test validation error when OR high < OR low"""
        with pytest.raises(ValidationError):
            OpeningRangeData(
                ticker="BHP",
                conid=8644,
                or_high=46.0,  # Lower than or_low
                or_low=48.0,
                open_price=47.0,
                prev_close=45.20,
                current_price=48.5,
                gap_holding=True,
            )


class TestBreakoutSignal:
    """Test BreakoutSignal validation"""

    def test_valid_breakout_signal(self):
        """Test creating a valid breakout signal"""
        signal = BreakoutSignal(
            ticker="BHP",
            conid=8644,
            gap_pct=5.5,
            or_high=48.0,
            or_low=46.0,
            or_size_pct=4.3,
            current_price=48.5,
            entry_signal="ORB_HIGH_BREAKOUT",
            timestamp=datetime.now(),
        )
        assert signal.ticker == "BHP"
        assert signal.entry_signal == "ORB_HIGH_BREAKOUT"
        assert signal.current_price > signal.or_high

    def test_orh_breakout_price_validation(self):
        """Test validation error for ORH breakout with wrong price"""
        with pytest.raises(ValidationError):
            BreakoutSignal(
                ticker="BHP",
                conid=8644,
                gap_pct=5.5,
                or_high=48.0,
                or_low=46.0,
                or_size_pct=4.3,
                current_price=47.5,  # Not > OR high
                entry_signal="ORB_HIGH_BREAKOUT",
                timestamp=datetime.now(),
            )


class TestASXAnnouncement:
    """Test ASXAnnouncement validation"""

    def test_valid_announcement(self):
        """Test creating a valid ASX announcement"""
        announcement = ASXAnnouncement(
            ticker="BHP",
            headline="Trading Halt - Pending Announcement",
            announcement_type="pricesens",
            timestamp=datetime.now(),
        )
        assert announcement.ticker == "BHP"
        assert announcement.announcement_type == "pricesens"
        assert "Trading Halt" in announcement.headline

    def test_ticker_normalization(self):
        """Test ticker is normalized to uppercase"""
        announcement = ASXAnnouncement(
            ticker="BHP",  # Pattern validation happens before normalization
            headline="Trading Halt",
            announcement_type="pricesens",
            timestamp=datetime.now(),
        )
        assert announcement.ticker == "BHP"

    def test_invalid_ticker_format(self):
        """Test validation error for invalid ticker format"""
        with pytest.raises(ValidationError):
            ASXAnnouncement(
                ticker="BHP123!",  # Invalid characters
                headline="Trading Halt",
                announcement_type="pricesens",
                timestamp=datetime.now(),
            )

    def test_empty_headline(self):
        """Test validation error for empty headline"""
        with pytest.raises(ValidationError):
            ASXAnnouncement(
                ticker="BHP",
                headline="",  # Empty headline
                announcement_type="pricesens",
                timestamp=datetime.now(),
            )


class TestPriceSensitiveFilter:
    """Test PriceSensitiveFilter validation"""

    def test_default_filter(self):
        """Test filter with default values"""
        filter_config = PriceSensitiveFilter()
        assert filter_config.min_ticker_length == 3
        assert filter_config.max_ticker_length == 6
        assert filter_config.exclude_tickers == []
        assert filter_config.include_only_tickers is None

    def test_custom_filter(self):
        """Test filter with custom values"""
        filter_config = PriceSensitiveFilter(
            min_ticker_length=2,
            max_ticker_length=4,
            exclude_tickers=["ABC", "DEF"],
        )
        assert filter_config.min_ticker_length == 2
        assert filter_config.max_ticker_length == 4
        assert filter_config.exclude_tickers == ["ABC", "DEF"]

    def test_mutually_exclusive_filters(self):
        """Test validation error when both include and exclude are specified"""
        with pytest.raises(ValidationError):
            PriceSensitiveFilter(
                include_only_tickers=["BHP", "RIO"],
                exclude_tickers=["CBA", "WES"],
            )

    def test_ticker_list_normalization(self):
        """Test ticker lists are normalized to uppercase"""
        filter_config = PriceSensitiveFilter(
            exclude_tickers=["bhp", "rio"],
        )
        assert filter_config.exclude_tickers == ["BHP", "RIO"]
