"""Unit tests for historical data repository"""

from datetime import date

import pytest

from skim.infrastructure.database.historical import (
    DailyPrice,
    HistoricalDataRepository,
)
from skim.infrastructure.database.historical.repository import (
    HistoricalDatabase,
)


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
def sample_prices():
    """Create sample price data for testing"""
    return [
        DailyPrice(
            ticker="ABC",
            trade_date=date(2024, 1, 1),
            open=1.00,
            high=1.05,
            low=0.95,
            close=1.02,
            volume=100000,
        ),
        DailyPrice(
            ticker="ABC",
            trade_date=date(2024, 1, 2),
            open=1.02,
            high=1.08,
            low=0.99,
            close=1.05,
            volume=120000,
        ),
        DailyPrice(
            ticker="ABC",
            trade_date=date(2024, 1, 3),
            open=1.05,
            high=1.10,
            low=1.01,
            close=1.08,
            volume=110000,
        ),
        DailyPrice(
            ticker="XYZ",
            trade_date=date(2024, 1, 1),
            open=10.00,
            high=10.50,
            low=9.80,
            close=10.20,
            volume=50000,
        ),
    ]


@pytest.mark.unit
def test_bulk_insert_prices(test_repo, sample_prices):
    """Test bulk insert of price data"""
    count = test_repo.bulk_insert_prices(sample_prices)
    assert count == 4

    assert test_repo.get_total_records() == 4


@pytest.mark.unit
def test_get_latest_date(test_repo, sample_prices):
    """Test getting latest date from database"""
    test_repo.bulk_insert_prices(sample_prices)
    latest = test_repo.get_latest_date()
    assert latest == date(2024, 1, 3)


@pytest.mark.unit
def test_get_earliest_date(test_repo, sample_prices):
    """Test getting earliest date from database"""
    test_repo.bulk_insert_prices(sample_prices)
    earliest = test_repo.get_earliest_date()
    assert earliest == date(2024, 1, 1)


@pytest.mark.unit
def test_get_tickers_with_data(test_repo, sample_prices):
    """Test getting list of tickers"""
    test_repo.bulk_insert_prices(sample_prices)
    tickers = test_repo.get_tickers_with_data()
    assert set(tickers) == {"ABC", "XYZ"}


@pytest.mark.unit
def test_get_price_on_date(test_repo, sample_prices):
    """Test getting price for a specific date"""
    test_repo.bulk_insert_prices(sample_prices)
    price = test_repo.get_price_on_date("ABC", date(2024, 1, 2))
    assert price is not None
    assert price.ticker == "ABC"
    assert price.close == 1.05


@pytest.mark.unit
def test_get_price_on_date_not_found(test_repo, sample_prices):
    """Test getting price for non-existent date"""
    test_repo.bulk_insert_prices(sample_prices)
    price = test_repo.get_price_on_date("ABC", date(2024, 1, 5))
    assert price is None


@pytest.mark.unit
def test_get_prices_in_range(test_repo, sample_prices):
    """Test getting prices within date range"""
    test_repo.bulk_insert_prices(sample_prices)
    prices = test_repo.get_prices_in_range(
        "ABC", date(2024, 1, 1), date(2024, 1, 2)
    )
    assert len(prices) == 2
    assert prices[0].trade_date == date(2024, 1, 1)
    assert prices[1].trade_date == date(2024, 1, 2)


@pytest.mark.unit
def test_get_performance(test_repo, sample_prices):
    """Test calculating performance over period"""
    test_repo.bulk_insert_prices(sample_prices)
    perf = test_repo.get_performance("ABC", 2, date(2024, 1, 3))
    assert perf is not None
    assert perf.ticker == "ABC"
    assert perf.period_days == 2
    assert perf.start_close == 1.02
    assert perf.end_close == 1.08
    assert abs(perf.return_percent - 5.88) < 0.01


@pytest.mark.unit
def test_get_performance_insufficient_data(test_repo, sample_prices):
    """Test performance calculation with insufficient data"""
    test_repo.bulk_insert_prices(sample_prices)
    perf = test_repo.get_performance("XYZ", 10, date(2024, 1, 5))
    assert perf is None


@pytest.mark.unit
def test_get_3month_performance(test_repo, sample_prices):
    """Test getting 3-month performance"""
    test_repo.bulk_insert_prices(sample_prices)
    perf = test_repo.get_3month_performance("ABC", date(2024, 1, 3))
    assert perf is not None
    assert perf.period_days == 90


@pytest.mark.unit
def test_get_6month_performance(test_repo, sample_prices):
    """Test getting 6-month performance"""
    test_repo.bulk_insert_prices(sample_prices)
    perf = test_repo.get_6month_performance("ABC", date(2024, 1, 3))
    assert perf is not None
    assert perf.period_days == 180


@pytest.mark.unit
def test_delete_ticker_data(test_repo, sample_prices):
    """Test deleting all data for a ticker"""
    test_repo.bulk_insert_prices(sample_prices)
    count = test_repo.delete_ticker_data("ABC")
    assert count == 3

    assert test_repo.get_total_records() == 1


@pytest.mark.unit
def test_get_tickers_count(test_repo, sample_prices):
    """Test getting count of unique tickers"""
    test_repo.bulk_insert_prices(sample_prices)
    count = test_repo.get_tickers_count()
    assert count == 2


@pytest.mark.unit
def test_get_total_records(test_repo, sample_prices):
    """Test getting total number of records"""
    test_repo.bulk_insert_prices(sample_prices)
    total = test_repo.get_total_records()
    assert total == 4


@pytest.mark.unit
def test_bulk_insert_update_existing(test_repo, sample_prices):
    """Test bulk insert updates existing records"""
    test_repo.bulk_insert_prices(sample_prices)

    updated_price = DailyPrice(
        ticker="ABC",
        trade_date=date(2024, 1, 1),
        open=2.00,
        high=2.05,
        low=1.95,
        close=2.02,
        volume=200000,
    )

    test_repo.bulk_insert_prices([updated_price])

    assert test_repo.get_total_records() == 4

    price = test_repo.get_price_on_date("ABC", date(2024, 1, 1))
    assert price.open == 2.00
    assert price.close == 2.02
    assert price.volume == 200000
