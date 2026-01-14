"""
Stock data model for representing ASX stock price history.
"""

import statistics
from datetime import datetime

import polars as pl


class StockData:
    """Represents a single stock with OHLCV data."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.df: pl.DataFrame | None = None

    def load_from_csv(self, filepath: str) -> None:
        """
        Load stock data from CSV file.

        Expected format: Ticker,Date,Open,High,Low,Close,Volume
        Date format: DD/MM/YYYY
        """
        df = pl.read_csv(
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
        )

        df = df.with_columns(pl.col("date").str.strptime(pl.Date, "%d/%m/%Y"))
        df = df.sort("date").unique(subset=["date"], maintain_order=True)

        self.df = df

    def calculate_return(
        self, start_date: datetime, end_date: datetime
    ) -> float | None:
        """Calculate percentage return between two dates."""
        if self.df is None:
            return None

        period_df = self.df.filter(
            (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
        )

        if len(period_df) < 2:
            return None

        start_price = period_df["close"][0]
        end_price = period_df["close"][-1]

        if start_price is None or end_price is None or start_price == 0:
            return None

        return ((end_price - start_price) / start_price) * 100

    def get_price(self, date: datetime) -> float | None:
        """Get closing price on a specific date."""
        if self.df is None:
            return None
        filtered = self.df.filter(pl.col("date") == date)
        if len(filtered) == 0:
            return None
        return filtered["close"][0]

    def calculate_returns_over_period(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """Calculate various return metrics over a period."""
        if self.df is None:
            return {}

        period_df = self.df.filter(
            (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
        )

        if len(period_df) < 2:
            return {}

        close_prices = period_df["close"].to_list()
        volumes = period_df["volume"].to_list()

        start_price_val = close_prices[0]
        end_price_val = close_prices[-1]

        if start_price_val is None or end_price_val is None:
            return {}

        try:
            start_price = float(start_price_val)
            end_price = float(end_price_val)
        except (TypeError, ValueError):
            return {}

        total_return = (
            ((end_price - start_price) / start_price) * 100
            if start_price > 0
            else None
        )

        try:
            avg_volume = (
                sum(v for v in volumes if v is not None)
                / len([v for v in volumes if v is not None])
                if volumes
                else 0.0
            )
        except (ZeroDivisionError, TypeError):
            avg_volume = 0.0

        if len(close_prices) > 1:
            pct_changes = []
            for i in range(1, len(close_prices)):
                if (
                    close_prices[i] is not None
                    and close_prices[i - 1] is not None
                    and close_prices[i - 1] != 0
                ):
                    pct_changes.append(
                        (
                            (close_prices[i] - close_prices[i - 1])
                            / close_prices[i - 1]
                        )
                        * 100
                    )

            if len(pct_changes) > 1:
                try:
                    volatility = statistics.stdev(pct_changes)
                except statistics.StatisticsError:
                    volatility = 0.0
            else:
                volatility = 0.0
        else:
            volatility = 0.0

        return {
            "ticker": self.ticker,
            "total_return": total_return,
            "start_price": start_price,
            "end_price": end_price,
            "avg_volume": avg_volume,
            "volatility": volatility,
            "days": len(period_df),
        }

    def filter_by_criteria(
        self, min_price: float = 0.20, min_volume: int = 50000
    ) -> bool:
        """
        Check if stock meets basic criteria.

        Args:
            min_price: Minimum closing price in AUD
            min_volume: Minimum average daily volume

        Returns:
            True if stock meets criteria
        """
        if self.df is None:
            return False

        latest_close = self.df["close"][-1]
        if len(self.df) >= 50:
            volume_mean = self.df["volume"].tail(50).mean()
            avg_volume = (
                float(volume_mean)
                if volume_mean is not None
                and isinstance(volume_mean, (int, float))
                else 0.0
            )
        else:
            volume_mean = self.df["volume"].mean()
            avg_volume = (
                float(volume_mean)
                if volume_mean is not None
                and isinstance(volume_mean, (int, float))
                else 0.0
            )

        return bool(latest_close >= min_price and avg_volume >= min_volume)
