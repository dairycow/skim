"""Position sizing and management logic"""

from typing import Optional


def can_open_new_position(
    current_positions: int,
    max_positions: int = 5,
) -> bool:
    """
    Check if we can open a new position based on position limits

    Risk management rule: Limit concurrent positions to avoid over-concentration
    and manage portfolio risk.

    Args:
        current_positions: Number of currently open positions
        max_positions: Maximum allowed concurrent positions (default: 5)

    Returns:
        True if we can open a new position, False if at limit

    Examples:
        >>> can_open_new_position(3, max_positions=5)
        True
        >>> can_open_new_position(5, max_positions=5)
        False
    """
    return current_positions < max_positions


def calculate_position_size(
    price: float,
    max_shares: int = 1000,
    max_value: float = 5000.0,
) -> int:
    """
    Calculate position size based on price and risk limits

    Position sizing rules:
    1. Fixed dollar amount per position (default: $5000)
    2. Maximum shares per position (default: 1000)
    3. Must buy at least 1 share

    Args:
        price: Current stock price
        max_shares: Maximum shares per position (default: 1000)
        max_value: Maximum dollar value per position (default: 5000)

    Returns:
        Number of shares to buy (0 if price too high)

    Examples:
        >>> calculate_position_size(50.0)
        100
        >>> calculate_position_size(10.0)
        500
        >>> calculate_position_size(100.0)
        50
        >>> calculate_position_size(0.50, max_shares=1000, max_value=5000)
        1000
        >>> calculate_position_size(10000.0)
        0
    """
    if price <= 0:
        return 0

    # Calculate shares based on fixed dollar amount
    shares_by_value = int(max_value / price)

    # Limit to max shares
    shares = min(shares_by_value, max_shares)

    # Must buy at least 1 share
    return shares if shares >= 1 else 0


def calculate_stop_loss(
    entry_price: float,
    low_of_day: Optional[float] = None,
    default_stop_percent: float = 0.05,
) -> float:
    """
    Calculate initial stop loss price

    Stop loss strategy:
    1. If low_of_day is available, use that (ideal for intraday entries)
    2. Otherwise, use a percentage-based stop (default: 5% below entry)

    Args:
        entry_price: Entry price for the position
        low_of_day: Low price of the day (optional)
        default_stop_percent: Default stop loss percentage (default: 0.05 = 5%)

    Returns:
        Stop loss price

    Examples:
        >>> calculate_stop_loss(50.0, low_of_day=48.0)
        48.0
        >>> calculate_stop_loss(50.0)
        47.5
        >>> calculate_stop_loss(100.0, default_stop_percent=0.10)
        90.0
    """
    if low_of_day is not None and low_of_day > 0:
        return low_of_day

    # Fallback to percentage-based stop
    return entry_price * (1.0 - default_stop_percent)


def validate_position_size(
    quantity: int,
    price: float,
    max_position_value: float = 5000.0,
) -> bool:
    """
    Validate that a position size is within risk limits

    Safety check to ensure position sizing calculations are correct
    and within acceptable risk parameters.

    Args:
        quantity: Number of shares
        price: Price per share
        max_position_value: Maximum position value in dollars (default: 5000)

    Returns:
        True if position size is valid, False otherwise

    Examples:
        >>> validate_position_size(100, 50.0, max_position_value=5000.0)
        False
        >>> validate_position_size(100, 40.0, max_position_value=5000.0)
        True
        >>> validate_position_size(0, 50.0)
        False
    """
    # Must have positive quantity
    if quantity <= 0:
        return False

    # Must have positive price
    if price <= 0:
        return False

    # Position value must be within limit
    position_value = quantity * price
    return position_value <= max_position_value
