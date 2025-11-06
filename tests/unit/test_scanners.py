"""Unit tests for scanner modules"""

from unittest.mock import Mock

import pytest
import requests

from skim.scanners.asx_announcements import ASXAnnouncementScanner
from skim.scanners.tradingview import GapStock, TradingViewScanner


class TestTradingViewScanner:
    """Tests for TradingViewScanner"""

    def test_scan_for_gaps_success(self, mocker):
        """Test successful scan for gap stocks"""
        scanner = TradingViewScanner()

        # Mock response data
        mock_response_data = {
            "data": [
                {
                    "s": "ASX:BHP",
                    "d": ["BHP Billiton Limited", 45.20, 5.5],
                },
                {
                    "s": "ASX:RIO",
                    "d": ["Rio Tinto Limited", 120.50, 4.2],
                },
                {
                    "s": "ASX:FMG",
                    "d": ["Fortescue Metals Group", 18.75, 3.8],
                },
            ]
        }

        # Mock the requests.post call
        mock_response = Mock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.post", return_value=mock_response)

        # Execute
        results = scanner.scan_for_gaps(min_gap=3.0)

        # Assert
        assert len(results) == 3
        assert results[0].ticker == "BHP"
        assert results[0].gap_percent == 5.5
        assert results[0].close_price == 45.20
        assert results[1].ticker == "RIO"
        assert results[2].ticker == "FMG"

    def test_scan_for_gaps_empty_response(self, mocker):
        """Test scan with empty response"""
        scanner = TradingViewScanner()

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()

        mocker.patch("requests.post", return_value=mock_response)

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 0

    def test_scan_for_gaps_network_error(self, mocker):
        """Test scan with network error"""
        scanner = TradingViewScanner()

        mocker.patch(
            "requests.post",
            side_effect=requests.exceptions.ConnectionError("Network error"),
        )

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 0

    def test_scan_for_gaps_timeout(self, mocker):
        """Test scan with timeout"""
        scanner = TradingViewScanner()

        mocker.patch(
            "requests.post", side_effect=requests.exceptions.Timeout("Timeout")
        )

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 0

    def test_scan_for_gaps_http_error(self, mocker):
        """Test scan with HTTP error"""
        scanner = TradingViewScanner()

        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "500 Server Error"
        )

        mocker.patch("requests.post", return_value=mock_response)

        results = scanner.scan_for_gaps(min_gap=3.0)

        assert len(results) == 0

    def test_build_payload(self):
        """Test payload construction"""
        scanner = TradingViewScanner()
        payload = scanner._build_payload(min_gap=5.0)

        assert payload["markets"] == ["australia"]
        assert payload["columns"] == ["name", "close", "change_from_open"]
        assert payload["sort"]["sortBy"] == "change_from_open"
        assert payload["filter"][0]["left"] == "change_from_open"
        assert payload["filter"][0]["operation"] == "greater"
        assert payload["filter"][0]["right"] == 5.0

    def test_build_headers(self):
        """Test headers construction"""
        scanner = TradingViewScanner()
        headers = scanner._build_headers()

        assert headers["content-type"] == "application/json"
        assert "Mozilla" in headers["user-agent"]
        assert headers["origin"] == "https://www.tradingview.com"

    def test_parse_response_with_missing_data(self):
        """Test parsing response with incomplete data"""
        scanner = TradingViewScanner()

        # Response with missing fields
        data = {
            "data": [
                {"s": "ASX:BHP", "d": [45.20]},  # Missing gap_percent
                {"s": "ASX:RIO", "d": None},  # No data array
                {"s": "ASX:FMG"},  # Missing 'd' field
            ]
        }

        results = scanner._parse_response(data)

        # Should only parse valid entries
        assert len(results) == 0

    def test_parse_response_with_null_values(self):
        """Test parsing response with null values"""
        scanner = TradingViewScanner()

        data = {
            "data": [
                {"s": "ASX:BHP", "d": ["BHP", None, 5.5]},  # Null close price
                {"s": "ASX:RIO", "d": ["RIO", 120.50, None]},  # Null gap
            ]
        }

        results = scanner._parse_response(data)

        # Should handle nulls gracefully
        assert len(results) == 2
        assert results[0].close_price == 0.0
        assert results[1].gap_percent == 0.0

    def test_gap_stock_named_tuple(self):
        """Test GapStock named tuple creation"""
        gap_stock = GapStock(ticker="BHP", gap_percent=5.5, close_price=45.20)

        assert gap_stock.ticker == "BHP"
        assert gap_stock.gap_percent == 5.5
        assert gap_stock.close_price == 45.20

        # Test immutability
        with pytest.raises(AttributeError):
            gap_stock.ticker = "RIO"


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
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "404 Not Found"
        )

        mocker.patch("requests.get", return_value=mock_response)

        results = scanner.fetch_price_sensitive_tickers()

        assert len(results) == 0

    def test_fetch_price_sensitive_announcements_malformed_html(self, mocker):
        """Test fetch with malformed HTML"""
        scanner = ASXAnnouncementScanner()

        mock_html = "<html><body><table><tr class='pricesens'></table></body></html>"

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
