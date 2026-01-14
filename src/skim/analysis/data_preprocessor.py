"""
Data preprocessing script to aggregate ASX stock data.

Copies 10-year historical data and merges new zip file updates
into a unified data/ directory for DataLoader.
"""

import shutil
import tempfile
import zipfile
from contextlib import suppress
from pathlib import Path

import polars as pl
from rich.console import Console
from tqdm import tqdm


class DataPreprocessor:
    """Aggregates 10-year historical data with new zip file updates."""

    def __init__(
        self,
        source_dir: str = "data/raw/10year_asx_csv_202509",
        output_dir: str = "data/processed/historical",
        zip_pattern: str = "data/raw/*.zip",
        cooltrader_dir: str | None = None,
    ):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.zip_pattern = zip_pattern
        self.cooltrader_dir = Path(cooltrader_dir) if cooltrader_dir else None
        self.console = Console()

    def run(self) -> None:
        """Run complete preprocessing pipeline."""
        self.console.print("[cyan]→ Starting data aggregation...[/cyan]")

        if not self.source_dir.exists():
            self.console.print(
                f"[red]✗ Source directory not found: {self.source_dir}[/red]"
            )
            return

        self._copy_base_data()
        zip_files = self._get_sorted_zip_files()

        if not zip_files:
            self.console.print(
                "[yellow]![/yellow] No zip files found to process"
            )
        else:
            self.console.print(
                f"[cyan]→ Processing {len(zip_files)} zip files...[/cyan]"
            )
            new_data = self._collect_zip_data(zip_files)
            self._merge_new_data(new_data)

        if self.cooltrader_dir and self.cooltrader_dir.exists():
            self._process_cooltrader_data()

        self._print_summary()

    def _copy_base_data(self) -> None:
        """Copy all CSV files from source directory to output directory."""
        if self.output_dir.exists():
            csv_count = len(list(self.output_dir.glob("*.csv")))
            self.console.print(
                f"[cyan]→ Output directory already exists with {csv_count} CSVs[/cyan]"
            )
            return

        self.output_dir.mkdir(exist_ok=True)
        csv_files = list(self.source_dir.glob("*.csv"))

        for filepath in tqdm(csv_files, desc="Copying base data"):
            with suppress(Exception):
                shutil.copy2(filepath, self.output_dir / filepath.name)

        self.console.print(
            f"[green]✓ Copied {len(csv_files)} tickers from {self.source_dir.name}[/green]"
        )

    def _get_sorted_zip_files(self) -> list[Path]:
        """Discover and sort zip files alphabetically (YYYYMM order)."""
        return sorted(Path(".").glob(self.zip_pattern))

    def _collect_zip_data(
        self, zip_files: list[Path]
    ) -> dict[str, list[pl.DataFrame]]:
        """Collect all new data from zip files into memory."""
        new_data: dict[str, list[pl.DataFrame]] = {}

        for zip_path in zip_files:
            self.console.print(f"[cyan]→ Reading {zip_path.name}...[/cyan]")

            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)

                try:
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall(temp_path)
                except Exception as e:
                    self.console.print(
                        f"[red]✗ Failed to extract {zip_path.name}: {e}[/red]"
                    )
                    continue

                daily_files = list(temp_path.glob("*.csv"))

                for daily_file in tqdm(
                    daily_files, desc=f"  {zip_path.name}", leave=False
                ):
                    try:
                        daily_df = pl.read_csv(
                            daily_file,
                            has_header=False,
                            new_columns=[
                                "ticker",
                                "date",
                                "open",
                                "high",
                                "low",
                                "close",
                                "volume",
                            ],
                        )
                        daily_df = daily_df.with_columns(
                            pl.col("date").str.strptime(pl.Date, "%d/%m/%Y")
                        )

                        grouped = daily_df.group_by("ticker")
                        for group_data in grouped:
                            ticker_name = group_data[0][0]
                            group_df = group_data[1]
                            if ticker_name not in new_data:
                                new_data[ticker_name] = []
                            new_data[ticker_name].append(group_df)
                    except Exception:
                        continue

        return new_data

    def _merge_new_data(self, new_data: dict[str, list[pl.DataFrame]]) -> None:
        """Merge collected new data into ticker CSV files."""
        self.console.print(
            f"[cyan]→ Merging data for {len(new_data)} tickers...[/cyan]"
        )

        for ticker, data_frames in tqdm(new_data.items(), desc="Merging data"):
            output_file = self.output_dir / f"{ticker.upper()}.csv"

            try:
                if output_file.exists():
                    existing_df = pl.read_csv(
                        output_file,
                        has_header=False,
                        new_columns=[
                            "ticker",
                            "date",
                            "open",
                            "high",
                            "low",
                            "close",
                            "volume",
                        ],
                    )
                    existing_df = existing_df.with_columns(
                        pl.col("date").str.strptime(pl.Date, "%d/%m/%Y")
                    )
                    all_data = [existing_df] + data_frames
                else:
                    all_data = data_frames

                merged_df = pl.concat(all_data)
                merged_df = merged_df.sort("date")
                merged_df = merged_df.unique(
                    subset=["ticker", "date"], keep="last", maintain_order=True
                )

                merged_df = merged_df.with_columns(
                    pl.col("date").dt.strftime("%d/%m/%Y")
                )
                merged_df.write_csv(output_file, include_header=False)

            except Exception:
                continue

    def _process_cooltrader_data(self) -> None:
        """Process downloaded daily CSV files from CoolTrader."""
        if not self.cooltrader_dir:
            return

        daily_files = sorted(self.cooltrader_dir.glob("*.csv"))

        if not daily_files:
            self.console.print(
                "[yellow]![/yellow] No CoolTrader files to process"
            )
            return

        self.console.print(
            f"[cyan]→ Processing {len(daily_files)} CoolTrader file(s)...[/cyan]"
        )

        for daily_file in tqdm(daily_files, desc="CoolTrader files"):
            try:
                self._process_cooltrader_single_file(daily_file)
            except Exception as e:
                self.console.print(
                    f"[red]✗ Failed to process {daily_file.name}: {e}[/red]"
                )

        self.console.print(
            f"[green]✓ Processed {len(daily_files)} CoolTrader file(s)[/green]"
        )

    def _process_cooltrader_single_file(self, filepath: Path) -> None:
        """Process a single CoolTrader daily CSV file.

        Args:
            filepath: Path to the daily CSV file.
        """
        try:
            daily_df = pl.read_csv(
                filepath,
                has_header=False,
                new_columns=[
                    "ticker",
                    "date",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
                schema_overrides={
                    "ticker": pl.Utf8,
                    "date": pl.Utf8,
                    "open": pl.Float64,
                    "high": pl.Float64,
                    "low": pl.Float64,
                    "close": pl.Float64,
                    "volume": pl.Int64,
                },
            )
            daily_df = daily_df.with_columns(
                pl.col("date").str.strptime(pl.Date, "%d/%m/%Y")
            )

            grouped = daily_df.group_by("ticker")
            for group_data in grouped:
                ticker_name = group_data[0][0]
                group_df = group_data[1]
                self._merge_cooltricker_ticker(ticker_name, group_df)

        except Exception as e:
            raise RuntimeError(f"Failed to process {filepath.name}: {e}") from e

    def _merge_cooltricker_ticker(
        self, ticker: str, new_df: pl.DataFrame
    ) -> None:
        """Merge CoolTrader data for a single ticker.

        Args:
            ticker: Ticker symbol.
            new_df: DataFrame with new data for the ticker.
        """
        output_file = self.output_dir / f"{ticker.upper()}.csv"

        try:
            if output_file.exists():
                existing_df = pl.read_csv(
                    output_file,
                    has_header=False,
                    new_columns=[
                        "ticker",
                        "date",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                    ],
                    schema_overrides={
                        "ticker": pl.Utf8,
                        "date": pl.Utf8,
                        "open": pl.Float64,
                        "high": pl.Float64,
                        "low": pl.Float64,
                        "close": pl.Float64,
                        "volume": pl.Int64,
                    },
                )
                existing_df = existing_df.with_columns(
                    pl.col("date").str.strptime(pl.Date, "%d/%m/%Y")
                )
                all_data = [existing_df, new_df]
            else:
                all_data = [new_df]

            merged_df = pl.concat(all_data)
            merged_df = merged_df.sort("date")
            merged_df = merged_df.unique(
                subset=["ticker", "date"], keep="last", maintain_order=True
            )

            merged_df = merged_df.with_columns(
                pl.col("date").dt.strftime("%d/%m/%Y")
            )
            merged_df.write_csv(output_file, include_header=False)

        except Exception as e:
            raise RuntimeError(f"Failed to merge {ticker} data: {e}") from e

    def _print_summary(self) -> None:
        """Print processing summary."""
        csv_files = list(self.output_dir.glob("*.csv"))

        date_ranges = []
        for csv_file in csv_files[:10]:
            try:
                df = pl.read_csv(
                    csv_file,
                    has_header=False,
                    new_columns=[
                        "ticker",
                        "date",
                        "open",
                        "high",
                        "low",
                        "close",
                        "volume",
                    ],
                )
                df = df.with_columns(
                    pl.col("date").str.strptime(pl.Date, "%d/%m/%Y")
                )
                if len(df) > 0:
                    date_ranges.append((df["date"].min(), df["date"].max()))
            except Exception:
                pass

        if date_ranges:
            overall_start = min(r[0] for r in date_ranges)
            overall_end = max(r[1] for r in date_ranges)
            date_range_str = f"{overall_start.strftime('%Y-%m-%d')} to {overall_end.strftime('%Y-%m-%d')}"
        else:
            date_range_str = "N/A"

        self.console.print("[green]✓ Aggregation complete![/green]")
        self.console.print(f"  - Output directory: {self.output_dir}/")
        self.console.print(f"  - Total tickers: {len(csv_files)}")
        self.console.print(f"  - Data range: {date_range_str}")


if __name__ == "__main__":
    preprocessor = DataPreprocessor()
    preprocessor.run()
