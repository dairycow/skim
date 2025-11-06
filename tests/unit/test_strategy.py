"""Unit tests for strategy layer (entry, exit, position management)"""

import pytest

from skim.data.models import Candidate, Position
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


class TestEntryLogic:
    """Tests for entry logic functions"""

    def test_filter_candidates_with_price_sensitive_and_gap(self):
        """Should include stocks with both price-sensitive announcement and sufficient gap"""
        gap_stocks = [
            ("BHP", 3.5, 45.20),
            ("RIO", 4.0, 120.50),
        ]
        price_sensitive = {"BHP", "RIO"}
        min_gap = 3.0

        candidates = filter_candidates(gap_stocks, price_sensitive, min_gap)

        assert len(candidates) == 2
        assert candidates[0].ticker == "BHP"
        assert candidates[0].gap_percent == 3.5
        assert candidates[1].ticker == "RIO"
        assert candidates[1].gap_percent == 4.0

    def test_filter_candidates_no_price_sensitive_announcement(self):
        """Should exclude stocks without price-sensitive announcements"""
        gap_stocks = [
            ("BHP", 3.5, 45.20),
            ("RIO", 4.0, 120.50),
        ]
        price_sensitive = {"BHP"}  # Only BHP has announcement
        min_gap = 3.0

        candidates = filter_candidates(gap_stocks, price_sensitive, min_gap)

        assert len(candidates) == 1
        assert candidates[0].ticker == "BHP"

    def test_filter_candidates_below_gap_threshold(self):
        """Should exclude stocks below gap threshold"""
        gap_stocks = [
            ("BHP", 2.5, 45.20),  # Below threshold
            ("RIO", 4.0, 120.50),  # Above threshold
        ]
        price_sensitive = {"BHP", "RIO"}
        min_gap = 3.0

        candidates = filter_candidates(gap_stocks, price_sensitive, min_gap)

        assert len(candidates) == 1
        assert candidates[0].ticker == "RIO"

    def test_filter_candidates_empty_inputs(self):
        """Should return empty list for empty inputs"""
        assert filter_candidates([], set(), 3.0) == []
        assert filter_candidates([("BHP", 3.5, 45.20)], set(), 3.0) == []

    def test_filter_candidates_sets_correct_fields(self):
        """Should set candidate fields correctly"""
        gap_stocks = [("BHP", 3.5, 45.20)]
        price_sensitive = {"BHP"}
        min_gap = 3.0

        candidates = filter_candidates(gap_stocks, price_sensitive, min_gap)

        assert candidates[0].ticker == "BHP"
        assert candidates[0].gap_percent == 3.5
        assert candidates[0].prev_close == 45.20
        assert candidates[0].status == "watching"
        assert "3.50%" in candidates[0].headline

    def test_check_breakout_price_above_opening_range(self):
        """Should return True when price breaks above opening range high"""
        candidate = Candidate(
            ticker="BHP",
            headline="Gap",
            scan_date="2025-11-03",
            status="watching",
            gap_percent=3.5,
        )

        assert check_breakout(candidate, current_price=46.50, opening_range_high=46.00)

    def test_check_breakout_price_below_opening_range(self):
        """Should return False when price is below opening range high"""
        candidate = Candidate(
            ticker="BHP",
            headline="Gap",
            scan_date="2025-11-03",
            status="watching",
            gap_percent=3.5,
        )

        assert not check_breakout(candidate, current_price=45.50, opening_range_high=46.00)

    def test_check_breakout_price_equals_opening_range(self):
        """Should return False when price equals opening range high (no breakout)"""
        candidate = Candidate(
            ticker="BHP",
            headline="Gap",
            scan_date="2025-11-03",
            status="watching",
            gap_percent=3.5,
        )

        assert not check_breakout(candidate, current_price=46.00, opening_range_high=46.00)

    def test_calculate_opening_range_high_normal(self):
        """Should return highest price from list"""
        assert calculate_opening_range_high([46.00, 46.20, 46.10, 45.90]) == 46.20

    def test_calculate_opening_range_high_empty_list(self):
        """Should return None for empty list"""
        assert calculate_opening_range_high([]) is None

    def test_calculate_opening_range_high_single_price(self):
        """Should return single price"""
        assert calculate_opening_range_high([46.00]) == 46.00

    def test_calculate_opening_range_high_filters_invalid(self):
        """Should filter out zero and negative prices"""
        assert calculate_opening_range_high([0, -1, 46.00, 46.20]) == 46.20

    def test_calculate_opening_range_high_all_invalid(self):
        """Should return None if all prices invalid"""
        assert calculate_opening_range_high([0, -1, 0]) is None


class TestExitLogic:
    """Tests for exit logic functions"""

    def test_check_stop_loss_triggered(self):
        """Should trigger stop loss when price falls below stop"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        signal = check_stop_loss(position, current_price=42.50)

        assert signal is not None
        assert signal.action == "SELL_ALL"
        assert signal.quantity == 100
        assert "42.50" in signal.reason

    def test_check_stop_loss_not_triggered(self):
        """Should not trigger when price above stop loss"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        signal = check_stop_loss(position, current_price=44.00)

        assert signal is None

    def test_check_stop_loss_with_low_of_day(self):
        """Should use low_of_day if provided"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        # Price below low_of_day but above position.stop_loss
        signal = check_stop_loss(position, current_price=43.50, low_of_day=44.00)

        assert signal is not None
        assert signal.action == "SELL_ALL"

    def test_check_stop_loss_half_sold_position(self):
        """Should calculate correct quantity for half-sold position"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="half_exited",
            half_sold=True,
        )

        signal = check_stop_loss(position, current_price=42.50)

        assert signal is not None
        assert signal.quantity == 50  # Half of 100

    def test_check_half_exit_day_3(self):
        """Should trigger half exit on day 3"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        signal = check_half_exit(position, days_held=3)

        assert signal is not None
        assert signal.action == "SELL_HALF"
        assert signal.quantity == 50
        assert "Day 3" in signal.reason

    def test_check_half_exit_day_2(self):
        """Should not trigger half exit before day 3"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        signal = check_half_exit(position, days_held=2)

        assert signal is None

    def test_check_half_exit_already_sold(self):
        """Should not trigger if already half sold"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="half_exited",
            half_sold=True,
        )

        signal = check_half_exit(position, days_held=3)

        assert signal is None

    def test_check_half_exit_odd_quantity(self):
        """Should handle odd quantities correctly"""
        position = Position(
            ticker="BHP",
            quantity=101,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        signal = check_half_exit(position, days_held=3)

        assert signal is not None
        assert signal.quantity == 50  # Integer division

    def test_check_trailing_stop_triggered(self):
        """Should trigger trailing stop when price below SMA"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-01T10:15:00",
            status="half_exited",
            half_sold=True,
        )

        signal = check_trailing_stop(position, current_price=45.00, sma_10=46.00)

        assert signal is not None
        assert signal.action == "SELL_ALL"
        assert signal.quantity == 50  # Remaining half
        assert "SMA" in signal.reason
        assert "46.00" in signal.reason

    def test_check_trailing_stop_not_triggered(self):
        """Should not trigger when price above SMA"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            status="half_exited",
            stop_loss=43.00,
            entry_date="2025-11-01T10:15:00",
            half_sold=True,
        )

        signal = check_trailing_stop(position, current_price=47.00, sma_10=46.00)

        assert signal is None

    def test_check_trailing_stop_not_half_sold(self):
        """Should not trigger trailing stop if position not half sold"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
            half_sold=False,
        )

        signal = check_trailing_stop(position, current_price=45.00, sma_10=46.00)

        assert signal is None

    def test_update_stop_loss_higher_low(self):
        """Should update stop loss to higher low of day"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        new_stop = update_stop_loss(position, low_of_day=44.00)

        assert new_stop == 44.00

    def test_update_stop_loss_lower_low(self):
        """Should not lower stop loss"""
        position = Position(
            ticker="BHP",
            quantity=100,
            entry_price=46.50,
            stop_loss=43.00,
            entry_date="2025-11-03T10:15:00",
            status="open",
        )

        new_stop = update_stop_loss(position, low_of_day=42.00)

        assert new_stop == 43.00  # Should keep current stop


class TestPositionManager:
    """Tests for position management functions"""

    def test_can_open_new_position_below_limit(self):
        """Should allow opening position when below limit"""
        assert can_open_new_position(current_positions=3, max_positions=5)

    def test_can_open_new_position_at_limit(self):
        """Should not allow opening position at limit"""
        assert not can_open_new_position(current_positions=5, max_positions=5)

    def test_can_open_new_position_above_limit(self):
        """Should not allow opening position above limit"""
        assert not can_open_new_position(current_positions=6, max_positions=5)

    def test_can_open_new_position_zero_positions(self):
        """Should allow opening first position"""
        assert can_open_new_position(current_positions=0, max_positions=5)

    def test_calculate_position_size_normal(self):
        """Should calculate correct position size"""
        # $5000 / $50 = 100 shares
        assert calculate_position_size(price=50.0) == 100

    def test_calculate_position_size_cheap_stock(self):
        """Should limit to max_shares for cheap stocks"""
        # $5000 / $0.50 = 10000 shares, but limited to 1000
        assert calculate_position_size(price=0.50) == 1000

    def test_calculate_position_size_expensive_stock(self):
        """Should handle expensive stocks"""
        # $5000 / $100 = 50 shares
        assert calculate_position_size(price=100.0) == 50

    def test_calculate_position_size_very_expensive_stock(self):
        """Should return 0 for extremely expensive stocks"""
        # $5000 / $10000 = 0.5 shares, rounds to 0
        assert calculate_position_size(price=10000.0) == 0

    def test_calculate_position_size_zero_price(self):
        """Should return 0 for zero price"""
        assert calculate_position_size(price=0.0) == 0

    def test_calculate_position_size_negative_price(self):
        """Should return 0 for negative price"""
        assert calculate_position_size(price=-10.0) == 0

    def test_calculate_position_size_custom_limits(self):
        """Should respect custom max_shares and max_value"""
        # $10000 / $50 = 200 shares
        assert calculate_position_size(price=50.0, max_shares=500, max_value=10000.0) == 200

    def test_calculate_stop_loss_with_low_of_day(self):
        """Should use low_of_day when provided"""
        stop = calculate_stop_loss(entry_price=50.0, low_of_day=48.0)
        assert stop == 48.0

    def test_calculate_stop_loss_without_low_of_day(self):
        """Should use percentage-based stop when low_of_day not provided"""
        # 50.0 * (1 - 0.05) = 47.5
        stop = calculate_stop_loss(entry_price=50.0)
        assert stop == 47.5

    def test_calculate_stop_loss_custom_percent(self):
        """Should use custom stop percentage"""
        # 100.0 * (1 - 0.10) = 90.0
        stop = calculate_stop_loss(entry_price=100.0, default_stop_percent=0.10)
        assert stop == 90.0

    def test_calculate_stop_loss_invalid_low_of_day(self):
        """Should use percentage-based stop for invalid low_of_day"""
        stop = calculate_stop_loss(entry_price=50.0, low_of_day=0)
        assert stop == 47.5

    def test_validate_position_size_valid(self):
        """Should validate correct position size"""
        # 100 * $40 = $4000 (within $5000 limit)
        assert validate_position_size(quantity=100, price=40.0)

    def test_validate_position_size_too_large(self):
        """Should reject position size exceeding value limit"""
        # 100 * $60 = $6000 (exceeds $5000 limit)
        assert not validate_position_size(quantity=100, price=60.0)

    def test_validate_position_size_zero_quantity(self):
        """Should reject zero quantity"""
        assert not validate_position_size(quantity=0, price=50.0)

    def test_validate_position_size_negative_quantity(self):
        """Should reject negative quantity"""
        assert not validate_position_size(quantity=-10, price=50.0)

    def test_validate_position_size_zero_price(self):
        """Should reject zero price"""
        assert not validate_position_size(quantity=100, price=0.0)

    def test_validate_position_size_negative_price(self):
        """Should reject negative price"""
        assert not validate_position_size(quantity=100, price=-10.0)

    def test_validate_position_size_at_limit(self):
        """Should accept position size at exact limit"""
        # 100 * $50 = $5000 (exactly at limit)
        assert validate_position_size(quantity=100, price=50.0)

    def test_validate_position_size_custom_limit(self):
        """Should respect custom max_position_value"""
        assert validate_position_size(quantity=100, price=90.0, max_position_value=10000.0)
        assert not validate_position_size(quantity=100, price=110.0, max_position_value=10000.0)


class TestExitSignal:
    """Tests for ExitSignal dataclass"""

    def test_exit_signal_creation(self):
        """Should create ExitSignal correctly"""
        signal = ExitSignal(
            action="SELL_ALL",
            quantity=100,
            reason="Stop loss hit",
        )

        assert signal.action == "SELL_ALL"
        assert signal.quantity == 100
        assert signal.reason == "Stop loss hit"

    def test_exit_signal_sell_half(self):
        """Should create SELL_HALF signal"""
        signal = ExitSignal(
            action="SELL_HALF",
            quantity=50,
            reason="Day 3 half exit",
        )

        assert signal.action == "SELL_HALF"
        assert signal.quantity == 50
