"""Unit tests for scanner modules"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
import requests

from skim.scanners.asx_announcements import ASXAnnouncementScanner


class TestASXAnnouncementScanner:
    """Tests for ASXAnnouncementScanner"""

    def test_fetch_price_sensitive_announcements_success(self, mocker):
        """Test successful fetch of price-sensitive announcements"""
        scanner = ASXAnnouncementScanner()

        # Mock HTML response with price-sensitive announcements
        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>Strong earnings report</td>
                    <td>10:30</td>
                </tr>
                <tr>
                    <td>RIO</td>
                    <td>Regular announcement</td>
                    <td>11:00</td>
                </tr>
                <tr class="pricesens">
                    <td>FMG</td>
                    <td>Major project update</td>
                    <td>12:00</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        assert len(results) == 2
        assert "BHP" in results
        assert "FMG" in results
        assert "RIO" not in results

    def test_fetch_price_sensitive_announcements_empty(self, mocker):
        """Test fetch with no price-sensitive announcements"""
        scanner = ASXAnnouncementScanner()

        mock_html = """
        <html>
        <body>
            <table>
                <tr>
                    <td>BHP</td>
                    <td>Regular announcement</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        assert len(results) == 0

    def test_fetch_price_sensitive_announcements_network_error(self, mocker):
        """Test fetch with network error"""
        scanner = ASXAnnouncementScanner()

        mocker.patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("Network error"),
        )

        results = scanner.fetch_price_sensitive_tickers()

        # Should return empty set on error
        assert len(results) == 0
        assert isinstance(results, set)

    def test_fetch_price_sensitive_announcements_timeout(self, mocker):
        """Test fetch with timeout"""
        scanner = ASXAnnouncementScanner()

        mocker.patch(
            "requests.get", side_effect=requests.exceptions.Timeout("Timeout")
        )

        results = scanner.fetch_price_sensitive_tickers()

        assert len(results) == 0

    def test_fetch_price_sensitive_announcements_http_error(self, mocker):
        """Test fetch with HTTP error"""
        scanner = ASXAnnouncementScanner()

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("404 Not Found")
        )

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        assert len(results) == 0

    def test_fetch_price_sensitive_announcements_malformed_html(self, mocker):
        """Test fetch with malformed HTML"""
        scanner = ASXAnnouncementScanner()

        mock_html = (
            "<html><body><table><tr class='pricesens'></table></body></html>"
        )

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        # Should handle malformed HTML gracefully
        assert isinstance(results, set)

    def test_fetch_with_whitespace_in_ticker(self, mocker):
        """Test fetch with whitespace around ticker"""
        scanner = ASXAnnouncementScanner()

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>  BHP  </td>
                    <td>Announcement</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        assert "BHP" in results

    def test_fetch_removes_duplicates(self, mocker):
        """Test that duplicate tickers are removed"""
        scanner = ASXAnnouncementScanner()

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>First announcement</td>
                </tr>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>Second announcement</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        assert len(results) == 1
        assert "BHP" in results

    def test_fetch_with_empty_ticker(self, mocker):
        """Test fetch with empty ticker field"""
        scanner = ASXAnnouncementScanner()

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td></td>
                    <td>Announcement with no ticker</td>
                </tr>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>Valid announcement</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        # Should only include valid ticker
        assert len(results) == 1
        assert "BHP" in results

    def test_fetch_price_sensitive_announcements_detailed_success(self, mocker):
        """Test successful fetch of detailed price-sensitive announcements"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(include_only_tickers=None)

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>Strong earnings report expected</td>
                    <td>10:30</td>
                </tr>
                <tr class="pricesens">
                    <td>RIO</td>
                    <td>Major acquisition announcement</td>
                    <td>11:00</td>
                </tr>
                <tr>
                    <td>FMG</td>
                    <td>Regular dividend announcement</td>
                    <td>12:00</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        assert len(results) == 2
        assert results[0].ticker == "BHP"
        assert results[0].headline == "Strong earnings report expected"
        assert results[0].announcement_type == "pricesens"
        assert results[1].ticker == "RIO"
        assert results[1].headline == "Major acquisition announcement"

    def test_fetch_price_sensitive_announcements_with_custom_filter(
        self, mocker
    ):
        """Test detailed fetch with custom filter configuration"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(
            min_ticker_length=3,
            max_ticker_length=3,
            min_headline_length=15,
            max_headline_length=50,
            include_only_tickers=["BHP"],
            exclude_tickers=[],
        )

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>This is a good headline length</td>
                    <td>10:30</td>
                </tr>
                <tr class="pricesens">
                    <td>RIO123</td>
                    <td>Too long headline that exceeds maximum length</td>
                    <td>11:00</td>
                </tr>
                <tr class="pricesens">
                    <td>FM</td>
                    <td>Short</td>
                    <td>12:00</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        # Only BHP should pass all filters
        assert len(results) == 1
        assert results[0].ticker == "BHP"

    def test_fetch_price_sensitive_announcements_with_exclude_filter(
        self, mocker
    ):
        """Test detailed fetch with exclude ticker filter"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(
            exclude_tickers=["BHP", "RIO"], include_only_tickers=None
        )

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>Earnings announcement</td>
                    <td>10:30</td>
                </tr>
                <tr class="pricesens">
                    <td>RIO</td>
                    <td>Acquisition news</td>
                    <td>11:00</td>
                </tr>
                <tr class="pricesens">
                    <td>FMG</td>
                    <td>Project update</td>
                    <td>12:00</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        # Only FMG should remain (BHP and RIO excluded)
        assert len(results) == 1
        assert results[0].ticker == "FMG"

    def test_fetch_price_sensitive_announcements_insufficient_cells(
        self, mocker
    ):
        """Test detailed fetch with insufficient table cells"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(include_only_tickers=None)

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <!-- Missing headline cell -->
                </tr>
                <tr class="pricesens">
                    <td>RIO</td>
                    <td>Valid announcement</td>
                    <td>11:00</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        # Only RIO should be valid (BHP has insufficient cells)
        assert len(results) == 1
        assert results[0].ticker == "RIO"

    def test_fetch_price_sensitive_announcements_validation_error_handling(
        self, mocker
    ):
        """Test detailed fetch handles individual validation errors gracefully"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(include_only_tickers=None)

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>Valid announcement</td>
                    <td>10:30</td>
                </tr>
                <tr class="pricesens">
                    <td></td>
                    <td>Invalid empty ticker</td>
                    <td>11:00</td>
                </tr>
                <tr class="pricesens">
                    <td>RIO</td>
                    <td>Another valid announcement</td>
                    <td>12:00</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        # Should skip invalid ticker but include valid ones
        assert len(results) == 2
        assert all(
            announcement.ticker in ["BHP", "RIO"] for announcement in results
        )

    def test_fetch_price_sensitive_announcements_detailed_timeout(self, mocker):
        """Test detailed fetch with timeout error"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(include_only_tickers=None)

        mocker.patch(
            "requests.get", side_effect=requests.exceptions.Timeout("Timeout")
        )

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        assert len(results) == 0
        assert isinstance(results, list)

    def test_fetch_price_sensitive_announcements_detailed_request_error(
        self, mocker
    ):
        """Test detailed fetch with general request error"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(include_only_tickers=None)

        mocker.patch(
            "requests.get",
            side_effect=requests.exceptions.ConnectionError("Network error"),
        )

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        assert len(results) == 0
        assert isinstance(results, list)

    def test_fetch_price_sensitive_announcements_detailed_http_error(
        self, mocker
    ):
        """Test detailed fetch with HTTP error"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(include_only_tickers=None)

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = (
            requests.exceptions.HTTPError("500 Server Error")
        )

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        assert len(results) == 0
        assert isinstance(results, list)

    def test_fetch_price_sensitive_announcements_default_filter(self, mocker):
        """Test detailed fetch uses default filter when none provided"""
        scanner = ASXAnnouncementScanner()

        mock_html = """
        <html>
        <body>
            <table>
                <tr class="pricesens">
                    <td>BHP</td>
                    <td>Valid announcement with proper length</td>
                    <td>10:30</td>
                </tr>
            </table>
        </body>
        </html>
        """

        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.get", return_value=mock_response)

        # Call without filter parameter
        results = scanner.fetch_price_sensitive_announcements()

        assert len(results) == 1
        assert results[0].ticker == "BHP"

    def test_fetch_price_sensitive_announcements_unexpected_error(self, mocker):
        """Test detailed fetch handles unexpected parsing errors"""
        from skim.validation.scanners import PriceSensitiveFilter

        scanner = ASXAnnouncementScanner()
        filter_config = PriceSensitiveFilter(include_only_tickers=None)

        # Mock BeautifulSoup to raise an exception
        mocker.patch(
            "skim.scanners.asx_announcements.BeautifulSoup",
            side_effect=Exception("Parsing error"),
        )

        results = scanner.fetch_price_sensitive_announcements(filter_config)

        assert len(results) == 0
        assert isinstance(results, list)


class TestIBKRGapScanner:
    """Tests for IBKRGapScanner"""

    def test_scan_for_gaps_success(self, mocker):
        """Test successful scan for gap stocks using IBKR scanner"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        # Mock IBKR scanner response with real field structure
        mock_scanner_results = [
            {
                "conid": "8644",
                "symbol": "BHP",
                "companyHeader": "BHP Group Ltd - ASX",
                "today_open": 47.68,  # 5.5% gap from 45.20
                "previous_close": 45.20,
                "last_price": 48.00,
                "change_percent": 6.19,
                "volume": 1000000,
            },
            {
                "conid": "8653",
                "symbol": "RIO",
                "companyHeader": "Rio Tinto Ltd - ASX",
                "today_open": 125.56,  # 4.2% gap from 120.50
                "previous_close": 120.50,
                "last_price": 126.00,
                "change_percent": 4.56,
                "volume": 750000,
            },
        ]

        mock_client.run_scanner.return_value = mock_scanner_results

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )
        scanner = IBKRGapScanner()
        scanner._connected = True  # Mock connected state
        mock_client = Mock()

        # Mock IBKR scanner response with real field structure
        mock_scanner_results = [
            {
                "conid": "8644",
                "symbol": "BHP",
                "today_open": 47.68,  # 5.5% gap from 45.20
                "previous_close": 45.20,
                "last_price": 48.00,
                "change_percent": 6.19,
                "volume": 1000000,
            },
            {
                "conid": "8653",
                "symbol": "RIO",
                "today_open": 125.56,  # 4.2% gap from 120.50
                "previous_close": 120.50,
                "last_price": 126.00,
                "change_percent": 4.56,
                "volume": 750000,
            },
        ]

        mock_client.run_scanner.return_value = mock_scanner_results

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 2
        assert results[0].ticker == "BHP"
        assert (
            abs(results[0].gap_percent - 6.19) < 0.01
        )  # Using scanner's change_percent directly

        assert results[0].conid == 8644

    def test_scan_for_gaps_empty_response(self, mocker):
        """Test scan with empty response from IBKR scanner"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        # Mock the scan_for_gaps method to return empty results
        mock_scan = mocker.patch.object(
            IBKRGapScanner, "scan_for_gaps", return_value=[]
        )

        scanner = IBKRGapScanner()
        scanner._connected = True  # Mock connected state

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 0
        mock_scan.assert_called_once_with(min_gap=3.0)

    def test_track_opening_range_success(self, mocker):
        """Test successful opening range tracking"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner
        from skim.validation.scanners import GapStock

        # Mock gap stocks
        gap_stocks = [
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                conid=8644,
            ),
            GapStock(
                ticker="RIO",
                gap_percent=4.2,
                conid=8653,
            ),
        ]

        # Mock market data responses for each ticker
        def mock_get_market_data_or_tracking(ticker):
            if ticker == "BHP":
                mock_data = Mock()
                mock_data.last_price = 47.80
                return mock_data
            elif ticker == "RIO":
                mock_data = Mock()
                mock_data.last_price = 124.80
                return mock_data
            return None

        # Mock extended market data for previous close
        def mock_get_market_data_extended(conid):
            if conid == "8644":  # BHP
                return {"previous_close": 45.20}
            elif conid == "8653":  # RIO
                return {"previous_close": 120.50}
            return {}

        mock_client = Mock()
        mock_client.get_market_data.side_effect = (
            mock_get_market_data_or_tracking
        )
        mock_client.get_market_data_extended.side_effect = (
            mock_get_market_data_extended
        )
        mock_client.is_connected.return_value = True

        # Patch IBKRClient before creating scanner
        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()

        # Mock the connect method to avoid real API calls and set connected state
        mocker.patch.object(scanner, "connect")
        scanner._connected = True  # Set connected state manually

        scanner = IBKRGapScanner()

        # Mock the connect method to avoid real API calls and set connected state
        mocker.patch.object(scanner, "connect")
        scanner._connected = True  # Set connected state manually

        # Mock gap stocks
        gap_stocks = [
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                conid=8644,
            ),
            GapStock(
                ticker="RIO",
                gap_percent=4.2,
                conid=8653,
            ),
        ]

        # Mock market data responses for each ticker
        def mock_get_market_data(ticker):
            if ticker == "BHP":
                mock_data = Mock()
                mock_data.last_price = 47.80
                return mock_data
            elif ticker == "RIO":
                mock_data = Mock()
                mock_data.last_price = 124.80
                return mock_data
            return None

        mock_client = Mock()
        mock_client.get_market_data.side_effect = mock_get_market_data
        mock_client.is_connected.return_value = True

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        # Mock time.sleep to speed up test and time.time to control loop
        mocker.patch("time.sleep")
        start_time = 1000.0
        mocker.patch(
            "time.time",
            side_effect=[start_time, start_time + 1, start_time + 61],
        )

        results = scanner.track_opening_range(gap_stocks, duration_seconds=60)

        assert len(results) == 2
        assert results[0].ticker == "BHP"
        assert results[0].conid == 8644
        assert results[0].gap_holding is True  # Gap is holding

    def test_track_opening_range_gap_not_holding(self, mocker):
        """Test opening range tracking where gap fails to hold"""
        from skim.scanners.ibkr_gap_scanner import (
            GapStock,
            IBKRGapScanner,
        )

        gap_stocks = [
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                conid=8644,
            ),
        ]

        # Mock market data where price falls more than 5% from opening
        call_count = 0

        def mock_get_market_data_gap_fail(ticker):
            nonlocal call_count
            call_count += 1
            if ticker == "BHP":
                mock_data = Mock()
                if call_count == 1:
                    mock_data.last_price = 44.80  # First call - opening price
                elif call_count == 2:
                    mock_data.last_price = (
                        40.00  # Second call - drops more than 5%
                    )
                else:
                    mock_data.last_price = 40.00  # Subsequent calls
                return mock_data
            return None

        # Mock extended market data for previous close
        def mock_get_market_data_extended(conid):
            if conid == "8644":  # BHP
                return {"previous_close": 45.20}
            return {}

        mock_client = Mock()
        mock_client.get_market_data.side_effect = mock_get_market_data_gap_fail
        mock_client.get_market_data_extended.side_effect = (
            mock_get_market_data_extended
        )
        mock_client.is_connected.return_value = True

        # Patch IBKRClient before creating scanner
        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()

        # Mock connect method to avoid real API calls
        mocker.patch.object(scanner, "connect")
        scanner._connected = True  # Set connected state manually

        # Mock time.sleep to speed up test and time.time to control loop
        mocker.patch("time.sleep")
        start_time = 1000.0
        # Provide enough time values for the loop to run multiple times
        time_values = [start_time]  # Initial check
        # Add values for first loop iteration
        time_values.extend(
            [start_time + 1] * 10
        )  # Multiple calls during first iteration
        # Add values for second loop iteration
        time_values.extend(
            [start_time + 31] * 10
        )  # Multiple calls during second iteration
        # Add final value to end loop
        time_values.append(start_time + 61)

        mocker.patch("time.time", side_effect=time_values)

        results = scanner.track_opening_range(
            gap_stocks, duration_seconds=60, poll_interval=30
        )

        assert len(results) == 1
        assert results[0].ticker == "BHP"
        assert results[0].gap_holding is False  # Gap failed to hold

    def test_filter_breakouts_success(self, mocker):
        """Test successful breakout filtering"""
        from skim.scanners.ibkr_gap_scanner import (
            IBKRGapScanner,
            OpeningRangeData,
        )

        scanner = IBKRGapScanner()

        # Mock opening range data
        or_data = [
            OpeningRangeData(
                ticker="BHP",
                conid=8644,
                or_high=47.80,
                or_low=47.50,
                open_price=47.00,
                prev_close=45.20,
                current_price=48.00,  # Above OR high
                gap_holding=True,
            ),
            OpeningRangeData(
                ticker="RIO",
                conid=8653,
                or_high=125.50,
                or_low=124.80,
                open_price=125.00,
                prev_close=120.50,
                current_price=125.20,  # Below OR high
                gap_holding=True,
            ),
        ]

        with patch("skim.scanners.ibkr_gap_scanner.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2025, 11, 9, 10, 30, 0)

            results = scanner.filter_breakouts(or_data)

            assert len(results) == 1
            assert results[0].ticker == "BHP"
            assert results[0].conid == 8644
            assert results[0].entry_signal == "ORB_HIGH_BREAKOUT"
            assert results[0].timestamp == datetime(2025, 11, 9, 10, 30, 0)

    def test_filter_breakouts_no_gap_holding(self, mocker):
        """Test breakout filtering excludes stocks not holding gap"""
        from skim.scanners.ibkr_gap_scanner import (
            IBKRGapScanner,
            OpeningRangeData,
        )

        scanner = IBKRGapScanner()

        or_data = [
            OpeningRangeData(
                ticker="BHP",
                conid=8644,
                or_high=47.80,
                or_low=47.50,
                open_price=47.00,
                prev_close=45.20,
                current_price=48.00,
                gap_holding=False,  # Gap not holding
            ),
        ]

        results = scanner.filter_breakouts(or_data)

        assert len(results) == 0

    def test_filter_breakouts_no_orh_breakout(self, mocker):
        """Test breakout filtering excludes stocks not breaking ORH"""
        from skim.scanners.ibkr_gap_scanner import (
            IBKRGapScanner,
            OpeningRangeData,
        )

        scanner = IBKRGapScanner()

        or_data = [
            OpeningRangeData(
                ticker="BHP",
                conid=8644,
                or_high=47.80,
                or_low=47.50,
                open_price=47.00,
                prev_close=45.20,
                current_price=47.60,  # Below OR high
                gap_holding=True,
            ),
        ]

        results = scanner.filter_breakouts(or_data)

        assert len(results) == 0

    def test_data_models_creation(self):
        """Test creation of data model objects"""
        from skim.scanners.ibkr_gap_scanner import (
            BreakoutSignal,
            GapStock,
            OpeningRangeData,
        )

        # Test GapStock
        gap_stock = GapStock(
            ticker="BHP",
            gap_percent=5.5,
            conid=8644,
        )
        assert gap_stock.ticker == "BHP"
        assert gap_stock.gap_percent == 5.5
        assert gap_stock.conid == 8644

        # Test OpeningRangeData
        or_data = OpeningRangeData(
            ticker="BHP",
            conid=8644,
            or_high=47.80,
            or_low=47.50,
            open_price=47.00,
            prev_close=45.20,
            current_price=48.00,
            gap_holding=True,
        )
        assert or_data.ticker == "BHP"
        assert or_data.gap_holding is True

        # Test BreakoutSignal
        signal = BreakoutSignal(
            ticker="BHP",
            conid=8644,
            gap_pct=5.5,
            or_high=47.80,
            or_low=47.50,
            or_size_pct=0.63,
            current_price=48.00,
            entry_signal="ORB_HIGH_BREAKOUT",
            timestamp=datetime(2025, 11, 9, 10, 30, 0),
        )
        assert signal.ticker == "BHP"
        assert signal.entry_signal == "ORB_HIGH_BREAKOUT"

    def test_create_gap_scan_params(self):
        """Test that gap scan parameters include required type field"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner = IBKRGapScanner()
        params = scanner._create_gap_scan_params(min_gap=3.0)

        # Verify required parameters are present
        assert "instrument" in params
        assert "type" in params
        assert "location" in params
        assert "filter" in params

        # Verify parameter values
        assert params["instrument"] == "STOCK.HK"
        assert params["type"] == "HIGH_OPEN_GAP"
        assert params["location"] == "STK.HK.ASX"

        # Verify filter structure
        assert isinstance(params["filter"], list)
        assert len(params["filter"]) == 2

        # Verify price filter
        price_filter = next(f for f in params["filter"] if f["code"] == "price")
        assert price_filter["value"] == 0.05

        # Verify volume filter
        volume_filter = next(
            f for f in params["filter"] if f["code"] == "volume"
        )
        assert volume_filter["value"] == 10000

    def test_scan_for_gaps_not_connected(self, mocker):
        """Test scan for gaps when scanner is not connected"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner = IBKRGapScanner()
        scanner._connected = False  # Ensure not connected

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 0

    def test_scan_for_gaps_missing_symbol_conid(self, mocker):
        """Test scan for gaps with missing symbol or conid in results"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        # Mock scanner results with missing data
        mock_scanner_results = [
            {
                "symbol": None,
                "conid": "8644",
                "change_percent": 5.5,
            },  # Missing symbol
            {
                "symbol": "BHP",
                "conid": None,
                "change_percent": 4.2,
            },  # Missing conid
            {"symbol": "RIO", "conid": "8653", "change_percent": 6.0},  # Valid
        ]

        mock_client.run_scanner.return_value = mock_scanner_results

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()
        scanner._connected = True

        results = scanner.scan_for_gaps(min_gap=3.0)

        # Should only include valid result (RIO)
        assert len(results) == 1
        assert results[0].ticker == "RIO"

    def test_scan_for_gaps_validation_error(self, mocker):
        """Test scan for gaps with validation error"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        # Mock scanner results that will cause validation error
        mock_scanner_results = [
            {
                "symbol": "",
                "conid": "8644",
                "change_percent": 5.5,
            },  # Empty symbol
        ]

        mock_client.run_scanner.return_value = mock_scanner_results

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()
        scanner._connected = True

        results = scanner.scan_for_gaps(min_gap=3.0)

        # Should handle validation error gracefully
        assert len(results) == 0

    def test_scan_for_gaps_invalid_result_format(self, mocker):
        """Test scan for gaps with invalid result format"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        # Mock scanner results with invalid format
        mock_scanner_results = [
            {"invalid": "data"},  # Missing required fields
            {"symbol": "BHP", "conid": "8644"},  # Missing change_percent
        ]

        mock_client.run_scanner.return_value = mock_scanner_results

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()
        scanner._connected = True

        results = scanner.scan_for_gaps(min_gap=3.0)

        # Should handle invalid format gracefully
        assert len(results) == 0

    def test_scan_for_gaps_below_minimum_gap(self, mocker):
        """Test scan for gaps filters out results below minimum gap"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        # Mock scanner results with gaps below minimum
        mock_scanner_results = [
            {
                "symbol": "BHP",
                "conid": "8644",
                "change_percent": 2.0,
            },  # Below 3.0%
            {
                "symbol": "RIO",
                "conid": "8653",
                "change_percent": 4.5,
            },  # Above 3.0%
        ]

        mock_client.run_scanner.return_value = mock_scanner_results

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()
        scanner._connected = True

        results = scanner.scan_for_gaps(min_gap=3.0)

        # Should only include RIO (above minimum)
        assert len(results) == 1
        assert results[0].ticker == "RIO"

    def test_scan_for_gaps_exception_handling(self, mocker):
        """Test scan for gaps handles exceptions gracefully"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()
        mock_client.run_scanner.side_effect = Exception("Scanner error")

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()
        scanner._connected = True

        results = scanner.scan_for_gaps(min_gap=3.0)

        # Should handle exception and return empty list
        assert len(results) == 0

    def test_track_opening_range_not_connected(self, mocker):
        """Test opening range tracking when scanner is not connected"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner
        from skim.validation.scanners import GapStock

        scanner = IBKRGapScanner()
        scanner._connected = False

        gap_stocks = [
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                conid=8644,
            )
        ]

        results = scanner.track_opening_range(gap_stocks)

        assert len(results) == 0

    def test_track_opening_range_no_candidates(self, mocker):
        """Test opening range tracking with no candidates"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner = IBKRGapScanner()
        scanner._connected = True

        results = scanner.track_opening_range([])

        assert len(results) == 0

    def test_track_opening_range_validation_error(self, mocker):
        """Test opening range tracking handles validation errors"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner
        from skim.validation.scanners import GapStock

        gap_stocks = [
            GapStock(
                ticker="BHP",
                gap_percent=5.5,
                conid=8644,
            )
        ]

        # Mock market data
        mock_market_data = Mock()
        mock_market_data.last_price = 47.80

        mock_client = Mock()
        mock_client.get_market_data.return_value = mock_market_data
        mock_client.is_connected.return_value = True

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()
        scanner._connected = True

        # Mock time to control loop duration
        mocker.patch("time.sleep")
        start_time = 1000.0
        mocker.patch("time.time", side_effect=[start_time, start_time + 61])

        # Mock OpeningRangeData creation to raise validation error
        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.OpeningRangeData",
            side_effect=Exception("Validation error"),
        )
        results = scanner.track_opening_range(gap_stocks, duration_seconds=60)

        # Should handle validation error and skip invalid data
        assert len(results) == 0

    def test_filter_breakouts_empty_data(self, mocker):
        """Test filter breakouts with empty opening range data"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner = IBKRGapScanner()

        results = scanner.filter_breakouts([])

        assert len(results) == 0

    def test_filter_breakouts_validation_error(self, mocker):
        """Test filter breakouts handles validation errors"""
        from skim.scanners.ibkr_gap_scanner import (
            IBKRGapScanner,
            OpeningRangeData,
        )

        scanner = IBKRGapScanner()

        or_data = [
            OpeningRangeData(
                ticker="BHP",
                conid=8644,
                or_high=47.80,
                or_low=47.50,
                open_price=47.00,
                prev_close=45.20,
                current_price=48.00,
                gap_holding=True,
            ),
        ]

        # Mock BreakoutSignal creation to raise validation error
        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.BreakoutSignal",
            side_effect=Exception("Validation error"),
        )
        results = scanner.filter_breakouts(or_data)

        # Should handle validation error and skip invalid data
        assert len(results) == 0

    def test_connect_success(self, mocker):
        """Test successful connection to IBKR"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()

        scanner.connect()

        assert scanner._connected is True
        mock_client.connect.assert_called_once()

    def test_connect_failure(self, mocker):
        """Test connection failure to IBKR"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()
        mock_client.connect.side_effect = Exception("Connection failed")

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()

        with pytest.raises(
            ConnectionError, match="Failed to connect IBKR gap scanner"
        ):
            scanner.connect()

        assert scanner._connected is False

    def test_disconnect_success(self, mocker):
        """Test successful disconnection from IBKR"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()
        scanner._connected = True

        scanner.disconnect()

        assert scanner._connected is False
        mock_client.disconnect.assert_called_once()

    def test_is_connected(self, mocker):
        """Test is_connected method"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        mock_client = Mock()

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        scanner = IBKRGapScanner()

        # Test when not connected
        scanner._connected = False
        mock_client.is_connected.return_value = False
        assert scanner.is_connected() is False

        # Test when scanner connected but client not
        scanner._connected = True
        mock_client.is_connected.return_value = False
        assert scanner.is_connected() is False

        # Test when both connected
        scanner._connected = True
        mock_client.is_connected.return_value = True
        assert scanner.is_connected() is True
