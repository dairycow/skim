"""Pytest fixtures for unit tests"""

import pytest

from skim.trading.data.database import Database


@pytest.fixture
def test_db():
    """In-memory SQLite database for testing"""
    db = Database(":memory:")
    yield db
    db.close()


@pytest.fixture
def sample_gap_candidate():
    """Sample gap-only candidate for testing"""
    from tests.factories import CandidateFactory

    return CandidateFactory.gap_candidate(
        ticker="RIO",
        gap_percent=4.2,
        conid=8645,
    )


@pytest.fixture
def sample_news_candidate():
    """Sample news-only candidate for testing"""
    from tests.factories import CandidateFactory

    return CandidateFactory.news_candidate(
        ticker="CBA",
        headline="Trading Halt",
    )


@pytest.fixture
def sample_position():
    """Sample open position for testing"""
    from tests.factories import PositionFactory

    return PositionFactory.position(
        ticker="BHP",
        quantity=100,
        entry_price=46.50,
        stop_loss=43.00,
    )


@pytest.fixture
def sample_market_data():
    """Sample market data for testing"""
    from tests.factories import MarketDataFactory

    return MarketDataFactory.market_data(
        ticker="BHP",
        conid="8644",
    )


@pytest.fixture
def mock_bot_config():
    """Create mock configuration for TradingBot tests.

    Returns a Mock object configured with standard trading bot parameters.
    Tests can override specific attributes as needed.

    Returns:
        Mock: Mock config with standard bot parameters
    """
    from unittest.mock import Mock

    from skim.trading.core.config import Config, ScannerConfig

    config = Mock(spec=Config)
    config.scanner_config = ScannerConfig(gap_threshold=3.0)
    config.max_positions = 5
    config.max_position_size = 1000
    config.stop_loss_pct = 5.0
    config.paper_trading = True
    config.discord_webhook_url = "https://discord-webhook.com"
    config.db_path = ":memory:"
    config.scanner_config = ScannerConfig()
    return config


@pytest.fixture(scope="session")
def scanner_config():
    """Create ScannerConfig instance for testing

    Session scope: This is a read-only immutable configuration object,
    so it's safe to share across all tests.
    """
    from skim.trading.core.config import ScannerConfig

    return ScannerConfig(
        gap_threshold=3.0,
        volume_filter=10000,
        price_filter=0.05,
        or_duration_minutes=5,
        or_poll_interval_seconds=30,
        gap_fill_tolerance=0.05,
        or_breakout_buffer=0.1,
    )


@pytest.fixture
def mock_trading_bot(mock_bot_config):
    """Create TradingBot instance with all dependencies mocked.

    This fixture patches all external dependencies (Database, IBKRClient,
    IBKRGapScanner, ASXAnnouncementScanner, DiscordNotifier) and returns
    a TradingBot instance ready for testing.

    The bot instance has access to mocked versions of:
    - bot.db (Database)
    - bot.ib_client (IBKRClient)
    - bot.ibkr_scanner (IBKRGapScanner)
    - bot.asx_scanner (ASXAnnouncementScanner)
    - bot.discord (DiscordNotifier)

    Args:
        mock_bot_config: Mock configuration fixture

    Returns:
        TradingBot: Bot instance with all dependencies mocked

    Example:
        def test_something(mock_trading_bot):
            mock_trading_bot.db.get_candidates.return_value = [...]
            result = mock_trading_bot.scan()
            assert result == expected
    """
    from unittest.mock import patch

    from skim.trading.core.bot import TradingBot

    with (
        patch("skim.trading.core.bot.Database"),
        patch("skim.trading.core.bot.IBKRClient"),
        patch("skim.trading.core.bot.IBKRMarketData"),
        patch("skim.trading.core.bot.IBKROrders"),
        patch("skim.trading.core.bot.IBKRGapScanner"),
        patch("skim.trading.core.bot.Scanner"),
        patch("skim.trading.core.bot.Trader"),
        patch("skim.trading.core.bot.Monitor"),
        patch("skim.trading.core.bot.DiscordNotifier"),
    ):
        bot = TradingBot(mock_bot_config)
        yield bot
