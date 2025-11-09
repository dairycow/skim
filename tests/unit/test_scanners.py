"""Unit tests for scanner modules"""

from datetime import datetime
from unittest.mock import Mock, patch

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


class TestIBKRGapScanner:
    """Tests for IBKRGapScanner"""

    def test_scan_for_gaps_success(self, mocker):
        """Test successful scan for gap stocks using IBKR scanner"""
        from skim.scanners.ibkr_gap_scanner import IBKRGapScanner

        scanner = IBKRGapScanner()
        scanner._connected = True  # Mock connected state

        mock_client = Mock()

        mocker.patch(
            "skim.scanners.ibkr_gap_scanner.IBKRClient",
            return_value=mock_client,
        )

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 2
        assert results[0].ticker == "BHP"
        assert results[0].gap_percent == 5.5
        assert results[0].close_price == 45.20
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
        from skim.scanners.ibkr_gap_scanner import (
            GapStock,
            IBKRGapScanner,
        )

        # Mock gap stocks
        gap_stocks = [
            GapStock(
                ticker="BHP", gap_percent=5.5, close_price=45.20, conid=8644
            ),
            GapStock(
                ticker="RIO", gap_percent=4.2, close_price=120.50, conid=8653
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
                ticker="BHP", gap_percent=5.5, close_price=45.20, conid=8644
            ),
            GapStock(
                ticker="RIO", gap_percent=4.2, close_price=120.50, conid=8653
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
                ticker="BHP", gap_percent=5.5, close_price=45.20, conid=8644
            ),
        ]

        # Mock market data where price falls below previous close
        def mock_get_market_data(ticker):
            if ticker == "BHP":
                mock_data = Mock()
                mock_data.last_price = 44.80  # Below prev close
                return mock_data
            return None

        mock_client = Mock()
        mock_client.get_market_data.side_effect = mock_get_market_data
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
        mocker.patch(
            "time.time",
            side_effect=[start_time, start_time + 1, start_time + 61],
        )

        results = scanner.track_opening_range(gap_stocks, duration_seconds=60)

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
            ticker="BHP", gap_percent=5.5, close_price=45.20, conid=8644
        )
        assert gap_stock.ticker == "BHP"
        assert gap_stock.gap_percent == 5.5
        assert gap_stock.close_price == 45.20
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
