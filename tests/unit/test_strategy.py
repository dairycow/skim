"""Unit tests for lightweight position management helpers."""

import pytest

from skim.strategy.position_manager import (
    calculate_position_size,
    calculate_stop_loss,
    can_open_new_position,
    validate_position_size,
)


def test_can_open_new_position_respects_limit():
    assert can_open_new_position(4, max_positions=5) is True
    assert can_open_new_position(5, max_positions=5) is False


@pytest.mark.parametrize(
    "price,expected",
    [
        (50.0, 100),
        (10.0, 500),
        (10000.0, 0),
        (-1.0, 0),
    ],
)
def test_calculate_position_size(price, expected):
    assert calculate_position_size(price) == expected


def test_calculate_stop_loss_prefers_low_of_day():
    assert calculate_stop_loss(50.0, low_of_day=48.0) == 48.0
    assert calculate_stop_loss(50.0, low_of_day=None) == pytest.approx(47.5)


@pytest.mark.parametrize(
    "quantity,price,valid",
    [(100, 40.0, True), (0, 50.0, False), (100, 60.0, False)],
)
def test_validate_position_size(quantity, price, valid):
    assert (
        validate_position_size(quantity, price, max_position_value=5000.0)
        is valid
    )
