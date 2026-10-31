import pytest

from src.calculator import clamp


@pytest.mark.parametrize("value,low,high,expected", [(5, 0, 10, 5), (-3, 0, 10, 0), (20, 0, 10, 10), (2, 2, 2, 2), (0.5, 0, 1, 0.5)])
def test_clamping(value, low, high, expected):
    assert clamp(value, low, high) == expected


@pytest.mark.parametrize("low,high", [(3, 2), (0, -2), (100, 99)])
def test_bad_bounds(low, high):
    with pytest.raises(ValueError):
        clamp(0, low, high)
