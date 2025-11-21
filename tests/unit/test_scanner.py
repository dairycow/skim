"""Unit tests for scanner module - TDD RED phase"""

from datetime import datetime

import pytest

from skim.scanner import Scanner


@pytest.fixture
def scanner(mocker):
    """Create a Scanner instance with mocked IBKR and ASX clients"""
    # Mock the clients before creating the scanner
    mock_ib_client = mocker.Mock()
    mock_gap_scanner = mocker.Mock()
    mock_asx_scanner = mocker.Mock()

    # Patch the imports
    mocker.patch("skim.scanner.IBKRClient", return_value=mock_ib_client)
    mocker.patch("skim.scanner.IBKRGapScanner", return_value=mock_gap_scanner)
    mocker.patch(
        "skim.scanner.ASXAnnouncementScanner", return_value=mock_asx_scanner
    )

    # Create scanner - it will use the mocked clients
    scanner = Scanner(
        paper_trading=True,
        gap_threshold=3.0,
    )

    # Return the scanner with mocked clients accessible
    scanner.ib_client = mock_ib_client
    scanner.gap_scanner = mock_gap_scanner
    scanner.asx_scanner = mock_asx_scanner

    return scanner


class TestScannerFindCandidates:
    """Test finding candidates with gap + announcement"""

    def test_find_candidates_returns_list(self, scanner):
        """Should return list of candidates"""
        scanner.gap_scanner.scan_for_gaps.return_value = []
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = set()

        result = scanner.find_candidates()

        assert isinstance(result, list)

    def test_find_candidates_filters_by_gap_threshold(self, scanner, mocker):
        """Should only include stocks with gap >= threshold"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        # Mock gap scanner to return stocks
        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=5.0, conid=1),  # >= 3.0
            GapStock(ticker="RIO", gap_percent=2.0, conid=2),  # < 3.0
        ]

        # Mock ASX announcements to return both tickers
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = {
            "BHP",
            "RIO",
        }

        # Mock market data
        market_data_bhp = mocker.Mock()
        market_data_bhp.high = 50.0
        market_data_bhp.low = 48.0
        market_data_bhp.open = 49.0

        market_data_rio = mocker.Mock()
        market_data_rio.high = 120.0
        market_data_rio.low = 118.0
        market_data_rio.open = 119.0

        scanner.gap_scanner.get_market_data.side_effect = [
            market_data_bhp,
            market_data_rio,
        ]

        result = scanner.find_candidates()

        # Should only include BHP (gap 5.0 >= 3.0)
        assert len(result) == 1
        assert result[0].ticker == "BHP"

    def test_find_candidates_filters_by_announcement(self, scanner, mocker):
        """Should only include stocks with price-sensitive announcements"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=5.0, conid=1),
            GapStock(ticker="RIO", gap_percent=4.0, conid=2),
        ]

        # ASX only returns BHP with announcement
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = {"BHP"}

        # Mock market data
        market_data = mocker.Mock()
        market_data.high = 50.0
        market_data.low = 48.0
        market_data.open = 49.0
        scanner.gap_scanner.get_market_data.return_value = market_data

        result = scanner.find_candidates()

        # Should only include BHP (has announcement)
        assert len(result) == 1
        assert result[0].ticker == "BHP"

    def test_find_candidates_sets_or_high_and_low(self, scanner, mocker):
        """Candidate should have or_high and or_low set"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=5.0, conid=1),
        ]
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = {"BHP"}

        market_data = mocker.Mock()
        market_data.high = 50.0
        market_data.low = 48.0
        market_data.open = 49.0
        scanner.gap_scanner.get_market_data.return_value = market_data

        result = scanner.find_candidates()

        assert result[0].or_high == 50.0
        assert result[0].or_low == 48.0

    def test_find_candidates_has_correct_status(self, scanner, mocker):
        """Candidate status should be 'watching'"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=5.0, conid=1),
        ]
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = {"BHP"}

        market_data = mocker.Mock()
        market_data.high = 50.0
        market_data.low = 48.0
        market_data.open = 49.0
        scanner.gap_scanner.get_market_data.return_value = market_data

        result = scanner.find_candidates()

        assert result[0].status == "watching"

    def test_find_candidates_has_scan_date(self, scanner, mocker):
        """Candidate should have scan_date set"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=5.0, conid=1),
        ]
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = {"BHP"}

        market_data = mocker.Mock()
        market_data.high = 50.0
        market_data.low = 48.0
        market_data.open = 49.0
        scanner.gap_scanner.get_market_data.return_value = market_data

        result = scanner.find_candidates()

        assert result[0].scan_date  # Should have a value
        # Should be parseable as ISO datetime
        datetime.fromisoformat(result[0].scan_date)

    def test_find_candidates_returns_empty_when_no_gaps(self, scanner):
        """Should return empty list when no gaps found"""
        scanner.gap_scanner.scan_for_gaps.return_value = []
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = set()

        result = scanner.find_candidates()

        assert result == []

    def test_find_candidates_returns_empty_when_no_announcements(
        self, scanner, mocker
    ):
        """Should return empty list when no price-sensitive announcements"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=5.0, conid=1),
        ]
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = set()

        result = scanner.find_candidates()

        assert result == []


class TestScannerEdgeCases:
    """Test edge cases and error handling"""

    def test_find_candidates_handles_missing_market_data(self, scanner, mocker):
        """Should skip candidates if market data unavailable"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=5.0, conid=1),
        ]
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = {"BHP"}

        # Market data request fails
        scanner.gap_scanner.get_market_data.side_effect = Exception(
            "Market data unavailable"
        )

        result = scanner.find_candidates()

        # Should skip the candidate
        assert result == []

    def test_find_candidates_handles_negative_gap(self, scanner, mocker):
        """Should skip stocks with negative gap"""
        from skim.scanners.ibkr_gap_scanner import GapStock

        scanner.gap_scanner.scan_for_gaps.return_value = [
            GapStock(ticker="BHP", gap_percent=-2.0, conid=1),
        ]
        scanner.asx_scanner.fetch_price_sensitive_tickers.return_value = {"BHP"}

        result = scanner.find_candidates()

        assert result == []
