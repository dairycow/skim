"""Tests for decoupled IBKRGapScanner (no database dependencies)

Tests verify that scanner returns structured data without accessing database.
The bot.py layer handles all database persistence.
"""

from unittest.mock import MagicMock

import pytest

from skim.brokers.ib_interface import MarketData
from skim.scanners.ibkr_gap_scanner import GapStock, IBKRGapScanner
from skim.validation.scanners import (
    GapScanResult,
    MonitoringResult,
    ORTrackingResult,
)


@pytest.fixture
def scanner_with_mocked_client(mocker):
    """Real IBKRGapScanner with mocked IBKR client"""
    scanner = IBKRGapScanner(paper_trading=True)
    # Mock the internal IBKR client to avoid real API calls
    scanner.client = mocker.MagicMock()
    scanner._connected = True
    return scanner


@pytest.mark.unit
class TestDecoupledGapScannerGapScanWithAnnouncements:
    """Tests for scan_gaps_with_announcements - no database coupling"""

    def test_returns_gap_scan_result(self, scanner_with_mocked_client):
        """Verify method returns GapScanResult dataclass"""
        scanner_with_mocked_client.scan_for_gaps = MagicMock(return_value=[])

        result = scanner_with_mocked_client.scan_gaps_with_announcements(
            price_sensitive_tickers={"BHP"}
        )

        assert isinstance(result, GapScanResult)
        assert isinstance(result.gap_stocks, list)
        assert isinstance(result.new_candidates, list)

    def test_no_db_parameter(self, scanner_with_mocked_client):
        """Verify method signature has no db parameter"""
        import inspect

        sig = inspect.signature(
            scanner_with_mocked_client.scan_gaps_with_announcements
        )

        params = list(sig.parameters.keys())
        assert "db" not in params
        assert "price_sensitive_tickers" in params

    def test_returns_candidate_data_for_persistence(
        self, scanner_with_mocked_client
    ):
        """Verify candidates returned contain fields needed for database persistence"""
        gap_stock = GapStock(conid=265598, gap_percent=5.5, ticker="BHP")
        scanner_with_mocked_client.scan_for_gaps = MagicMock(
            return_value=[gap_stock]
        )
        scanner_with_mocked_client.get_market_data = MagicMock(
            return_value=MarketData(
                ticker="BHP",
                conid="265598",
                last_price=50.0,
                high=51.0,
                low=49.0,
                bid=49.95,
                ask=50.05,
                bid_size=100,
                ask_size=200,
                volume=1000,
                open=49.5,
                prior_close=48.0,
                change_percent=4.17,
            )
        )

        result = scanner_with_mocked_client.scan_gaps_with_announcements(
            price_sensitive_tickers={"BHP"}
        )

        assert len(result.new_candidates) == 1
        candidate = result.new_candidates[0]

        # Verify it has fields needed for Candidate model
        assert candidate["ticker"] == gap_stock.ticker
        assert candidate["headline"] is not None
        assert candidate["gap_percent"] == 5.5
        assert candidate["price"] == 50.0
        assert candidate["status"] == "watching"
        assert candidate["scan_date"] is not None


@pytest.mark.unit
class TestDecoupledScannerMonitoringResult:
    """Tests for scan_and_monitor_gaps - no database coupling"""

    def test_returns_monitoring_result(self, scanner_with_mocked_client):
        """Verify method returns MonitoringResult dataclass"""
        scanner_with_mocked_client.scan_for_gaps = MagicMock(return_value=[])

        result = scanner_with_mocked_client.scan_and_monitor_gaps(
            existing_candidates=[]
        )

        assert isinstance(result, MonitoringResult)
        assert isinstance(result.gap_stocks, list)
        assert isinstance(result.triggered_candidates, list)

    def test_no_db_parameter(self, scanner_with_mocked_client):
        """Verify method signature has no db parameter"""
        import inspect

        sig = inspect.signature(
            scanner_with_mocked_client.scan_and_monitor_gaps
        )

        params = list(sig.parameters.keys())
        assert "db" not in params
        assert "existing_candidates" in params

    def test_distinguishes_existing_vs_new_triggered(
        self, scanner_with_mocked_client
    ):
        """Verify triggered candidates indicate if they're existing or new"""
        from skim.data.models import Candidate

        existing_candidate = Candidate(
            ticker="BHP",
            headline="Gap detected",
            scan_date="2025-11-20T10:00:00",
            status="watching",
            gap_percent=5.0,
            prev_close=50.0,
        )

        gap_stock = GapStock(conid=1, gap_percent=5.5, ticker="BHP")
        scanner_with_mocked_client.scan_for_gaps = MagicMock(
            return_value=[gap_stock]
        )
        scanner_with_mocked_client.get_market_data = MagicMock(
            return_value=MarketData(
                ticker="BHP",
                conid="BHP",
                last_price=52.0,
                high=53.0,
                low=51.0,
                bid=51.95,
                ask=52.05,
                bid_size=100,
                ask_size=200,
                volume=1000,
                open=51.0,
                prior_close=50.0,
                change_percent=4.0,
            )
        )

        result = scanner_with_mocked_client.scan_and_monitor_gaps(
            existing_candidates=[existing_candidate]
        )

        assert len(result.triggered_candidates) == 1
        triggered = result.triggered_candidates[0]
        assert triggered["is_existing"] is True
        assert triggered["status"] == "triggered"


@pytest.mark.unit
class TestDecoupledScannerORTrackingResult:
    """Tests for scan_for_or_tracking - no database coupling"""

    def test_returns_or_tracking_result(self, scanner_with_mocked_client):
        """Verify method returns ORTrackingResult dataclass"""
        scanner_with_mocked_client.scan_for_gaps = MagicMock(return_value=[])

        result = scanner_with_mocked_client.scan_for_or_tracking()

        assert isinstance(result, ORTrackingResult)
        assert isinstance(result.gap_stocks, list)
        assert isinstance(result.or_tracking_candidates, list)

    def test_no_db_parameter(self, scanner_with_mocked_client):
        """Verify method signature has no db parameter"""
        import inspect

        sig = inspect.signature(scanner_with_mocked_client.scan_for_or_tracking)

        params = list(sig.parameters.keys())
        assert "db" not in params

    def test_returns_candidate_data_with_or_fields(
        self, scanner_with_mocked_client
    ):
        """Verify candidates have fields needed for OR tracking persistence"""
        gap_stock = GapStock(conid=265598, gap_percent=5.5, ticker="BHP")
        scanner_with_mocked_client.scan_for_gaps = MagicMock(
            return_value=[gap_stock]
        )
        scanner_with_mocked_client.get_market_data = MagicMock(
            return_value=MarketData(
                ticker="BHP",
                conid="265598",
                last_price=50.0,
                high=51.0,
                low=49.0,
                bid=49.95,
                ask=50.05,
                bid_size=100,
                ask_size=200,
                volume=1000,
                open=49.5,
                prior_close=48.0,
                change_percent=4.17,
            )
        )

        result = scanner_with_mocked_client.scan_for_or_tracking()

        assert len(result.or_tracking_candidates) == 1
        candidate = result.or_tracking_candidates[0]

        # Verify OR tracking specific fields
        assert candidate["status"] == "or_tracking"
        assert candidate["conid"] == 265598
        assert candidate["source"] == "ibkr"
        assert candidate["gap_percent"] == 5.5
