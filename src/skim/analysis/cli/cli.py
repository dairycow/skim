"""
Interactive console interface for ASX stock analysis.
"""

import yfinance as yf
from rich.console import Console
from rich.panel import Panel

from skim.analysis.announcement_scraper import AnnouncementScraper
from skim.analysis.chart_viewer import ChartViewer
from skim.analysis.data_downloader import CoolTraderDownloader
from skim.analysis.data_loader import DataLoader
from skim.analysis.date_parser import parse_date_range
from skim.analysis.gap_scanner import GapScanner
from skim.analysis.momentum_scanner import MomentumScanner
from skim.analysis.performance import PerformanceCalculator


class CLI:
    """Interactive command-line interface."""

    def __init__(self):
        self.console = Console()
        self.loader: DataLoader
        self.calculator: PerformanceCalculator
        self.scanner: GapScanner
        self.momentum_scanner: MomentumScanner
        self.scraper = AnnouncementScraper()
        self.viewer: ChartViewer
        self.data_loaded = False

    def show_welcome(self):
        """Display welcome message."""
        welcome_text = """
        [bold cyan]ASX Swing Trading Study[/bold cyan]

        Commands:
        [yellow]top <period>[/yellow]      - Show top performers (e.g., 'top 2024', 'top 2024-03')
        [yellow]gaps <period>[/yellow]     - Show gaps (e.g., 'gaps 2024-06')
        [yellow]ann <ticker> <period>[/yellow] - Show announcements (e.g., 'ann BHP 2024')
        [yellow]chart <ticker> [period][/yellow] - Show terminal candlestick chart (e.g., 'chart BHP 2024')
        [yellow]momentum <period>[/yellow] - Show momentum bursts (e.g., 'momentum 2024-12')
        [yellow]consolidate <period>[/yellow] - Show consolidation patterns (e.g., 'consolidate 2024-12')
        [yellow]pattern <ticker> <period>[/yellow] - Show pattern analysis (e.g., 'pattern BHP 2024-12')
        [yellow]perf <ticker> <period>[/yellow] - Show stock performance (e.g., 'perf BHP 2024-12')
        [yellow]movestats <period>[/yellow] - Show move statistics (e.g., 'movestats 2024-12')
        [yellow]info <ticker>[/yellow]      - Show company info (e.g., 'info BHP')
        [yellow]help[/yellow]              - Show this help
        [yellow]quit[/yellow]              - Exit
        """
        self.console.print(
            Panel(
                welcome_text, title="[bold]Welcome[/bold]", border_style="cyan"
            )
        )

    def load_data(self):
        """Load stock data."""
        if self.data_loaded:
            self.console.print("[yellow]Data already loaded[/yellow]")
            return

        self.console.print("[cyan]Loading stock data...[/cyan]")
        self.loader = DataLoader()
        self.loader.load_all(min_price=0.20, min_volume=50000)

        self.calculator = PerformanceCalculator(self.loader.stocks)
        self.scanner = GapScanner(self.loader.stocks)
        self.momentum_scanner = MomentumScanner(self.loader.stocks)
        self.viewer = ChartViewer(self.loader.stocks, self.console)
        self.data_loaded = True

        self.console.print(
            f"[green]✓ Loaded {len(self.loader.stocks)} stocks[/green]"
        )

    def download_data(self, date_arg: str | None = None) -> None:
        """Download daily data from CoolTrader.

        Args:
            date_arg: Optional date specification (YYYYMMDD, today, yesterday).
                      Defaults to today.
        """
        self.console.print("[cyan]→ Downloading data from CoolTrader...[/cyan]")

        try:
            downloader = CoolTraderDownloader()

            if date_arg:
                path = downloader.download_for_date_str(date_arg)
            else:
                path = downloader.download_today()

            if path:
                self.console.print(f"[green]✓ Downloaded: {path}[/green]")

                self.console.print(
                    "[cyan]→ Processing downloaded data...[/cyan]"
                )
                count = downloader.process_downloads()
                self.console.print(
                    f"[green]✓ Processed {count} file(s)[/green]"
                )
            else:
                self.console.print(
                    "[yellow]![/yellow] No data available (file may not exist yet)"
                )

            downloader.close()

        except Exception as e:
            if "AuthError" in type(e).__name__ or "auth" in str(e).lower():
                self.console.print(f"[red]✗ Authentication failed: {e}[/red]")
            else:
                self.console.print(f"[red]✗ Download failed: {e}[/red]")

    def show_top_performers(self, period: str):
        """Show top performers for a period."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Finding top performers for {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        results = self.calculator.find_top_performers(
            start_date=start_date,
            end_date=end_date,
            limit=50,
            min_price=0.20,
            min_volume=50000,
        )

        self.calculator.display_top_performers(results, self.console)

    def show_gaps(self, period: str):
        """Show gaps for a period."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Scanning for gaps in {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        gaps = self.scanner.find_gaps(
            start_date=start_date,
            end_date=end_date,
            gap_threshold=10.0,
            volume_multiplier=2.0,
            min_volume=50000,
        )

        self.scanner.display_gaps(gaps, self.console)

    def show_announcements(self, ticker: str, period: str):
        """Show announcements for a ticker."""
        try:
            start_date, end_date = self.scraper.parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Fetching announcements for {ticker} in {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        announcements = self.scraper.get_announcements(
            ticker, start_date, end_date
        )
        self.scraper.display_announcements(announcements, self.console)

    def show_chart(self, ticker: str, period: str | None = None):
        """Show terminal candlestick chart for a ticker."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        self.viewer.show_chart(ticker, period)

    def show_momentum_bursts(self, period: str, min_days: int = 3):
        """Show momentum bursts for a period."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Finding momentum bursts for {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        bursts = self.momentum_scanner.find_all_momentum_bursts(
            start_date=start_date,
            end_date=end_date,
            min_days=min_days,
            limit=50,
        )

        self.momentum_scanner.display_momentum_bursts(bursts, self.console)

    def show_consolidations(
        self, period: str, max_range: float = 10.0, min_days: int = 5
    ):
        """Show consolidation patterns for a period."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Finding consolidations for {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        consolidations = self.momentum_scanner.find_all_consolidations(
            start_date=start_date,
            end_date=end_date,
            max_range_pct=max_range,
            min_days=min_days,
            limit=50,
        )

        self.momentum_scanner.display_consolidations(
            consolidations, self.console
        )

    def show_pattern_analysis(self, ticker: str, period: str):
        """Show pattern analysis for a specific stock."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Analyzing patterns for {ticker} in {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        patterns = self.momentum_scanner.analyze_stock_patterns(
            ticker, start_date, end_date
        )

        self.console.print(
            f"[bold]Pattern Analysis for {ticker} ({period})[/bold]\n"
        )
        self.console.print(
            f"[cyan]Momentum Bursts:[/cyan] {patterns.get('total_momentum_bursts', 0)}"
        )
        if patterns.get("momentum_bursts"):
            self.momentum_scanner.display_momentum_bursts(
                patterns["momentum_bursts"], self.console
            )
        self.console.print(
            f"\n[cyan]Consolidations:[/cyan] {patterns.get('total_consolidations', 0)}"
        )
        if patterns.get("consolidations"):
            self.momentum_scanner.display_consolidations(
                patterns["consolidations"], self.console
            )

    def show_performance(self, ticker: str, period: str):
        """Show performance metrics for a specific stock."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        if ticker.upper() not in self.loader.stocks:
            self.console.print(
                f"[red]Stock {ticker.upper()} not found in loaded data[/red]"
            )
            return

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Calculating performance for {ticker.upper()} in {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        stock = self.loader.stocks[ticker.upper()]
        metrics = stock.calculate_returns_over_period(start_date, end_date)

        if not metrics:
            self.console.print(
                f"[yellow]No data available for {ticker.upper()} in the specified period[/yellow]"
            )
            return

        from rich.table import Table

        table = Table(title=f"Performance: {ticker.upper()} ({period})")
        table.add_column("Metric", style="cyan", width=15)
        table.add_column("Value", style="white", width=20)

        table.add_row(
            "Return %",
            f"{metrics['total_return']:.2f}%"
            if metrics["total_return"] is not None
            else "N/A",
        )
        table.add_row(
            "Start Price",
            f"${metrics['start_price']:.3f}"
            if metrics["start_price"]
            else "N/A",
        )
        table.add_row(
            "End Price",
            f"${metrics['end_price']:.3f}" if metrics["end_price"] else "N/A",
        )
        table.add_row(
            "Avg Volume",
            f"{metrics['avg_volume']:,.0f}" if metrics["avg_volume"] else "N/A",
        )
        table.add_row(
            "Volatility %",
            f"{metrics['volatility']:.2f}%" if metrics["volatility"] else "N/A",
        )
        table.add_row(
            "Days", f"{metrics['days']}" if metrics.get("days") else "N/A"
        )

        self.console.print(table)

    def show_move_statistics(self, period: str):
        """Show move duration statistics."""
        if not self.data_loaded:
            self.console.print(
                "[red]Please load data first using 'load' command[/red]"
            )
            return

        try:
            start_date, end_date = parse_date_range(period)
        except ValueError as e:
            self.console.print(f"[red]Error parsing period: {e}[/red]")
            return

        self.console.print(
            f"[cyan]Calculating move statistics for {period} ({start_date.date()} to {end_date.date()})...[/cyan]"
        )

        stats = self.momentum_scanner.get_move_statistics(start_date, end_date)
        self.momentum_scanner.display_move_statistics(stats, self.console)

    def show_company_info(self, ticker: str):
        """Show company information using yfinance."""
        ticker = ticker.upper()
        yahoo_ticker = f"{ticker}.AX"

        self.console.print(
            f"[cyan]Fetching company info for {ticker}...[/cyan]"
        )

        try:
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            if not info or "longName" not in info:
                self.console.print(
                    f"[red]Ticker {ticker} not found or no data available[/red]"
                )
                return

            name = info.get("longName", "N/A")
            sector = info.get("sector", "N/A")
            industry = info.get("industry", "N/A")
            market_cap = info.get("marketCap", None)
            summary = info.get("longBusinessSummary", "N/A")

            if market_cap is not None:
                if market_cap >= 1e9:
                    market_cap_str = f"${market_cap / 1e9:.2f}B"
                elif market_cap >= 1e6:
                    market_cap_str = f"${market_cap / 1e6:.2f}M"
                else:
                    market_cap_str = f"${market_cap:,.0f}"
            else:
                market_cap_str = "N/A"

            if summary and summary != "N/A":
                first_period = summary.split(".")[0] + "."
            else:
                first_period = "N/A"

            from rich.table import Table

            table = Table(title=f"Company Info: {ticker}")
            table.add_column("Field", style="cyan", width=20)
            table.add_column("Value", style="white", width=50)

            table.add_row("Company Name", name)
            table.add_row("Sector", sector)
            table.add_row("Industry", industry)
            table.add_row("Market Cap", market_cap_str)
            table.add_row(
                "Business Summary",
                first_period[:200] + "..."
                if len(first_period) > 200
                else first_period,
            )

            self.console.print(table)

        except Exception as e:
            self.console.print(
                f"[red]Error fetching info for {ticker}: {e}[/red]"
            )

    def show_help(self):
        """Show help information."""
        help_text = """
        [bold]Commands:[/bold]

        [cyan]download [date][/cyan]
            Download daily data from CoolTrader.
            Examples: download, download 20260102, download yesterday

        [cyan]top <period>[/cyan]
            Show top performing stocks for a period.
            Examples: top 2024, top 2024-03, top 2024-03-01 to 2024-03-31, top 1M

        [cyan]gaps <period>[/cyan]
            Show significant gaps (10%+) for a period.
            Examples: gaps 2024, gaps 2024-06

        [cyan]ann <ticker> <period>[/cyan]
            Show announcements for a ticker.
            Examples: ann BHP 2024, ann CBA 2024-06, ann TLS 2024-01-01 to 2024-03-31, ann WOW 3M

        [cyan]chart <ticker> [period][/cyan]
            Show terminal candlestick chart for a ticker.
            Optional period: YYYY, YYYY-MM, YYYY-MM-DD to YYYY-MM-DD, 1M, 3M, 6M, 1Y
            Examples: chart BHP, chart BHP 2024, chart BHP 2024-03, chart CBA 3M

        [cyan]momentum <period>[/cyan]
            Show momentum bursts (3+ consecutive up days) for a period.
            Examples: momentum 2024, momentum 2024-12, momentum 3M

        [cyan]consolidate <period>[/cyan]
            Show consolidation patterns (flat price + low volume) for a period.
            Examples: consolidate 2024, consolidate 2024-12, consolidate 6M

        [cyan]pattern <ticker> <period>[/cyan]
            Show pattern analysis (momentum + consolidation) for a specific stock.
            Examples: pattern BHP 2024, pattern CBA 2024-12, pattern TLS 2024-03

        [cyan]perf <ticker> <period>[/cyan]
            Show performance metrics for a specific stock.
            Examples: perf BHP 2024, perf CBA 2024-12, perf TLS 3M

        [cyan]movestats <period>[/cyan]
            Show move duration statistics across all stocks.
            Examples: movestats 2024, movestats 2024-12

        [cyan]info <ticker>[/cyan]
            Show company information (name, sector, market cap, description).
            Works independently without loading data.
            Examples: info BHP, info CBA, info TLS

        [cyan]help[/cyan]
            Show this help message.

        [cyan]quit[/cyan]
            Exit program.
        """
        self.console.print(
            Panel(help_text, title="[bold]Help[/bold]", border_style="yellow")
        )

    def run(self):
        """Run interactive console."""
        self.show_welcome()
        self.load_data()

        try:
            while True:
                try:
                    command = input("> ").strip()

                    if not command:
                        continue

                    parts = command.split()
                    cmd = parts[0].lower()

                    if cmd == "quit" or cmd == "exit" or cmd == "q":
                        self.console.print("[yellow]Goodbye![/yellow]")
                        break

                    elif cmd == "load":
                        self.load_data()

                    elif cmd == "download":
                        date_arg = parts[1] if len(parts) > 1 else None
                        self.download_data(date_arg)

                    elif cmd == "top":
                        if len(parts) < 2:
                            self.console.print("[red]Usage: top <period>[/red]")
                            continue
                        self.show_top_performers(" ".join(parts[1:]))

                    elif cmd == "gaps":
                        if len(parts) < 2:
                            self.console.print(
                                "[red]Usage: gaps <period>[/red]"
                            )
                            continue
                        self.show_gaps(" ".join(parts[1:]))

                    elif cmd == "ann":
                        if len(parts) < 3:
                            self.console.print(
                                "[red]Usage: ann <ticker> <period>[/red]"
                            )
                            continue
                        ticker = parts[1]
                        period = " ".join(parts[2:])
                        self.show_announcements(ticker, period)

                    elif cmd == "chart":
                        if len(parts) < 2:
                            self.console.print(
                                "[red]Usage: chart <ticker> [period][/red]"
                            )
                            continue
                        ticker = parts[1]
                        period = " ".join(parts[2:]) if len(parts) > 2 else None
                        self.show_chart(ticker, period)

                    elif cmd == "momentum":
                        if len(parts) < 2:
                            self.console.print(
                                "[red]Usage: momentum <period>[/red]"
                            )
                            continue
                        period = " ".join(parts[1:])
                        self.show_momentum_bursts(period)

                    elif cmd == "consolidate":
                        if len(parts) < 2:
                            self.console.print(
                                "[red]Usage: consolidate <period>[/red]"
                            )
                            continue
                        period = " ".join(parts[1:])
                        self.show_consolidations(period)

                    elif cmd == "pattern":
                        if len(parts) < 3:
                            self.console.print(
                                "[red]Usage: pattern <ticker> <period>[/red]"
                            )
                            continue
                        ticker = parts[1]
                        period = " ".join(parts[2:])
                        self.show_pattern_analysis(ticker, period)

                    elif cmd == "perf":
                        if len(parts) < 3:
                            self.console.print(
                                "[red]Usage: perf <ticker> <period>[/red]"
                            )
                            continue
                        ticker = parts[1]
                        period = " ".join(parts[2:])
                        self.show_performance(ticker, period)

                    elif cmd == "movestats":
                        if len(parts) < 2:
                            self.console.print(
                                "[red]Usage: movestats <period>[/red]"
                            )
                            continue
                        period = " ".join(parts[1:])
                        self.show_move_statistics(period)

                    elif cmd == "info":
                        if len(parts) < 2:
                            self.console.print(
                                "[red]Usage: info <ticker>[/red]"
                            )
                            continue
                        ticker = parts[1]
                        self.show_company_info(ticker)

                    elif cmd == "help" or cmd == "h":
                        self.show_help()

                    else:
                        self.console.print(f"[red]Unknown command: {cmd}[/red]")
                        self.console.print(
                            "[yellow]Type 'help' for available commands[/yellow]"
                        )

                except KeyboardInterrupt:
                    self.console.print(
                        "\n[yellow]Interrupted. Type 'quit' to exit.[/yellow]"
                    )
                except EOFError:
                    break
                except Exception as e:
                    self.console.print(f"[red]Error: {e}[/red]")
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Goodbye![/yellow]")


def main():
    """Main entry point."""
    cli = CLI()
    cli.run()


if __name__ == "__main__":
    main()
