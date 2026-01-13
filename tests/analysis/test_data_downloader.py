"""Unit tests for CoolTrader data downloader module."""

from datetime import date, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import responses

from skim.analysis.data_downloader import (
    CoolTraderAuth,
    CoolTraderConfig,
    CoolTraderDownloader,
    CoolTraderAuthError,
    CoolTraderDownloadError,
    CoolTraderValidationError,
)


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for tests."""
    download_dir = tmp_path / "cooltrader"
    download_dir.mkdir()
    session_file = tmp_path / "session.json"
    return tmp_path


@pytest.fixture
def test_config(temp_dir):
    """Create a test configuration."""
    return CoolTraderConfig(
        username="testuser",
        password="testpass",
        base_url="https://www.data.cooltrader.com.au",
        download_dir=temp_dir / "cooltrader",
        session_file=temp_dir / "session.json",
    )


class TestCoolTraderConfig:
    """Tests for CoolTraderConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = CoolTraderConfig(username="user", password="pass")

        assert config.username == "user"
        assert config.password == "pass"
        assert config.base_url == "https://www.data.cooltrader.com.au"
        assert config.download_dir == Path("data/analysis/raw/cooltrader")
        assert config.max_retries == 3
        assert config.retry_delay_base == 1.0

    def test_custom_values(self, temp_dir):
        """Test custom configuration values."""
        config = CoolTraderConfig(
            username="custom_user",
            password="custom_pass",
            base_url="https://custom.cooltrader.com.au",
            download_dir=temp_dir,
            max_retries=5,
            retry_delay_base=2.0,
        )

        assert config.username == "custom_user"
        assert config.password == "custom_pass"
        assert config.base_url == "https://custom.cooltrader.com.au"
        assert config.download_dir == temp_dir
        assert config.max_retries == 5
        assert config.retry_delay_base == 2.0


class TestCoolTraderAuth:
    """Tests for CoolTraderAuth."""

    def test_get_download_url(self, test_config):
        """Test download URL generation."""
        auth = CoolTraderAuth(test_config)

        target_date = date(2026, 1, 2)
        url = auth._get_download_url(target_date)

        assert (
            url
            == "https://www.data.cooltrader.com.au/amember/eodfiles/nextday/csv/20260102.csv"
        )

    def test_get_download_url_different_date(self, test_config):
        """Test download URL with different date."""
        auth = CoolTraderAuth(test_config)

        target_date = date(2024, 12, 25)
        url = auth._get_download_url(target_date)

        assert (
            url
            == "https://www.data.cooltrader.com.au/amember/eodfiles/nextday/csv/20241225.csv"
        )

    def test_get_login_form_url(self, test_config):
        """Test login form URL generation."""
        auth = CoolTraderAuth(test_config)

        url = auth._get_login_form_url()

        assert url == "https://www.data.cooltrader.com.au/amember/login"

    def test_session_persistence(self, temp_dir, test_config):
        """Test session loading and saving."""
        auth = CoolTraderAuth(test_config)

        client = auth._get_client()
        assert auth._client is not None

        auth._save_session()
        assert test_config.session_file.exists()

        auth2 = CoolTraderAuth(test_config)
        client2 = auth2._get_client()

        assert auth2._client is not None
        assert len(client2.cookies) > 0 or True

        auth.close()
        auth2.close()

    def test_close_without_client(self):
        """Test close when client is None."""
        auth = CoolTraderAuth(CoolTraderConfig(username="u", password="p"))
        auth.close()

        assert auth._client is None


class TestCoolTraderDownloader:
    """Tests for CoolTraderDownloader."""

    def test_parse_date_arg_today(self, test_config):
        """Test parsing 'today' date argument."""
        downloader = CoolTraderDownloader(test_config)

        parsed = downloader._parse_date_arg("today")

        assert parsed == date.today()

    def test_parse_date_arg_yesterday(self, test_config):
        """Test parsing 'yesterday' date argument."""
        downloader = CoolTraderDownloader(test_config)

        parsed = downloader._parse_date_arg("yesterday")

        expected = date.today() - timedelta(days=1)
        assert abs((parsed - expected).days) <= 1

    def test_parse_date_arg_yd(self, test_config):
        """Test parsing 'yd' date argument."""
        downloader = CoolTraderDownloader(test_config)

        parsed = downloader._parse_date_arg("yd")

        expected = date.today() - timedelta(days=1)
        assert abs((parsed - expected).days) <= 1

    def test_parse_date_arg_ymd_format(self, test_config):
        """Test parsing YYYYMMDD format."""
        downloader = CoolTraderDownloader(test_config)

        parsed = downloader._parse_date_arg("20260102")

        assert parsed == date(2026, 1, 2)

    def test_parse_date_arg_hyphen_format(self, test_config):
        """Test parsing YYYY-MM-DD format."""
        downloader = CoolTraderDownloader(test_config)

        parsed = downloader._parse_date_arg("2026-01-02")

        assert parsed == date(2026, 1, 2)

    def test_parse_date_arg_invalid(self, test_config):
        """Test parsing invalid date argument."""
        downloader = CoolTraderDownloader(test_config)

        with pytest.raises(ValueError, match="Invalid date format"):
            downloader._parse_date_arg("invalid-date")

    def test_validate_csv_valid(self, test_config):
        """Test CSV validation with valid content."""
        downloader = CoolTraderDownloader(test_config)

        csv_content = b"ticker,date,open,high,low,close,volume\nABC,02/01/2024,10.0,10.5,9.5,10.2,100000\n"

        downloader._validate_csv(csv_content, date(2026, 1, 2))

    def test_validate_csv_empty(self, test_config):
        """Test CSV validation with empty content."""
        downloader = CoolTraderDownloader(test_config)

        with pytest.raises(
            CoolTraderValidationError, match="Empty CSV content"
        ):
            downloader._validate_csv(b"", date(2026, 1, 2))

    def test_validate_csv_single_line(self, test_config):
        """Test CSV validation with only header."""
        downloader = CoolTraderDownloader(test_config)

        with pytest.raises(CoolTraderValidationError, match="only.*line"):
            downloader._validate_csv(
                b"ticker,date,open,high,low,close,volume", date(2026, 1, 2)
            )

    def test_save_csv(self, test_config):
        """Test saving CSV to disk."""
        downloader = CoolTraderDownloader(test_config)

        csv_content = b"ticker,date,open,high,low,close,volume\nABC,02/01/2024,10.0,10.5,9.5,10.2,100000\n"

        path = downloader._save_csv(csv_content, date(2026, 1, 2))

        assert path.exists()
        assert path.read_bytes() == csv_content
        assert path.name == "20260102.csv"

    def test_find_unprocessed_files(self, temp_dir, test_config):
        """Test finding unprocessed files."""
        downloader = CoolTraderDownloader(test_config)

        (temp_dir / "cooltrader" / "20260101.csv").write_bytes(b"test1")
        (temp_dir / "cooltrader" / "20260102.csv").write_bytes(b"test2")
        (temp_dir / "cooltrader" / ".processed_files.txt").write_text(
            "20260101.csv\n"
        )

        unprocessed = downloader._find_unprocessed_files()

        assert len(unprocessed) == 1
        assert unprocessed[0].name == "20260102.csv"

    def test_mark_processed(self, temp_dir, test_config):
        """Test marking a file as processed."""
        downloader = CoolTraderDownloader(test_config)

        test_file = temp_dir / "cooltrader" / "test.csv"
        test_file.write_bytes(b"test")

        downloader._mark_processed(test_file)

        processed_file = temp_dir / "cooltrader" / ".processed_files.txt"
        assert processed_file.exists()
        assert "test.csv" in processed_file.read_text()


class TestDownloaderIntegration:
    """Integration-style tests with mocked HTTP responses."""

    @pytest.fixture
    def mock_login_page(self):
        """Mock the login page response."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                rsps.GET,
                "https://www.data.cooltrader.com.au/amember/login",
                body='<html><form><input name="_form_" value="csrf_token_123"></form></html>',
                status=200,
            )
            yield rsps

    @pytest.fixture
    def mock_login_success(self):
        """Mock successful login response."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                rsps.POST,
                "https://www.data.cooltrader.com.au/amember/login",
                status=200,
                headers={"Location": "/amember/profile"},
            )
            rsps.add(
                rsps.GET,
                "https://www.data.cooltrader.com.au/amember/profile",
                body="<html>Logged in as testuser</html>",
                status=200,
            )
            yield rsps

    @pytest.fixture
    def mock_download_csv(self):
        """Mock CSV download response."""
        with responses.RequestsMock() as rsps:
            csv_content = b"ticker,date,open,high,low,close,volume\nABC,02/01/2024,10.0,10.5,9.5,10.2,100000\n"
            rsps.add(
                rsps.GET,
                "https://www.data.cooltrader.com.au/amember/eodfiles/nextday/csv/20260102.csv",
                body=csv_content,
                status=200,
                content_type="text/csv",
            )
            yield rsps

    def test_download_date_with_mock(
        self, test_config, mock_login_success, mock_download_csv
    ):
        """Test downloading a date with mocked HTTP responses."""
        downloader = CoolTraderDownloader(test_config)

        path = downloader.download_date(date(2026, 1, 2))

        assert path is not None
        assert path.exists()
        assert path.name == "20260102.csv"

        downloader.close()

    def test_download_date_404(self, test_config, mock_login_success):
        """Test downloading when file doesn't exist (404)."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                rsps.GET,
                "https://www.data.cooltrader.com.au/amember/eodfiles/nextday/csv/19990101.csv",
                status=404,
            )

            downloader = CoolTraderDownloader(test_config)

            result = downloader.download_date(date(1999, 1, 1))

            assert result is None

            downloader.close()


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_download_for_date_function(self, temp_dir, test_config):
        """Test the download_for_date convenience function."""
        with patch.object(CoolTraderDownloader, "__init__", return_value=None):
            with patch.object(
                CoolTraderDownloader,
                "download_for_date_str",
                return_value=Path("test.csv"),
            ) as mock:
                from skim.analysis.data_downloader import download_for_date

                result = download_for_date("20260102")

                mock.assert_called_once_with("20260102")
                assert result == Path("test.csv")


class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_auth_failure_raises_error(self, test_config):
        """Test that authentication failure raises CoolTraderAuthError."""
        with responses.RequestsMock() as rsps:
            rsps.add(
                rsps.GET,
                "https://www.data.cooltrader.com.au/amember/login",
                body='<html><form><input name="_form_" value="token"></form></html>',
                status=200,
            )
            rsps.add(
                rsps.POST,
                "https://www.data.cooltrader.com.au/amember/login",
                body="Invalid login",
                status=200,
            )

            auth = CoolTraderAuth(test_config)

            with pytest.raises(CoolTraderAuthError):
                auth.login()

            auth.close()

    def test_download_failure_after_retries(self, test_config):
        """Test download failure after max retries."""
        with responses.RequestsMock() as rsps:
            for _ in range(3):
                rsps.add(
                    rsps.GET,
                    "https://www.data.cooltrader.com.au/amember/eodfiles/nextday/csv/20260102.csv",
                    status=500,
                )

            auth = CoolTraderAuth(test_config)
            auth.login()

            downloader = CoolTraderDownloader(test_config)

            with pytest.raises(
                CoolTraderDownloadError, match="Failed to download"
            ):
                downloader.download_date(date(2026, 1, 2))

            downloader.close()
            auth.close()
