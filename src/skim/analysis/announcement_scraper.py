"""
Announcement scraper for ASX company announcements.
"""

from datetime import datetime

import requests
from bs4 import BeautifulSoup
from rich.console import Console
from rich.table import Table

ASX_BASE_URL = "https://www.asx.com.au"


def normalize_date(date_str: str) -> str:
    """Convert date from DD/MM/YYYY format to YYYYMMDD."""
    if not date_str or "/" not in date_str:
        return ""

    try:
        day, month, year = date_str.strip().split("/")
        return f"{year}{month.zfill(2)}{day.zfill(2)}"
    except ValueError:
        return ""


def normalize_time(time_str: str) -> str:
    """Convert to 24-hour format."""
    try:
        if "pm" in time_str:
            hour, minute = time_str.replace(" pm", "").split(":")
            hour = int(hour)
            if hour != 12:
                hour += 12
        else:
            hour, minute = time_str.replace(" am", "").split(":")
            hour = int(hour)
            if hour == 12:
                hour = 0
        return f"{hour:02d}{minute}"
    except Exception:
        return "0000"


def extract_page_count(cell) -> int:
    """Extract page count from PDF link cell."""
    page_span = cell.find("span", class_="page")
    page_text = page_span.get_text().strip()
    page_number = page_text.split()[0]
    return int(page_number)


def parse_row(cells) -> dict | None:
    """Extract announcement details from table row."""
    pdf_href = cells[2].find("a").get("href")

    if not pdf_href:
        return None

    return {
        "date": normalize_date(cells[0].get_text().split("\n")[1].strip()),
        "time": normalize_time(cells[0].get_text().split("\n")[2].strip()),
        "headline": cells[2].get_text().split("\n")[2].strip(),
        "price_sensitive": bool(cells[1].find("img", class_="pricesens")),
        "pages": extract_page_count(cells[2]),
    }


def scrape_announcements_for_year(ticker: str, year: int) -> list[dict]:
    """Scrape announcements for a given ticker and year."""
    url = f"{ASX_BASE_URL}/asx/v2/statistics/announcements.do?by=asxCode&asxCode={ticker}&timeframe=Y&year={year}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select("#content > div > announcement_data > table")

        if not table:
            return []

        announcements = table[0].select("tr")[1:]
        results = []

        for row in announcements:
            cells = row.select("td")
            if len(cells) < 3:
                continue

            announcement = parse_row(cells)
            if announcement and announcement["date"]:
                results.append(announcement)

        return results
    except Exception:
        return []


def filter_announcements_by_date_range(
    announcements: list[dict], start_date: datetime, end_date: datetime
) -> list[dict]:
    """Filter announcements to only those within the date range."""
    start_date_str = start_date.strftime("%Y%m%d")
    end_date_str = end_date.strftime("%Y%m%d")

    return [
        ann
        for ann in announcements
        if start_date_str <= ann["date"] <= end_date_str
    ]


class AnnouncementScraper:
    """Scrapes and displays ASX company announcements."""

    def get_announcements(
        self, ticker: str, start_date: datetime, end_date: datetime
    ) -> list[dict]:
        """
        Get announcements for a ticker within date range.

        Args:
            ticker: ASX ticker symbol
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of announcement dictionaries with date, time, headline, price_sensitive, pages
        """
        ticker = ticker.upper()
        results = []

        start_year = start_date.year
        end_year = end_date.year

        for year in range(start_year, end_year + 1):
            year_announcements = scrape_announcements_for_year(ticker, year)
            results.extend(year_announcements)

        filtered_results = filter_announcements_by_date_range(
            results, start_date, end_date
        )
        filtered_results.sort(key=lambda x: x["date"], reverse=True)

        return filtered_results

    def display_announcements(
        self, announcements: list[dict], console: Console
    ) -> None:
        """Display announcements in a formatted table."""
        if not announcements:
            console.print("[yellow]No announcements found[/yellow]")
            return

        table = Table(title=f"Announcements (showing {len(announcements)})")
        table.add_column("Date", style="cyan", width=12)
        table.add_column("Time", style="yellow", width=6)
        table.add_column("Headline", style="white", width=60)
        table.add_column("Price Sensitive", width=15)
        table.add_column("Pages", width=8)

        for ann in announcements:
            date_str = ann["date"]
            if date_str and len(date_str) == 8:
                formatted_date = (
                    f"{date_str[6:8]}/{date_str[4:6]}/{date_str[:4]}"
                )
            else:
                formatted_date = date_str

            time_str = ann["time"]
            if time_str and len(time_str) == 4:
                formatted_time = f"{time_str[:2]}:{time_str[2:]}"
            else:
                formatted_time = time_str

            price_sensitive = "✓" if ann["price_sensitive"] else "✗"

            table.add_row(
                formatted_date,
                formatted_time,
                ann["headline"][:57] + "..."
                if len(ann["headline"]) > 57
                else ann["headline"],
                price_sensitive,
                str(ann["pages"]),
            )

        console.print(table)

    def parse_date_range(
        self, period: str, reference_date: datetime | None = None
    ) -> tuple[datetime, datetime]:
        """
        Parse period string into date range.

        Supported formats:
        - "YYYY" (e.g., "2025")
        - "YYYY-MM" (e.g., "2024-03")
        - "YYYY-MM-DD to YYYY-MM-DD" (e.g., "2024-03-01 to 2024-03-31")
        - "1M", "3M", "6M", "1Y" (last X months/years from reference)
        """
        from datetime import timedelta

        if reference_date is None:
            reference_date = datetime.now()

        period = period.strip()

        if period.isdigit() and len(period) == 4:
            start_date = datetime(int(period), 1, 1)
            end_date = datetime(int(period), 12, 31)
            return start_date, end_date

        if " to " in period.lower():
            parts = period.lower().split(" to ")
            start_date = datetime.strptime(parts[0].strip(), "%Y-%m-%d")
            end_date = datetime.strptime(parts[1].strip(), "%Y-%m-%d")
            return start_date, end_date

        if "-" in period and len(period) == 7:
            year, month = map(int, period.split("-"))
            if month == 12:
                end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(year, month + 1, 1) - timedelta(days=1)
            start_date = datetime(year, month, 1)
            return start_date, end_date

        if period.upper() == "1M":
            end_date = reference_date
            start_date = reference_date - timedelta(days=30)
        elif period.upper() == "3M":
            end_date = reference_date
            start_date = reference_date - timedelta(days=90)
        elif period.upper() == "6M":
            end_date = reference_date
            start_date = reference_date - timedelta(days=180)
        elif period.upper() == "1Y":
            end_date = reference_date
            start_date = reference_date - timedelta(days=365)
        else:
            raise ValueError(f"Unknown period format: {period}")

        return start_date, end_date
