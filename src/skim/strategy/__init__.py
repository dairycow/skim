"""Trading strategy logic (entry, exit, position management)"""

from skim.strategy.entry import (
    calculate_opening_range_high,
    check_breakout,
    filter_candidates,
)
from skim.strategy.exit import (
    ExitSignal,
    check_half_exit,
    check_stop_loss,
    check_trailing_stop,
    update_stop_loss,
)
from skim.strategy.position_manager import (
    calculate_position_size,
    calculate_stop_loss,
    can_open_new_position,
    validate_position_size,
)

__all__ = [
    # Entry logic
    "filter_candidates",
    "check_breakout",
    "calculate_opening_range_high",
    # Exit logic
    "ExitSignal",
    "check_stop_loss",
    "check_half_exit",
    "check_trailing_stop",
    "update_stop_loss",
    # Position management
    "can_open_new_position",
    "calculate_position_size",
    "calculate_stop_loss",
    "validate_position_size",
]
