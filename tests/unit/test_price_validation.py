"""FR-015: invalid prices are rejected with a reason, never shown."""

import pytest

from kisan.prices.normalise import CropBounds, validate

WHEAT = CropBounds(1500, 10000)


@pytest.mark.parametrize(
    ("low", "high", "reason"),
    [
        (None, None, "no_price"),
        (0, 0, "not_positive"),
        (-100, 4000, "not_positive"),
        (0, 4000, "not_positive"),
        (4100, 4000, "min_above_max"),
        (1000, 4000, "out_of_range"),
        (4000, 25000, "out_of_range"),
        (None, 100, "out_of_range"),
    ],
)
def test_rejected(low: int | None, high: int | None, reason: str) -> None:
    assert validate(low, high, WHEAT) == reason


@pytest.mark.parametrize(("low", "high"), [(3900, 4050), (4000, 4000), (None, 4000),
                                           (1500, 10000)])
def test_accepted(low: int | None, high: int | None) -> None:
    assert validate(low, high, WHEAT) is None


def test_unknown_crop_bounds_only_basic_checks() -> None:
    assert validate(5, 6, None) is None
    assert validate(0, 6, None) == "not_positive"
