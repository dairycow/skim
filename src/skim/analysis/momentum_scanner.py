"""
Momentum and consolidation pattern detection for ASX stocks.
"""

import statistics
from datetime import datetime

import polars as pl
from rich.console import Console
from rich.table import Table

from skim.analysis.stock_data import StockData


class MomentumScanner:
    """Detects momentum bursts and consolidation patterns in stock price data."""

    def __init__(self, stocks: dict[str, StockData]):
        self.stocks = stocks

    def detect_momentum_bursts(
        self,
        stock: StockData,
        min_days: int = 3,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """
        Detect momentum bursts (3+ consecutive up days) for a stock.

        Args:
            stock: StockData object
            min_days: Minimum consecutive up days (default: 3)
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            List of momentum burst dictionaries
        """
        if stock.df is None:
            return []

        df = stock.df
        if start_date and end_date:
            df = df.filter(
                (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
            )

        bursts = []
        consecutive_up = 0
        burst_start_idx = None

        close_prices = df["close"].to_list()
        volumes = df["volume"].to_list()
        dates = df["date"].to_list()

        for i in range(1, len(close_prices)):
            if close_prices[i] is None or close_prices[i - 1] is None:
                if consecutive_up >= min_days and burst_start_idx is not None:
                    end_idx = i - 1
                    self._add_momentum_burst(
                        bursts,
                        stock,
                        dates,
                        close_prices,
                        volumes,
                        burst_start_idx,
                        end_idx,
                        consecutive_up,
                    )
                consecutive_up = 0
                burst_start_idx = None
                continue

            if close_prices[i] > close_prices[i - 1]:
                consecutive_up += 1
                if burst_start_idx is None:
                    burst_start_idx = i - 1
            else:
                if consecutive_up >= min_days and burst_start_idx is not None:
                    end_idx = i - 1
                    self._add_momentum_burst(
                        bursts,
                        stock,
                        dates,
                        close_prices,
                        volumes,
                        burst_start_idx,
                        end_idx,
                        consecutive_up,
                    )
                consecutive_up = 0
                burst_start_idx = None

        if consecutive_up >= min_days and burst_start_idx is not None:
            end_idx = len(close_prices) - 1
            self._add_momentum_burst(
                bursts,
                stock,
                dates,
                close_prices,
                volumes,
                burst_start_idx,
                end_idx,
                consecutive_up,
            )

        return bursts

    def _add_momentum_burst(
        self,
        bursts: list[dict],
        stock: StockData,
        dates: list,
        close_prices: list,
        volumes: list,
        start_idx: int,
        end_idx: int,
        consecutive_up: int,
    ) -> None:
        """Helper method to add a momentum burst to the list."""
        if close_prices[start_idx] is None or close_prices[end_idx] is None:
            return

        start_price = close_prices[start_idx]
        end_price = close_prices[end_idx]
        total_gain = ((end_price - start_price) / start_price) * 100

        avg_volume = sum(
            v for v in volumes[start_idx : end_idx + 1] if v is not None
        ) / (end_idx - start_idx + 1)
        baseline_start = max(0, start_idx - 50)
        baseline_count = start_idx - baseline_start
        baseline_volume = (
            sum(v for v in volumes[baseline_start:start_idx] if v is not None)
            / baseline_count
            if baseline_count > 0
            else avg_volume
        )
        volume_multiple = (
            avg_volume / baseline_volume if baseline_volume > 0 else 1.0
        )

        daily_gains = []
        for j in range(start_idx + 1, end_idx + 1):
            if (
                close_prices[j - 1] is not None
                and close_prices[j] is not None
                and close_prices[j - 1] > 0
            ):
                daily_gains.append(
                    (
                        (close_prices[j] - close_prices[j - 1])
                        / close_prices[j - 1]
                    )
                    * 100
                )

        bursts.append(
            {
                "ticker": stock.ticker,
                "pattern_type": "momentum_burst",
                "start_date": dates[start_idx],
                "end_date": dates[end_idx],
                "duration_days": consecutive_up,
                "consecutive_up_days": consecutive_up,
                "start_price": float(start_price),
                "end_price": float(end_price),
                "total_gain_pct": total_gain,
                "daily_gains": daily_gains,
                "avg_volume": int(avg_volume),
                "volume_spike_multiple": round(volume_multiple, 2),
            }
        )

    def detect_consolidation(
        self,
        stock: StockData,
        max_range_pct: float = 10.0,
        min_days: int = 5,
        volume_threshold: float = 0.5,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict]:
        """
        Detect consolidation patterns (flat price + low volume) for a stock.

        Args:
            stock: StockData object
            max_range_pct: Maximum price range percentage (default: 10%)
            min_days: Minimum consolidation duration (default: 5 days)
            volume_threshold: Volume ratio threshold (default: 0.5 = 50% of baseline)
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            List of consolidation dictionaries
        """
        if stock.df is None:
            return []

        df = stock.df
        if start_date and end_date:
            df = df.filter(
                (pl.col("date") >= start_date) & (pl.col("date") <= end_date)
            )

        consolidations = []
        close_prices = df["close"].to_list()
        volumes = df["volume"].to_list()
        dates = df["date"].to_list()
        highs = df["high"].to_list()
        lows = df["low"].to_list()

        window_size = min_days
        for i in range(len(close_prices) - window_size + 1):
            window_end = min(i + window_size, len(close_prices))

            max_price = max(highs[i:window_end])
            min_price = min(lows[i:window_end])
            avg_price = (max_price + min_price) / 2

            price_range_pct = ((max_price - min_price) / avg_price) * 100

            if price_range_pct <= max_range_pct:
                avg_volume = sum(volumes[i:window_end]) / (window_end - i)
                baseline_volume = (
                    sum(volumes[max(0, i - 50) : i]) / min(50, i)
                    if i > 0
                    else avg_volume
                )
                volume_ratio = (
                    avg_volume / baseline_volume if baseline_volume > 0 else 1.0
                )

                if volume_ratio <= volume_threshold:
                    volume_decline_pct = (
                        ((baseline_volume - avg_volume) / baseline_volume) * 100
                        if baseline_volume > 0
                        else 0
                    )

                    consolidations.append(
                        {
                            "ticker": stock.ticker,
                            "pattern_type": "consolidation",
                            "start_date": dates[i],
                            "end_date": dates[window_end - 1],
                            "duration_days": window_end - i,
                            "price_range_pct": round(price_range_pct, 2),
                            "start_price": float(close_prices[i]),
                            "end_price": float(close_prices[window_end - 1]),
                            "high": float(max_price),
                            "low": float(min_price),
                            "avg_volume": int(avg_volume),
                            "volume_decline_pct": round(volume_decline_pct, 2),
                            "volume_ratio_to_avg": round(volume_ratio, 2),
                        }
                    )

        return consolidations

    def analyze_stock_patterns(
        self,
        ticker: str,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> dict:
        """
        Analyze all patterns for a specific stock.

        Args:
            ticker: Stock ticker symbol
            start_date: Start date for analysis (optional)
            end_date: End date for analysis (optional)

        Returns:
            Dictionary with all detected patterns
        """
        if ticker not in self.stocks:
            return {"ticker": ticker, "error": "Stock not found"}

        stock = self.stocks[ticker]
        momentum_bursts = self.detect_momentum_bursts(
            stock, start_date=start_date, end_date=end_date
        )
        consolidations = self.detect_consolidation(
            stock, start_date=start_date, end_date=end_date
        )

        return {
            "ticker": ticker,
            "momentum_bursts": momentum_bursts,
            "consolidations": consolidations,
            "total_momentum_bursts": len(momentum_bursts),
            "total_consolidations": len(consolidations),
        }

    def find_all_momentum_bursts(
        self,
        start_date: datetime,
        end_date: datetime,
        min_days: int = 3,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all momentum bursts across all stocks.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            min_days: Minimum consecutive up days (default: 3)
            limit: Maximum number of results

        Returns:
            List of all momentum bursts
        """
        all_bursts = []

        for _ticker, stock in self.stocks.items():
            bursts = self.detect_momentum_bursts(
                stock,
                min_days=min_days,
                start_date=start_date,
                end_date=end_date,
            )
            all_bursts.extend(bursts)

        all_bursts.sort(key=lambda x: x["total_gain_pct"], reverse=True)
        return all_bursts[:limit]

    def find_all_consolidations(
        self,
        start_date: datetime,
        end_date: datetime,
        max_range_pct: float = 10.0,
        min_days: int = 5,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all consolidations across all stocks.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis
            max_range_pct: Maximum price range percentage (default: 10%)
            min_days: Minimum consolidation duration (default: 5 days)
            limit: Maximum number of results

        Returns:
            List of all consolidations
        """
        all_consolidations = []

        for _ticker, stock in self.stocks.items():
            consolidations = self.detect_consolidation(
                stock,
                max_range_pct=max_range_pct,
                min_days=min_days,
                start_date=start_date,
                end_date=end_date,
            )
            all_consolidations.extend(consolidations)

        all_consolidations.sort(key=lambda x: x["duration_days"], reverse=True)
        return all_consolidations[:limit]

    def get_move_statistics(
        self, start_date: datetime, end_date: datetime
    ) -> dict:
        """
        Calculate move duration statistics across all stocks.

        Args:
            start_date: Start date for analysis
            end_date: End date for analysis

        Returns:
            Dictionary with statistical summaries
        """
        all_bursts = self.find_all_momentum_bursts(
            start_date, end_date, limit=1000
        )
        all_consolidations = self.find_all_consolidations(
            start_date, end_date, limit=1000
        )

        momentum_durations = [b["duration_days"] for b in all_bursts]
        momentum_gains = [b["total_gain_pct"] for b in all_bursts]

        consolidation_durations = [
            c["duration_days"] for c in all_consolidations
        ]
        consolidation_ranges = [
            c["price_range_pct"] for c in all_consolidations
        ]

        def analyze_distribution(values: list[int], bins: list[int]) -> dict:
            """Create distribution bins."""
            distribution = {}
            for value in values:
                for i, bin_threshold in enumerate(bins):
                    if value <= bin_threshold:
                        bin_label = (
                            f"{bins[i - 1] + 1}_days"
                            if i > 0
                            else f"1-{bins[0]}_days"
                        )
                        if i == len(bins) - 1:
                            bin_label = (
                                f"{bins[i - 1] + 1}+_days"
                                if i > 0
                                else f"{bins[0]}+_days"
                            )
                        distribution[bin_label] = (
                            distribution.get(bin_label, 0) + 1
                        )
                        break
                else:
                    bin_label = f"{bins[-1] + 1}+_days"
                    distribution[bin_label] = distribution.get(bin_label, 0) + 1
            return distribution

        momentum_dist = analyze_distribution(momentum_durations, [3, 4, 5, 10])
        consolidation_dist = analyze_distribution(
            consolidation_durations, [5, 10, 15]
        )

        return {
            "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
            "total_stocks": len(self.stocks),
            "momentum_bursts": {
                "total_count": len(all_bursts),
                "avg_duration_days": round(
                    statistics.mean(momentum_durations), 2
                )
                if momentum_durations
                else 0,
                "median_duration_days": round(
                    statistics.median(momentum_durations), 2
                )
                if momentum_durations
                else 0,
                "max_duration_days": max(momentum_durations)
                if momentum_durations
                else 0,
                "min_duration_days": min(momentum_durations)
                if momentum_durations
                else 0,
                "total_gain_avg_pct": round(statistics.mean(momentum_gains), 2)
                if momentum_gains
                else 0,
                "duration_distribution": momentum_dist,
            },
            "consolidation": {
                "total_count": len(all_consolidations),
                "avg_duration_days": round(
                    statistics.mean(consolidation_durations), 2
                )
                if consolidation_durations
                else 0,
                "median_duration_days": round(
                    statistics.median(consolidation_durations), 2
                )
                if consolidation_durations
                else 0,
                "max_duration_days": max(consolidation_durations)
                if consolidation_durations
                else 0,
                "min_duration_days": min(consolidation_durations)
                if consolidation_durations
                else 0,
                "avg_price_range_pct": round(
                    statistics.mean(consolidation_ranges), 2
                )
                if consolidation_ranges
                else 0,
                "duration_distribution": consolidation_dist,
            },
        }

    def display_momentum_bursts(
        self, bursts: list[dict], console: Console
    ) -> None:
        """Display momentum bursts in a formatted table."""
        if not bursts:
            console.print("[yellow]No momentum bursts found[/yellow]")
            return

        table = Table(title="Momentum Bursts")
        table.add_column("Ticker", style="cyan", width=8)
        table.add_column("Start", width=12)
        table.add_column("End", width=12)
        table.add_column("Days", style="green", width=6)
        table.add_column("Gain %", style="green", width=10)
        table.add_column("Start $", width=10)
        table.add_column("End $", width=10)
        table.add_column("Vol Multiple", width=12)

        for b in bursts:
            table.add_row(
                b["ticker"],
                b["start_date"].strftime("%Y-%m-%d"),
                b["end_date"].strftime("%Y-%m-%d"),
                str(b["duration_days"]),
                f"{b['total_gain_pct']:.2f}",
                f"{b['start_price']:.3f}",
                f"{b['end_price']:.3f}",
                f"{b['volume_spike_multiple']:.2f}x",
            )

        console.print(table)

    def display_consolidations(
        self, consolidations: list[dict], console: Console
    ) -> None:
        """Display consolidations in a formatted table."""
        if not consolidations:
            console.print("[yellow]No consolidations found[/yellow]")
            return

        table = Table(title="Consolidation Patterns")
        table.add_column("Ticker", style="cyan", width=8)
        table.add_column("Start", width=12)
        table.add_column("End", width=12)
        table.add_column("Days", style="yellow", width=6)
        table.add_column("Range %", width=10)
        table.add_column("Low $", width=10)
        table.add_column("High $", width=10)
        table.add_column("Vol Ratio", width=10)

        for c in consolidations:
            table.add_row(
                c["ticker"],
                c["start_date"].strftime("%Y-%m-%d"),
                c["end_date"].strftime("%Y-%m-%d"),
                str(c["duration_days"]),
                f"{c['price_range_pct']:.2f}",
                f"{c['low']:.3f}",
                f"{c['high']:.3f}",
                f"{c['volume_ratio_to_avg']:.2f}x",
            )

        console.print(table)

    def display_move_statistics(self, stats: dict, console: Console) -> None:
        """Display move statistics summary."""
        table = Table(title="Move Duration Statistics")
        table.add_column("Metric", style="cyan", width=25)
        table.add_column("Momentum Bursts", width=20)
        table.add_column("Consolidation", width=20)

        m = stats["momentum_bursts"]
        c = stats["consolidation"]

        table.add_row(
            "Total Count", str(m["total_count"]), str(c["total_count"])
        )
        table.add_row(
            "Avg Duration (days)",
            str(m["avg_duration_days"]),
            str(c["avg_duration_days"]),
        )
        table.add_row(
            "Median Duration (days)",
            str(m["median_duration_days"]),
            str(c["median_duration_days"]),
        )
        table.add_row(
            "Max Duration (days)",
            str(m["max_duration_days"]),
            str(c["max_duration_days"]),
        )
        table.add_row(
            "Min Duration (days)",
            str(m["min_duration_days"]),
            str(c["min_duration_days"]),
        )

        if m.get("total_gain_avg_pct"):
            table.add_row(
                "Avg Gain/Range %",
                f"{m['total_gain_avg_pct']:.2f}",
                f"{c['avg_price_range_pct']:.2f}",
            )
        else:
            table.add_row(
                "Avg Gain/Range %", "N/A", f"{c['avg_price_range_pct']:.2f}"
            )

        console.print(table)

        console.print("\n[bold]Momentum Duration Distribution:[/bold]")
        dist_table = Table()
        dist_table.add_column("Duration", style="cyan")
        dist_table.add_column("Count", style="green")
        for duration, count in m["duration_distribution"].items():
            dist_table.add_row(duration.replace("_", " "), str(count))
        console.print(dist_table)

        console.print("\n[bold]Consolidation Duration Distribution:[/bold]")
        dist_table2 = Table()
        dist_table2.add_column("Duration", style="cyan")
        dist_table2.add_column("Count", style="green")
        for duration, count in c["duration_distribution"].items():
            dist_table2.add_row(duration.replace("_", " "), str(count))
        console.print(dist_table2)
