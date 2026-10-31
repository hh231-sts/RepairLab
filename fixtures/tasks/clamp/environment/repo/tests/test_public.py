import pytest
from src.calculator import clamp


def test_normal():
    assert clamp(5, 0, 10) == 5


def test_inverted():
    with pytest.raises(ValueError):
        clamp(3, 8, 2)
