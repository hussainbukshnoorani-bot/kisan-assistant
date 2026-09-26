from decimal import Decimal

import pytest

from kisan.prices.normalise import UnknownUnitError, to_rs_per_40kg, unit_factor


@pytest.mark.parametrize(
    ("unit", "expected"),
    [
        ("40 Kg", "per_40kg"),
        ("40kg", "per_40kg"),
        ("Per 40 KG", "per_40kg"),
        ("maund", "per_40kg"),
        ("Mound", "per_40kg"),
        ("100 Kg", "per_100kg"),
        ("100KG", "per_100kg"),
        ("Kg", "per_kg"),
        ("1 kg", "per_kg"),
        ("per kg", "per_kg"),
    ],
)
def test_unit_recognised(unit: str, expected: str) -> None:
    assert unit_factor(unit)[0] == expected


@pytest.mark.parametrize(
    ("value", "unit", "expected"),
    [
        (Decimal("4000"), "40 Kg", 4000),
        (Decimal("10000"), "100 Kg", 4000),
        (Decimal("9750"), "100 Kg", 3900),
        (Decimal("62.5"), "Kg", 2500),
        (Decimal("100.01"), "Kg", 4000),  # rounded half-up to whole rupees
        (Decimal("3900"), "maund", 3900),
    ],
)
def test_converted_to_rs_per_40kg(value: Decimal, unit: str, expected: int) -> None:
    assert to_rs_per_40kg(value, unit) == expected


def test_none_stays_none() -> None:
    assert to_rs_per_40kg(None, "40 Kg") is None


@pytest.mark.parametrize("unit", ["bag", "50 kg", "", "ton"])
def test_unknown_unit_raises(unit: str) -> None:
    with pytest.raises(UnknownUnitError):
        to_rs_per_40kg(Decimal("100"), unit)
