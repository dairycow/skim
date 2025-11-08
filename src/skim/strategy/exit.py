"""Exit logic for trading strategy"""

from dataclasses import dataclass

from skim.data.models import Position


@dataclass
class ExitSignal:
    """Signal to exit a position (full or partial)"""

    action: str  # "SELL_ALL" or "SELL_HALF"
    quantity: int
    reason: str


def check_stop_loss(
    position: Position,
    current_price: float,
    low_of_day: float | None = None,
) -> ExitSignal | None:
    """
    Check if stop loss should be triggered

    Stop loss is set at the low of day to protect against reversals.
    This gives the trade room to breathe while limiting downside.

    Args:
        position: Position to check
        current_price: Current market price
        low_of_day: Low price of the day (if None, uses position.stop_loss)

    Returns:
        ExitSignal if stop loss triggered, None otherwise

    Examples:
        >>> pos = Position("BHP", 100, 46.50, 43.00, "2025-11-03T10:15:00")
        >>> check_stop_loss(pos, 42.50)
        ExitSignal(action='SELL_ALL', quantity=100, reason='Stop loss hit at $42.50')
        >>> check_stop_loss(pos, 44.00)
        None
    """
    # Use low_of_day if provided, otherwise fall back to position.stop_loss
    stop_price = low_of_day if low_of_day is not None else position.stop_loss

    if current_price <= stop_price:
        # Calculate remaining quantity (may be half if already partially exited)
        remaining_qty = (
            position.quantity
            if not position.half_sold
            else position.quantity // 2
        )

        return ExitSignal(
            action="SELL_ALL",
            quantity=remaining_qty,
            reason=f"Stop loss hit at ${current_price:.2f}",
        )

    return None


def check_half_exit(
    position: Position,
    days_held: int | None = None,
) -> ExitSignal | None:
    """
    Check if half position should be exited on day 3

    Strategy rule: Sell half the position on day 3 to lock in profits
    while letting the other half run with a trailing stop.

    Args:
        position: Position to check
        days_held: Number of days held (if None, calculated from position.entry_date)

    Returns:
        ExitSignal if day 3 half-exit triggered, None otherwise

    Examples:
        >>> pos = Position("BHP", 100, 46.50, 43.00, "2025-11-01T10:15:00")
        >>> check_half_exit(pos, days_held=3)
        ExitSignal(action='SELL_HALF', quantity=50, reason='Day 3 half exit')
        >>> check_half_exit(pos, days_held=2)
        None
    """
    # If already exited half, don't trigger again
    if position.half_sold:
        return None

    # Use provided days_held or calculate from position
    days = days_held if days_held is not None else position.days_held

    # Trigger on day 3 or later
    if days >= 3:
        quantity_to_sell = position.quantity // 2

        if quantity_to_sell > 0:
            return ExitSignal(
                action="SELL_HALF",
                quantity=quantity_to_sell,
                reason="Day 3 half exit",
            )

    return None


def check_trailing_stop(
    position: Position,
    current_price: float,
    sma_10: float,
) -> ExitSignal | None:
    """
    Check if trailing stop with 10-day SMA should be triggered

    After the day 3 half-exit, trail the remaining position with the
    10-day simple moving average. Exit if price closes below the SMA.

    Args:
        position: Position to check
        current_price: Current market price
        sma_10: 10-day simple moving average

    Returns:
        ExitSignal if trailing stop triggered, None otherwise

    Examples:
        >>> pos = Position("BHP", 100, 46.50, 43.00, "2025-11-01T10:15:00", half_sold=True)
        >>> check_trailing_stop(pos, 45.00, 46.00)
        ExitSignal(action='SELL_ALL', quantity=50, reason='Price below 10-day SMA ($46.00)')
        >>> check_trailing_stop(pos, 47.00, 46.00)
        None
    """
    # Only apply trailing stop after half exit
    if not position.half_sold:
        return None

    # Exit if price falls below 10-day SMA
    if current_price < sma_10:
        remaining_qty = position.quantity // 2

        return ExitSignal(
            action="SELL_ALL",
            quantity=remaining_qty,
            reason=f"Price below 10-day SMA (${sma_10:.2f})",
        )

    return None


def update_stop_loss(
    position: Position,
    low_of_day: float,
) -> float:
    """
    Update stop loss to current low of day

    The stop loss trails up with the low of day to protect profits
    as the trade moves in our favor.

    Args:
        position: Position to update
        low_of_day: Current low of day

    Returns:
        New stop loss price (max of current stop and low of day)

    Examples:
        >>> pos = Position("BHP", 100, 46.50, 43.00, "2025-11-03T10:15:00")
        >>> update_stop_loss(pos, 44.00)
        44.0
        >>> update_stop_loss(pos, 42.00)
        43.0
    """
    # Stop loss can only move up, never down
    return max(position.stop_loss, low_of_day)
