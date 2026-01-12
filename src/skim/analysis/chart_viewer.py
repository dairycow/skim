"""
Terminal candlestick chart viewer using py-candlestick-chart.
"""

import polars as pl
from candlestick_chart import Candle, Chart
from rich.console import Console

from skim.analysis.date_parser import parse_date_range
from skim.analysis.stock_data import StockData


class ChartViewer:
    """Displays terminal candlestick charts for stocks."""

    def __init__(self, stocks: dict[str, StockData], console: Console):
        self.stocks = stocks
        self.console = console

    def show_chart(self, ticker: str, period: str | None = None) -> None:
        """
        Display terminal candlestick chart for a ticker.

        Args:
            ticker: Stock ticker symbol
            period: Optional time period (e.g., "2024", "2024-03", "1M", "3M")
                    If None, shows last 100 candles
        """
        ticker_upper = ticker.upper()

        if ticker_upper not in self.stocks:
            self.console.print(f"[red]Ticker {ticker_upper} not found in loaded data[/red]")
            return

        stock = self.stocks[ticker_upper]

        if stock.df is None:
            self.console.print(f"[red]No data available for {ticker_upper}[/red]")
            return

        df = stock.df

        if period:
            try:
                start_date, end_date = parse_date_range(period)
                self.console.print(f"[cyan]Loading chart for {ticker_upper}: {start_date.date()} to {end_date.date()}[/cyan]")
                df = df.filter((pl.col('date') >= start_date) & (pl.col('date') <= end_date))
            except ValueError as e:
                self.console.print(f"[red]Error parsing period: {e}[/red]")
                return
        else:
            self.console.print(f"[cyan]Loading chart for {ticker_upper} (last 100 candles)...[/cyan]")
            df = df.tail(100)

        if len(df) == 0:
            self.console.print(f"[yellow]No data found for {ticker_upper} in specified period[/yellow]")
            return

        try:
            candles = [
                Candle(
                    open=float(row['open']),
                    close=float(row['close']),
                    high=float(row['high']),
                    low=float(row['low']),
                    volume=float(row['volume'])
                )
                for row in df.iter_rows(named=True)
            ]

            chart = Chart(candles, title=f"{ticker_upper} OHLC")
            chart.set_name(f"ASX:{ticker_upper}")
            chart.set_bear_color(255, 107, 107)
            chart.set_bull_color(75, 199, 124)
            chart.set_volume_pane_enabled(True)
            chart.set_volume_pane_height(6)

            chart.draw()
        except Exception as e:
            self.console.print(f"[red]Error creating chart: {e}[/red]")
