"""
Date parsing utilities for specifying time periods.
"""

from datetime import datetime, timedelta


def parse_date_range(
    period: str, reference_date: datetime | None = None
) -> tuple[datetime, datetime]:
    """
    Parse period string into date range.

    Supported formats:
    - "YYYY" (e.g., "2025")
    - "YYYY-MM" (e.g., "2024-03")
    - "YYYY-MM-DD to YYYY-MM-DD" (e.g., "2024-03-01 to 2024-03-31")
    - "1M", "3M", "6M", "1Y" (last X months/years from reference)

    Args:
        period: Period string to parse
        reference_date: Reference date for relative periods (defaults to now)

    Returns:
        Tuple of (start_date, end_date)

    Raises:
        ValueError: If period format is unknown
    """
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
