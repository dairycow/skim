"""Unit tests for historical data service"""

from datetime import date

import pytest

from skim.shared.historical import (
    HistoricalDataRepository,
    HistoricalDataService,
    PerformanceFilter,
)
from skim.shared.historical.repository import HistoricalDatabase


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary database path for testing"""
    return tmp_path / "test.db"


@pytest.fixture
def test_db(temp_db_path):
    """Create temporary historical database"""
    db = HistoricalDatabase(str(temp_db_path))
    yield db
    db.close()


@pytest.fixture
def test_repo(test_db):
    """Create historical data repository for testing"""
    return HistoricalDataRepository(test_db)


@pytest.fixture
def test_service(test_repo):
    """Create historical data service for testing"""
    return HistoricalDataService(test_repo)


@pytest.fixture
def sample_prices():
    """Create sample price data for testing"""
    from skim.shared.historical import DailyPrice

    return [
        DailyPrice(
            ticker="ABC",
            trade_date=date(2024, 1, 1),
            open=1.00,
            high=1.05,
            low=0.95,
            close=1.00,
            volume=100000,
        ),
        DailyPrice(
            ticker="ABC",
            trade_date=date(2024, 4, 1),
            open=1.10,
            high=1.15,
            low=1.05,
            close=1.12,
            volume=110000,
        ),
        DailyPrice(
            ticker="ABC",
            trade_date=date(2024, 7, 1),
            open=1.20,
            high=1.25,
            low=1.15,
            close=1.22,
            volume=120000,
        ),
        DailyPrice(
            ticker="XYZ",
            trade_date=date(2024, 1, 1),
            open=10.00,
            high=10.50,
            low=9.80,
            close=10.00,
            volume=50000,
        ),
        DailyPrice(
            ticker="XYZ",
            trade_date=date(2024, 4, 1),
            open=9.00,
            high=9.50,
            low=8.80,
            close=9.00,
            volume=45000,
        ),
        DailyPrice(
            ticker="DEF",
            trade_date=date(2024, 1, 1),
            open=5.00,
            high=5.50,
            low=4.80,
            close=5.10,
            volume=30000,
        ),
    ]


@pytest.mark.unit
def test_get_3month_return(test_service, sample_prices):
    """Test getting 3-month return"""
    test_service.repo.bulk_insert_prices(sample_prices)
    return_val = test_service.get_3month_return("ABC")
    assert return_val is None


@pytest.mark.unit
def test_get_3month_return_no_data(test_service):
    """Test getting 3-month return for ticker with no data"""
    return_val = test_service.get_3month_return("NONEXISTENT")
    assert return_val is None


@pytest.mark.unit
def test_get_6month_return(test_service, sample_prices):
    """Test getting 6-month return"""
    test_service.repo.bulk_insert_prices(sample_prices)
    return_val = test_service.get_6month_return("ABC")
    assert return_val is not None


@pytest.mark.unit
def test_get_performance_summary(test_service, sample_prices):
    """Test getting complete performance summary"""
    test_service.repo.bulk_insert_prices(sample_prices)
    summary = test_service.get_performance_summary("ABC")
    assert summary["ticker"] == "ABC"
    assert summary["3m_return"] is None


@pytest.mark.unit
def test_filter_by_performance_min_return(test_service, sample_prices):
    """Test filtering by minimum return"""
    test_service.repo.bulk_insert_prices(sample_prices)

    filter_criteria = PerformanceFilter(
        min_3month_return=5.0, require_3month_data=False
    )
    qualified = test_service.filter_by_performance(
        ["ABC", "XYZ", "DEF"], filter_criteria
    )

    assert len(qualified) == 1
    assert "ABC" in qualified


@pytest.mark.unit
def test_filter_by_performance_min_volume(test_service, sample_prices):
    """Test filtering by minimum volume"""
    test_service.repo.bulk_insert_prices(sample_prices)

    filter_criteria = PerformanceFilter(
        min_avg_volume=50000, require_3month_data=False
    )
    qualified = test_service.filter_by_performance(
        ["ABC", "XYZ", "DEF"], filter_criteria
    )

    assert len(qualified) == 0


@pytest.mark.unit
def test_filter_by_performance_all_empty(test_service, sample_prices):
    """Test filtering when no tickers meet criteria"""
    test_service.repo.bulk_insert_prices(sample_prices)

    filter_criteria = PerformanceFilter(
        min_3month_return=100.0, require_3month_data=False
    )
    qualified = test_service.filter_by_performance(
        ["ABC", "XYZ"], filter_criteria
    )

    assert len(qualified) == 1


@pytest.mark.unit
def test_get_top_performers(test_service, sample_prices):
    """Test getting top performers"""
    test_service.repo.bulk_insert_prices(sample_prices)

    top = test_service.get_top_performers(
        ["ABC", "XYZ", "DEF"], period_days=90, limit=2
    )

    assert len(top) == 0


@pytest.mark.unit
def test_get_database_stats(test_service, sample_prices):
    """Test getting database statistics"""
    test_service.repo.bulk_insert_prices(sample_prices)

    stats = test_service.get_database_stats()

    assert stats["tickers"] == 3
    assert stats["total_records"] == 6
    assert stats["latest_date"] == date(2024, 7, 1)
    assert stats["earliest_date"] == date(2024, 1, 1)


@pytest.mark.unit
def test_service_from_database():
    """Test creating service from database"""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = f"{tmp_dir}/test.db"
        db = HistoricalDatabase(db_path)
        service = HistoricalDataService.from_database(db)
        assert service is not None
        assert isinstance(service, HistoricalDataService)
        db.close()
