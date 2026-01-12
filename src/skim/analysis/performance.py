"""
Performance calculation utilities for ranking stocks.
"""

from datetime import datetime

from rich.console import Console
from rich.table import Table

from skim.analysis.stock_data import StockData


class PerformanceCalculator:
    """Calculates and ranks stock performance over time periods."""

    def __init__(self, stocks: dict[str, StockData]):
        self.stocks = stocks

    def find_top_performers(
        self,
        start_date: datetime,
        end_date: datetime,
        limit: int = 20,
        min_price: float = 0.20,
        min_volume: int = 50000,
    ) -> list[dict]:
        """
        Find top performing stocks over a period.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            limit: Maximum number of results
            min_price: Minimum price filter
            min_volume: Minimum volume filter

        Returns:
            List of dictionaries with performance data
        """
        results = []

        for _ticker, stock in self.stocks.items():
            metrics = stock.calculate_returns_over_period(start_date, end_date)

            if (
                metrics
                and metrics.get("total_return") is not None
                and metrics["start_price"] >= min_price
                and metrics["avg_volume"] >= min_volume
            ):
                results.append(metrics)

        results.sort(key=lambda x: x["total_return"], reverse=True)
        return results[:limit]

    def display_top_performers(
        self, results: list[dict], console: Console
    ) -> None:
        """Display top performers in a formatted table."""
        if not results:
            console.print("[yellow]No results found[/yellow]")
            return

        table = Table(title="Top Performers")
        table.add_column("Ticker", style="cyan", width=10)
        table.add_column("Return %", style="green", width=10)
        table.add_column("Start Price", width=12)
        table.add_column("End Price", width=12)
        table.add_column("Avg Volume", width=12)
        table.add_column("Volatility %", width=12)

        for r in results:
            table.add_row(
                r["ticker"],
                f"{r['total_return']:.2f}" if r["total_return"] else "N/A",
                f"{r['start_price']:.3f}" if r["start_price"] else "N/A",
                f"{r['end_price']:.3f}" if r["end_price"] else "N/A",
                f"{r['avg_volume']:,.0f}" if r["avg_volume"] else "N/A",
                f"{r['volatility']:.2f}" if r["volatility"] else "N/A",
            )

        console.print(table)
