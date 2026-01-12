"""
Data loader for loading and managing ASX stock data.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from tqdm import tqdm

from skim.analysis.stock_data import StockData


class DataLoader:
    """Loads and manages ASX stock data from CSV files."""

    def __init__(
        self, data_dir: str = "data/analysis/raw/10year_asx_csv_202509"
    ):
        self.data_dir = Path(data_dir)
        self.stocks: dict[str, StockData] = {}

    def load_all(
        self,
        min_price: float = 0.20,
        min_volume: int = 50000,
        num_workers: int = 8,
        quiet: bool = False,
    ) -> dict[str, StockData]:
        """
        Load all CSV files from data directory.

        Args:
            min_price: Minimum price filter (default $0.20)
            min_volume: Minimum average volume filter (default 50k)
            num_workers: Number of concurrent workers (default 8)

        Returns:
            Dictionary mapping ticker -> StockData
        """
        csv_files = list(self.data_dir.glob("*.csv"))
        if not quiet:
            print(f"Found {len(csv_files)} CSV files")

        stocks = {}

        with ThreadPoolExecutor(max_workers=num_workers) as executor:
            future_to_file = {
                executor.submit(
                    self._load_single_stock, f, min_price, min_volume
                ): f
                for f in csv_files
            }

            iterator = as_completed(future_to_file)
            if not quiet:
                iterator = tqdm(
                    iterator, total=len(csv_files), desc="Loading stocks"
                )

            for future in iterator:
                try:
                    stock = future.result()
                    if stock:
                        stocks[stock.ticker] = stock
                except Exception:
                    pass

        self.stocks = stocks
        if not quiet:
            print(f"Loaded {len(stocks)} stocks meeting criteria")
        return stocks

    @staticmethod
    def _load_single_stock(
        filepath: Path, min_price: float, min_volume: int
    ) -> StockData | None:
        """Load a single stock from CSV file."""
        try:
            ticker = filepath.stem.upper()
            if len(ticker) != 3:
                return None
            stock = StockData(ticker)
            stock.load_from_csv(str(filepath))
            if stock.filter_by_criteria(min_price, min_volume):
                return stock
        except Exception:
            pass
        return None

    def get_stock(self, ticker: str) -> StockData | None:
        """Get stock data by ticker."""
        return self.stocks.get(ticker.upper())

    def get_all_tickers(self) -> list[str]:
        """Get list of all loaded tickers."""
        return sorted(self.stocks.keys())
