"""
Gap detection scanner for identifying significant price gaps.
"""

import polars as pl
from rich.console import Console
from rich.table import Table

from skim.analysis.stock_data import StockData


class GapScanner:
    """Scans for significant price gaps in stock data."""

    def __init__(self, stocks: dict[str, StockData]):
        self.stocks = stocks

    def find_gaps(
        self,
        start_date,
        end_date,
        gap_threshold: float = 10.0,
        volume_multiplier: float = 2.0,
        min_volume: int = 50000,
    ) -> list[dict]:
        """
        Find gaps over a period.

        Args:
            start_date: Start date for scanning
            end_date: End date for scanning
            gap_threshold: Minimum gap percentage (default 10%)
            volume_multiplier: Minimum volume multiple vs 50-day avg (default 2x)
            min_volume: Minimum daily volume (default 50k)

        Returns:
            List of gap dictionaries with details
        """
        gaps = []

        for _ticker, stock in self.stocks.items():
            stock_gaps = self._find_gaps_in_stock(
                stock,
                start_date,
                end_date,
                gap_threshold,
                volume_multiplier,
                min_volume,
            )
            gaps.extend(stock_gaps)

        gaps.sort(key=lambda x: x["gap_percent"], reverse=True)
        return gaps

    def _find_gaps_in_stock(
        self,
        stock: StockData,
        start_date,
        end_date,
        gap_threshold: float,
        volume_multiplier: float,
        min_volume: int,
    ) -> list[dict]:
        """Find gaps in a single stock."""
        gaps = []

        if stock.df is None:
            return gaps

        period_df = stock.df.filter(
            (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
        )

        if len(period_df) < 2:
            return gaps

        for i in range(1, len(period_df)):
            current = period_df.row(i, named=True)
            previous = period_df.row(i - 1, named=True)

            gap = (
                (current["open"] - previous["close"]) / previous["close"] * 100
            )

            if gap >= gap_threshold:
                filtered_df = stock.df.filter(pl.col("date") < current["date"])
                if len(filtered_df) >= 50:
                    volume_mean = filtered_df["volume"].tail(50).mean()
                    avg_volume = (
                        float(volume_mean)
                        if volume_mean is not None
                        and isinstance(volume_mean, (int, float))
                        else 0.0
                    )
                else:
                    avg_volume = 0.0

                if avg_volume > 0:
                    vol_multiple = current["volume"] / avg_volume
                else:
                    vol_multiple = 0

                if (
                    current["volume"] >= min_volume
                    and vol_multiple >= volume_multiplier
                ):
                    gaps.append(
                        {
                            "ticker": stock.ticker,
                            "date": current["date"],
                            "gap_percent": gap,
                            "open": current["open"],
                            "prev_close": previous["close"],
                            "high": current["high"],
                            "low": current["low"],
                            "close": current["close"],
                            "volume": current["volume"],
                            "avg_volume_50d": avg_volume,
                            "volume_multiple": vol_multiple,
                        }
                    )

        return gaps

    def display_gaps(self, gaps: list[dict], console: Console) -> None:
        """Display gaps in a formatted table."""
        if not gaps:
            console.print("[yellow]No gaps found[/yellow]")
            return

        table = Table(title=f"Significant Gaps (showing top {len(gaps)})")
        table.add_column("Ticker", style="cyan", width=8)
        table.add_column("Date", style="yellow", width=12)
        table.add_column("Gap %", style="green", width=8)
        table.add_column("Open", width=8)
        table.add_column("Close", width=8)
        table.add_column("Vol", width=10)
        table.add_column("Vol x50d", width=8)

        for g in gaps[:50]:
            table.add_row(
                g["ticker"],
                g["date"].strftime("%Y-%m-%d"),
                f"{g['gap_percent']:.2f}%",
                f"{g['open']:.3f}",
                f"{g['close']:.3f}",
                f"{g['volume']:,.0f}",
                f"{g['volume_multiple']:.1f}x",
            )

        console.print(table)
