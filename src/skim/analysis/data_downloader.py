"""CoolTrader data downloader for daily ASX stock CSV files.

Downloads daily CSV files from cooltrader.com.au and saves them to
data/analysis/raw/cooltrader/ for processing by data_preprocessor.py.

Authentication: Login-based session using username/password form.
Download URL: https://www.data.cooltrader.com.au/amember/eodfiles/nextday/csv/{YYYYMMDD}.csv
"""

import json
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx
from dotenv import load_dotenv
from loguru import logger


@dataclass
class CoolTraderConfig:
    """Configuration for CoolTrader data downloader."""

    username: str
    password: str
    base_url: str = "https://data.cooltrader.com.au"
    download_dir: Path = field(
        default_factory=lambda: Path("data/raw/cooltrader")
    )
    session_file: Path = field(
        default_factory=lambda: Path("data/raw/cooltrader_session.json")
    )
    max_retries: int = 3
    retry_delay_base: float = 1.0

    @classmethod
    def from_env(cls) -> "CoolTraderConfig":
        """Create config from environment variables."""
        from pathlib import Path as PathLib

        load_dotenv()

        username = (
            PathLib(".env")
            .read_text()
            .split("COOLTRADER_USERNAME=")[1]
            .split("\n")[0]
            .strip()
        )
        password = (
            PathLib(".env")
            .read_text()
            .split("COOLTRADER_PASSWORD=")[1]
            .split("\n")[0]
            .strip()
        )

        return cls(
            username=username,
            password=password,
        )


class CoolTraderError(Exception):
    """Base exception for CoolTrader downloader errors."""

    pass


class CoolTraderAuthError(CoolTraderError):
    """Authentication failed."""

    pass


class CoolTraderDownloadError(CoolTraderError):
    """Download failed."""

    pass


class CoolTraderValidationError(CoolTraderError):
    """Downloaded data validation failed."""

    pass


class CoolTraderAuth:
    """Handles authentication to CoolTrader website using session cookies."""

    LOGIN_URL = "/amember/member"
    LOGOUT_URL = "/amember/logout"

    def __init__(self, config: CoolTraderConfig):
        """Initialise authentication handler.

        Args:
            config: CoolTraderConfig with credentials and settings.
        """
        self.config = config
        self._client: httpx.Client | None = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client with session persistence."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-AU,en;q=0.9",
                },
            )
            self._load_session()
        return self._client

    def _load_session(self) -> None:
        """Load session cookies from file if they exist."""
        if self._client is None:
            return
        if self.config.session_file.exists():
            try:
                session_data = json.loads(self.config.session_file.read_text())
                expires = datetime.fromisoformat(
                    session_data.get("expires", "")
                )
                if expires > datetime.now():
                    for cookie_data in session_data.get("cookies", []):
                        if isinstance(cookie_data, dict):
                            self._client.cookies.set(
                                cookie_data.get("name", ""),
                                cookie_data.get("value", ""),
                                domain=cookie_data.get(
                                    "domain", ".cooltrader.com.au"
                                ),
                            )
                    logger.debug("Loaded session from file")
                else:
                    logger.debug("Session file expired")
            except Exception as e:
                logger.debug(f"Failed to load session: {e}")

    def _save_session(self) -> None:
        """Save session cookies to file."""
        if self._client is None:
            return

        try:
            cookies = []
            for name in self._client.cookies:
                cookies.append(
                    {
                        "name": name,
                        "value": self._client.cookies.get(name),
                        "domain": ".cooltrader.com.au",
                    }
                )

            session_data = {
                "cookies": cookies,
                "expires": (datetime.now() + timedelta(hours=24)).isoformat(),
                "saved_at": datetime.now().isoformat(),
            }

            self.config.session_file.parent.mkdir(parents=True, exist_ok=True)
            self.config.session_file.write_text(json.dumps(session_data))
            logger.debug("Saved session to file")
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")

    def get_download_url(self, target_date: date) -> str:
        """Get the download URL for a specific date (public interface for tests).

        Args:
            target_date: The date to download CSV for

        Returns:
            Full URL to download CSV file.
        """
        return self._get_download_url(target_date)

    def _get_login_form_url(self) -> str:
        """Get the login page URL to extract CSRF token."""
        return f"{self.config.base_url}{self.LOGIN_URL}"

    def is_authenticated(self) -> bool:
        """Check if currently authenticated.

        Returns:
            True if session appears valid.
        """
        client = self._get_client()
        check_url = f"{self.config.base_url}/amember"

        try:
            response = client.get(check_url, follow_redirects=False)
            return (
                response.status_code == 200
                and "logout" in response.text.lower()
            )
        except Exception:
            return False

    def login(self) -> bool:
        """Authenticate to CoolTrader using username/password form.

        Returns:
            True if login successful.

        Raises:
            CoolTraderAuthError: If authentication fails.
        """
        client = self._get_client()
        login_url = self._get_login_form_url()

        logger.info("Logging in to CoolTrader...")

        try:
            response = client.get(login_url)
            response.raise_for_status()
        except httpx.HTTPError as e:
            raise CoolTraderAuthError(f"Failed to load login page: {e}") from e

        try:
            html = response.text

            csrf_token = None
            for line in html.split("\n"):
                if 'name="_form_"' in line or 'name="_form_" value="' in line:
                    start = line.find('value="')
                    if start != -1:
                        end = line.find('"', start + 7)
                        if end != -1:
                            csrf_token = line[start + 7 : end]
                            break

            if not csrf_token:
                csrf_token = "1"

            login_data = {
                "_form_": csrf_token,
                "amember_login": self.config.username,
                "amember_pass": self.config.password,
                "remember": "1",
            }

            login_post_url = f"{self.config.base_url}{self.LOGIN_URL}"

            response = client.post(login_post_url, data=login_data)
            response.raise_for_status()

            if (
                "login" in response.url.path.lower()
                or "invalid" in response.text.lower()
            ):
                raise CoolTraderAuthError("Login failed - invalid credentials")

            self._save_session()
            logger.info("Successfully logged in to CoolTrader")
            return True

        except httpx.HTTPError as e:
            raise CoolTraderAuthError(f"Login request failed: {e}") from e
        except CoolTraderAuthError:
            raise
        except Exception as e:
            raise CoolTraderAuthError(f"Unexpected login error: {e}") from e

    def logout(self) -> None:
        """Log out from CoolTrader."""
        client = self._get_client()
        logout_url = f"{self.config.base_url}{self.LOGOUT_URL}"
        try:
            client.get(logout_url)
            logger.info("Logged out from CoolTrader")
        except Exception:
            pass

    def close(self) -> None:
        """Close HTTP client and cleanup."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self) -> "CoolTraderAuth":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class CoolTraderDownloader:
    """Downloads and processes daily CSV files from CoolTrader."""

    def __init__(self, config: CoolTraderConfig | None = None):
        """Initialise downloader.

        Args:
            config: Optional config, will load from env if not provided.
        """
        if config is None:
            config = CoolTraderConfig.from_env()
        self.config = config
        self.config.download_dir.mkdir(parents=True, exist_ok=True)
        self.auth = CoolTraderAuth(self.config)
        self._processed_count = 0

    def get_download_url(self, target_date: date) -> str:
        """Get the download URL for a specific date (public interface).

        Args:
            target_date: The date to download CSV for.

        Returns:
            Full URL to download CSV file.
        """
        date_str = target_date.strftime("%Y%m%d")
        return f"{self.config.base_url}/amember/eodfiles/nextday/csv/{date_str}.csv"

    def download_csv(self, target_date: date) -> bytes | None:
        """Download CSV file for a specific date.

        Args:
            target_date: The date to download data for.

        Returns:
            CSV file content as bytes, or None if not available.

        Raises:
            CoolTraderDownloadError: If download fails after retries.
        """
        client = self.auth._get_client()
        download_url = self._get_download_url(target_date)

        logger.info(f"Downloading CSV for {target_date.isoformat()}...")

        last_error: Exception | None = None

        for attempt in range(self.config.max_retries):
            try:
                response = client.get(download_url, follow_redirects=True)
                response.raise_for_status()

                content = response.content

                if len(content) < 100:
                    logger.warning(
                        f"Downloaded file too small ({len(content)} bytes) - may be empty or error page"
                    )
                    if (
                        b"not found" in content.lower()
                        or b"error" in content.lower()
                    ):
                        return None

                return content

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    logger.warning(
                        f"CSV not available for {target_date.isoformat()} (404)"
                    )
                    return None
                last_error = e

            except httpx.TimeoutException as e:
                last_error = e

            except httpx.RequestError as e:
                last_error = e

            if attempt < self.config.max_retries - 1:
                delay = self.config.retry_delay_base * (2**attempt)
                logger.warning(
                    f"Download attempt {attempt + 1} failed, retrying in {delay}s..."
                )
                time.sleep(delay)

        raise CoolTraderDownloadError(
            f"Failed to download after {self.config.max_retries} attempts: {last_error}"
        )

    def _validate_csv(self, content: bytes, target_date: date) -> None:
        """Validate downloaded CSV content.

        Args:
            content: CSV file content.
            target_date: Expected date in the data.

        Raises:
            CoolTraderValidationError: If validation fails.
        """
        if not content:
            raise CoolTraderValidationError("Empty CSV content")

        text = content.decode("utf-8", errors="replace")
        lines = [line.strip() for line in text.split("\n") if line.strip()]

        if len(lines) < 2:
            raise CoolTraderValidationError(
                f"CSV has only {len(lines)} line(s)"
            )

        first_line_parts = lines[0].split(",")
        if len(first_line_parts) != 7:
            logger.warning(
                f"CSV first line doesn't have 7 columns: {lines[0][:50]}"
            )

        logger.debug(f"CSV validation passed: {len(lines)} rows")

    def _save_csv(self, content: bytes, target_date: date) -> Path:
        """Save CSV content to disk.

        Args:
            content: CSV file content.
            target_date: The date this data is for.

        Returns:
            Path to saved file.
        """
        date_str = target_date.strftime("%Y%m%d")
        output_path = self.config.download_dir / f"{date_str}.csv"
        output_path.write_bytes(content)
        logger.info(f"Saved CSV to {output_path}")
        return output_path

    def _parse_date_arg(self, date_arg: str) -> date:
        """Parse date argument in various formats.

        Args:
            date_arg: Date string (YYYYMMDD), "today", or "yesterday".

        Returns:
            Parsed date object.

        Raises:
            ValueError: If format is invalid.
        """
        date_arg_lower = date_arg.lower().strip()

        if date_arg_lower in ("today", "td"):
            return date.today()
        elif date_arg_lower in ("yesterday", "yd", "prev", "previous"):
            return date.today() - timedelta(days=1)
        else:
            try:
                return datetime.strptime(date_arg, "%Y%m%d").date()
            except ValueError:
                try:
                    return datetime.strptime(date_arg, "%Y-%m-%d").date()
                except ValueError:
                    raise ValueError(
                        f"Invalid date format: {date_arg}. Use YYYYMMDD, today, or yesterday"
                    ) from None

    def download_date(self, target_date: date) -> Path | None:
        """Download CSV for a specific date.

        Args:
            target_date: The date to download.

        Returns:
            Path to downloaded file, or None if not available.
        """
        try:
            self.auth.login()
            content = self.download_csv(target_date)

            if content is None:
                logger.warning(
                    f"No data available for {target_date.isoformat()}"
                )
                return None

            self._validate_csv(content, target_date)
            return self._save_csv(content, target_date)

        except CoolTraderAuthError as e:
            logger.error(f"Authentication failed: {e}")
            raise
        except CoolTraderDownloadError as e:
            logger.error(f"Download failed: {e}")
            raise
        except CoolTraderValidationError as e:
            logger.error(f"Validation failed: {e}")
            raise

    def download_for_date_str(self, date_arg: str) -> Path | None:
        """Download CSV for a date specified as string.

        Args:
            date_arg: Date string (YYYYMMDD), "today", or "yesterday".

        Returns:
            Path to downloaded file, or None if not available.
        """
        target_date = self._parse_date_arg(date_arg)
        return self.download_date(target_date)

    def download_today(self) -> Path | None:
        """Download today's CSV.

        Returns:
            Path to downloaded file, or None if not available.
        """
        return self.download_date(date.today())

    def download_yesterday(self) -> Path | None:
        """Download yesterday's CSV.

        Returns:
            Path to downloaded file, or None if not available.
        """
        yesterday = date.today() - timedelta(days=1)
        return self.download_date(yesterday)

    def download_date_range(
        self, start_date: date, end_date: date
    ) -> list[Path]:
        """Download CSV files for a range of dates.

        Args:
            start_date: First date to download.
            end_date: Last date to download.

        Returns:
            List of paths to downloaded files.
        """
        downloaded: list[Path] = []

        current = start_date
        while current <= end_date:
            path = self.download_date(current)
            if path:
                downloaded.append(path)
            current += timedelta(days=1)

        return downloaded

    def _check_remote_availability_single(self, target_date: date) -> bool:
        """Check if a CSV file is available remotely without downloading.

        Args:
            target_date: The date to check.

        Returns:
            True if file is available, False otherwise.
        """
        client = self.auth._get_client()
        download_url = self._get_download_url(target_date)

        try:
            response = client.head(download_url, follow_redirects=True)
            if response.status_code == 200:
                content_length = response.headers.get("content-length", "0")
                try:
                    if int(content_length) > 100:
                        return True
                except ValueError:
                    return True
            elif response.status_code == 404:
                return False
        except Exception:
            pass

        try:
            response = client.get(download_url, follow_redirects=True)
            if response.status_code == 200:
                content = response.content
                if len(content) > 100 and b"not found" not in content.lower():
                    return True
            return False
        except Exception:
            return False

    def check_remote_availability(
        self, start_date: date, end_date: date
    ) -> dict[date, bool]:
        """Check availability of CSV files for a date range.

        Makes lightweight HEAD requests to check which dates have data
        available without downloading full files.

        Args:
            start_date: First date to check.
            end_date: Last date to check.

        Returns:
            Dictionary mapping dates to availability status.
        """
        self.auth.login()

        availability: dict[date, bool] = {}
        current = start_date

        while current <= end_date:
            available = self._check_remote_availability_single(current)
            availability[current] = available
            current += timedelta(days=1)

        return availability

    def backfill_check(
        self, start_date: date, end_date: date
    ) -> dict[str, list[date]]:
        """Check for missing data and generate backfill report.

        Compares remote availability with local files to identify gaps.

        Args:
            start_date: First date to check.
            end_date: Last date to check.

        Returns:
            Dictionary with:
            - 'available_remote': dates with data on server
            - 'missing_remote': dates not available on server (data gaps)
            - 'not_downloaded': available but not in local storage
            - 'already_downloaded': available and already downloaded
        """
        availability = self.check_remote_availability(start_date, end_date)

        available_remote: list[date] = []
        missing_remote: list[date] = []
        not_downloaded: list[date] = []
        already_downloaded: list[date] = []

        local_files = set()
        for f in self.config.download_dir.glob("*.csv"):
            if f.name.endswith(".csv") and f.name[:8].isdigit():
                try:
                    file_date = datetime.strptime(f.name[:8], "%Y%m%d").date()
                    if start_date <= file_date <= end_date:
                        local_files.add(file_date)
                except ValueError:
                    pass

        for check_date, is_available in availability.items():
            if is_available:
                available_remote.append(check_date)
                if check_date in local_files:
                    already_downloaded.append(check_date)
                else:
                    not_downloaded.append(check_date)
            else:
                missing_remote.append(check_date)

        return {
            "available_remote": sorted(available_remote),
            "missing_remote": sorted(missing_remote),
            "not_downloaded": sorted(not_downloaded),
            "already_downloaded": sorted(already_downloaded),
        }

    def _find_unprocessed_files(self) -> list[Path]:
        """Find CSV files that haven't been processed yet.

        Returns:
            List of unprocessed CSV file paths.
        """
        processed_file = self.config.download_dir / ".processed_files.txt"
        processed: set[str] = set()

        if processed_file.exists():
            processed = set(processed_file.read_text().strip().split("\n"))

        all_files = sorted(self.config.download_dir.glob("*.csv"))
        unprocessed = [
            f
            for f in all_files
            if f.name not in processed and not f.name.startswith(".")
        ]

        return unprocessed

    def _mark_processed(self, filepath: Path) -> None:
        """Mark a file as processed.

        Args:
            filepath: Path to the processed file.
        """
        processed_file = self.config.download_dir / ".processed_files.txt"
        with open(processed_file, "a") as f:
            f.write(f"{filepath.name}\n")

    def process_downloads(self) -> int:
        """Process all unprocessed downloaded CSV files.

        Processes files by running data_preprocessor.py to merge
        downloaded data into the main data directory.

        Returns:
            Number of files processed.
        """
        from skim.analysis.data_preprocessor import DataPreprocessor

        unprocessed = self._find_unprocessed_files()

        if not unprocessed:
            logger.info("No new files to process")
            return 0

        logger.info(f"Processing {len(unprocessed)} downloaded file(s)...")

        for filepath in unprocessed:
            try:
                logger.info(f"Processing {filepath.name}...")

                preprocessor = DataPreprocessor(
                    source_dir="data/raw/10year_asx_csv_202509",
                    output_dir="data/processed/historical",
                    cooltrader_dir=str(self.config.download_dir),
                )

                preprocessor._process_cooltrader_single_file(filepath)
                self._mark_processed(filepath)
                self._processed_count += 1
                logger.info(f"Successfully processed {filepath.name}")

            except Exception as e:
                logger.error(f"Failed to process {filepath.name}: {e}")

        logger.info(f"Processed {self._processed_count} file(s)")
        return self._processed_count

    def run(self) -> None:
        """Run complete download and process workflow."""
        logger.info("Starting CoolTrader download workflow...")

        try:
            self.auth.login()

            path = self.download_today()

            if path:
                logger.info(f"Downloaded {path.name}")
                self.process_downloads()
            else:
                logger.warning("No data downloaded (file not available yet)")

        except CoolTraderError as e:
            logger.error(f"CoolTrader error: {e}")
        finally:
            self.auth.close()

    def close(self) -> None:
        """Close the downloader and cleanup resources."""
        self.auth.close()

    def __enter__(self) -> "CoolTraderDownloader":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


def download_for_date(date_arg: str) -> Path | None:
    """Convenience function to download CSV for a specific date.

    Args:
        date_arg: Date string (YYYYMMDD), "today", or "yesterday".

    Returns:
        Path to downloaded file, or None if not available.
    """
    with CoolTraderDownloader() as downloader:
        return downloader.download_for_date_str(date_arg)


def download_today_and_process() -> int:
    """Download today's CSV and process it.

    Returns:
        Number of files processed.
    """
    with CoolTraderDownloader() as downloader:
        if downloader.download_today():
            return downloader.process_downloads()
        return 0


def backfill_check(start_date: date, end_date: date) -> dict[str, list[date]]:
    """Check for missing data and generate backfill report.

    Args:
        start_date: First date to check.
        end_date: Last date to check.

    Returns:
        Dictionary with backfill information.
    """
    with CoolTraderDownloader() as downloader:
        return downloader.backfill_check(start_date, end_date)


def download_main():
    """CLI entry point for data download command."""
    import argparse

    parser = argparse.ArgumentParser(description="CoolTrader data downloader")
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands"
    )

    download_parser = subparsers.add_parser(
        "download", help="Download data for a date"
    )
    download_parser.add_argument(
        "date",
        nargs="?",
        default="today",
        help="Date to download (YYYYMMDD, today, yesterday)",
    )
    download_parser.add_argument(
        "--process",
        action="store_true",
        help="Process downloaded files after download",
    )

    subparsers.add_parser("process", help="Process downloaded files")

    subparsers.add_parser("run", help="Download today and process")

    backfill_parser = subparsers.add_parser(
        "backfill", help="Check for missing data and generate backfill report"
    )
    backfill_parser.add_argument(
        "--start",
        required=True,
        help="Start date (YYYYMMDD)",
    )
    backfill_parser.add_argument(
        "--end",
        required=True,
        help="End date (YYYYMMDD)",
    )
    backfill_parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Only show dates that need downloading",
    )
    backfill_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON for programmatic use",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    if args.command == "download":
        with CoolTraderDownloader() as downloader:
            path = downloader.download_for_date_str(args.date)
            if path:
                print(f"Downloaded: {path}")
                if args.process:
                    count = downloader.process_downloads()
                    print(f"Processed {count} file(s)")
            else:
                print("No data available")
    elif args.command == "process":
        with CoolTraderDownloader() as downloader:
            count = downloader.process_downloads()
            print(f"Processed {count} file(s)")
    elif args.command == "run":
        with CoolTraderDownloader() as downloader:
            if downloader.download_today():
                count = downloader.process_downloads()
                print(f"Downloaded and processed {count} file(s)")
            else:
                print("No data available")
    elif args.command == "backfill":
        with CoolTraderDownloader() as downloader:
            start = downloader._parse_date_arg(args.start)
            end = downloader._parse_date_arg(args.end)
            report = backfill_check(start_date=start, end_date=end)

            if args.json:
                import json

                json_output = {
                    "range": f"{start.isoformat()} to {end.isoformat()}",
                    "available_remote": [
                        d.isoformat() for d in report["available_remote"]
                    ],
                    "missing_remote": [
                        d.isoformat() for d in report["missing_remote"]
                    ],
                    "not_downloaded": [
                        d.isoformat() for d in report["not_downloaded"]
                    ],
                    "already_downloaded": [
                        d.isoformat() for d in report["already_downloaded"]
                    ],
                }
                print(json.dumps(json_output, indent=2))
            else:
                print(
                    f"Backfill Report: {start.isoformat()} to {end.isoformat()}"
                )
                print()

                if report["missing_remote"]:
                    print(
                        f"Missing from server (data gaps): {len(report['missing_remote'])}"
                    )
                    for d in report["missing_remote"]:
                        print(f"  {d.isoformat()}")
                    print()

                if not args.missing_only:
                    if report["not_downloaded"]:
                        print(
                            f"Available but not downloaded: {len(report['not_downloaded'])}"
                        )
                        for d in report["not_downloaded"]:
                            print(f"  {d.isoformat()}")
                        print()

                    if report["already_downloaded"]:
                        print(
                            f"Already downloaded: {len(report['already_downloaded'])}"
                        )
                        for d in report["already_downloaded"]:
                            print(f"  {d.isoformat()}")


if __name__ == "__main__":
    download_main()
