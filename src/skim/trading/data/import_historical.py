#!/usr/bin/env python
"""Import historical ASX stock data from CSV files into SQLite database.

Usage:
    python -m skim.trading.data.import_historical --help

Examples:
    # Import all CSVs from a directory
    python -m skim.trading.data.import_historical --data-dir data/analysis/raw/10year_asx_csv_202509

    # Import a single day's update
    python -m skim.trading.data.import_historical --data-dir data/analysis/raw/202512.zip --daily-update

    # Dry run to see what would be imported
    python -mskim.trading.data.import_historical --data-dir data/analysis/raw/10year_asx_csv_202509 --dry-run
"""

import argparse
import sys
import zipfile
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path

from loguru import logger

from skim.infrastructure.database.historical import (
    DailyPrice,
    HistoricalDataRepository,
)
from skim.infrastructure.database.historical.paths import get_historical_db_path
from skim.infrastructure.database.historical.repository import (
    HistoricalDatabase,
)


def parse_csv_date(date_str: str) -> datetime:
    """Parse CSV date format (DD/MM/YYYY) to datetime.

    Args:
        date_str: Date string in DD/MM/YYYY format

    Returns:
        datetime object
    """
    return datetime.strptime(date_str.strip(), "%d/%m/%Y")


def read_csv_file(filepath: Path) -> Iterator[DailyPrice]:
    """Read a single CSV file and yield DailyPrice objects.

    Args:
        filepath: Path to CSV file

    Yields:
        DailyPrice objects
    """
    ticker = filepath.stem.upper()
    if len(ticker) != 3:
        logger.debug(f"Skipping non-3-char ticker: {filepath.name}")
        return

    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    for line in content.strip().split("\n"):
        if not line.strip():
            continue

        parts = line.split(",")
        if len(parts) < 7:
            logger.warning(
                f"Invalid line format in {filepath.name}: {line[:50]}..."
            )
            continue

        try:
            date_str = parts[1]
            trade_date = parse_csv_date(date_str).date()

            price = DailyPrice(
                ticker=ticker,
                trade_date=trade_date,
                open=float(parts[2]),
                high=float(parts[3]),
                low=float(parts[4]),
                close=float(parts[5]),
                volume=int(parts[6]),
            )
            yield price
        except (ValueError, IndexError) as e:
            logger.warning(f"Error parsing line in {filepath.name}: {e}")
            continue


def read_csv_from_zip(zip_path: Path) -> Iterator[DailyPrice]:
    """Read CSV files from a zip archive (for daily updates).

    Args:
        zip_path: Path to zip file

    Yields:
        DailyPrice objects
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if not name.endswith(".csv"):
                continue

            ticker = Path(name).stem.upper()
            if len(ticker) != 3:
                continue

            with zf.open(name) as f:
                content = f.read().decode("utf-8")

            for line in content.strip().split("\n"):
                if not line.strip():
                    continue

                parts = line.split(",")
                if len(parts) < 7:
                    continue

                try:
                    date_str = parts[1]
                    trade_date = parse_csv_date(date_str).date()

                    price = DailyPrice(
                        ticker=ticker,
                        trade_date=trade_date,
                        open=float(parts[2]),
                        high=float(parts[3]),
                        low=float(parts[4]),
                        close=float(parts[5]),
                        volume=int(parts[6]),
                    )
                    yield price
                except (ValueError, IndexError):
                    continue


def import_directory(
    data_dir: Path,
    repo: HistoricalDataRepository,
    dry_run: bool = False,
    quiet: bool = False,
) -> tuple[int, int]:
    """Import all CSV files from a directory.

    Args:
        data_dir: Directory containing CSV files
        repo: HistoricalDataRepository instance
        dry_run: If True, don't actually write to database
        quiet: If True, suppress progress output

    Returns:
        Tuple of (files_processed, records_imported)
    """
    csv_files = list(data_dir.glob("*.csv"))
    if not csv_files:
        logger.warning(f"No CSV files found in {data_dir}")
        return 0, 0

    if not quiet:
        logger.info(f"Found {len(csv_files)} CSV files in {data_dir}")

    files_processed = 0
    records_imported = 0

    for csv_file in csv_files:
        prices = list(read_csv_file(csv_file))
        if not prices:
            continue

        files_processed += 1
        records_imported += len(prices)

        if not dry_run:
            repo.bulk_insert_prices(prices)

        if not quiet:
            logger.debug(f"Processed {csv_file.name}: {len(prices)} records")

    return files_processed, records_imported


def import_daily_zip(
    zip_path: Path,
    repo: HistoricalDataRepository,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Import CSV files from a zip archive (for daily updates).

    Args:
        zip_path: Path to zip file
        repo: HistoricalDataRepository instance
        dry_run: If True, don't actually write to database

    Returns:
        Tuple of (files_processed, records_imported)
    """
    if not zip_path.exists():
        logger.error(f"Zip file not found: {zip_path}")
        return 0, 0

    prices = list(read_csv_from_zip(zip_path))
    if not prices:
        logger.warning(f"No valid data found in {zip_path}")
        return 0, 0

    tickers = {p.ticker for p in prices}

    if not dry_run:
        repo.bulk_insert_prices(prices)

    logger.info(
        f"Imported {len(prices)} records for {len(tickers)} tickers from {zip_path.name}"
    )
    return len(tickers), len(prices)


def get_repository() -> HistoricalDataRepository:
    """Get a HistoricalDataRepository instance.

    Returns:
        Configured HistoricalDataRepository
    """
    db_path = get_historical_db_path()
    db = HistoricalDatabase(str(db_path))
    return HistoricalDataRepository(db)


def main() -> int:
    """Main entry point for the import script.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    parser = argparse.ArgumentParser(
        description="Import historical ASX stock data from CSV files into SQLite database"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directory containing CSV files or a zip file for daily updates",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Path to historical SQLite database (auto-detected if not provided)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without actually importing",
    )
    parser.add_argument(
        "--daily-update",
        action="store_true",
        help="Treat data-dir as a zip file containing daily updates",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    if args.verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        logger.remove()
        logger.add(sys.stderr, level="INFO")

    try:
        repo = get_repository()

        if args.daily_update:
            files, records = import_daily_zip(
                args.data_dir, repo, dry_run=args.dry_run
            )
        else:
            files, records = import_directory(
                args.data_dir, repo, dry_run=args.dry_run, quiet=args.quiet
            )

        if args.dry_run:
            logger.info(
                f"[DRY RUN] Would import {records} records from {files} files"
            )
        else:
            logger.info(f"Imported {records} records from {files} files")

            stats = repo.get_tickers_count()
            total = repo.get_total_records()
            logger.info(
                f"Database now contains {stats} tickers, {total} total records"
            )

        return 0

    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
