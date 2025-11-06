"""Entry logic for trading strategy"""


from skim.data.models import Candidate


def filter_candidates(
    gap_stocks: list[tuple[str, float, float]],
    price_sensitive_tickers: set[str],
    min_gap: float,
) -> list[Candidate]:
    """
    Filter gap stocks by price-sensitive announcements and minimum gap threshold

    Combines TradingView gaps with ASX price-sensitive announcements to identify
    high-quality entry candidates. Only stocks with both momentum (gap) and
    fundamental catalysts (announcements) are selected.

    Args:
        gap_stocks: List of (ticker, gap_percent, close_price) from TradingView
        price_sensitive_tickers: Set of tickers with price-sensitive announcements today
        min_gap: Minimum gap percentage threshold (e.g., 3.0 for 3%)

    Returns:
        List of Candidate objects meeting all criteria

    Examples:
        >>> gap_stocks = [("BHP", 3.5, 45.20), ("RIO", 2.0, 120.50)]
        >>> price_sensitive = {"BHP"}
        >>> candidates = filter_candidates(gap_stocks, price_sensitive, 3.0)
        >>> len(candidates)
        1
        >>> candidates[0].ticker
        'BHP'
    """
    candidates = []

    for ticker, gap_percent, close_price in gap_stocks:
        # Filter 1: Must have price-sensitive announcement
        if ticker not in price_sensitive_tickers:
            continue

        # Filter 2: Must meet minimum gap threshold
        if gap_percent < min_gap:
            continue

        # Create candidate
        candidate = Candidate(
            ticker=ticker,
            headline=f"Gap detected: {gap_percent:.2f}%",
            scan_date="",  # Set by caller
            status="watching",
            gap_percent=gap_percent,
            prev_close=close_price,
        )

        candidates.append(candidate)

    return candidates


def check_breakout(
    candidate: Candidate,
    current_price: float,
    opening_range_high: float,
) -> bool:
    """
    Check if price has broken above opening range high

    This is the entry signal for the pivot strategy. We wait for price to
    break above the opening range high (first 15-30 minutes of trading)
    to confirm momentum before entering.

    Args:
        candidate: Candidate to check for breakout
        current_price: Current market price
        opening_range_high: High price during opening range period

    Returns:
        True if breakout confirmed (price > opening range high), False otherwise

    Examples:
        >>> candidate = Candidate("BHP", "Gap", "2025-11-03", gap_percent=3.5)
        >>> check_breakout(candidate, 46.50, 46.00)
        True
        >>> check_breakout(candidate, 45.50, 46.00)
        False
    """
    # Price must break above opening range high to trigger entry
    return current_price > opening_range_high


def calculate_opening_range_high(
    high_prices: list[float],
) -> float | None:
    """
    Calculate opening range high from price samples

    The opening range is typically the first 15-30 minutes of trading.
    This function finds the highest price during that period.

    Args:
        high_prices: List of high prices during opening range period

    Returns:
        Highest price in opening range, or None if no valid prices

    Examples:
        >>> calculate_opening_range_high([46.00, 46.20, 46.10])
        46.2
        >>> calculate_opening_range_high([])
        None
    """
    if not high_prices:
        return None

    valid_prices = [p for p in high_prices if p > 0]

    if not valid_prices:
        return None

    return max(valid_prices)
