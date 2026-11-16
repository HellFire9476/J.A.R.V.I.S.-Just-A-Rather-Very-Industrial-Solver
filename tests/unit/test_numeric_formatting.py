from decimal import Decimal

import pytest

from jarvis.presentation.numeric_format import format_decimal, format_power


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("30.000"), "30"),
        (Decimal("30.500"), "30,5"),
        (Decimal("30.250"), "30,25"),
        (Decimal("30.125"), "30,125"),
        (Decimal("-0.0001"), "0"),
        (60, "60"),
    ],
)
def test_format_decimal_removes_insignificant_zeros(value, expected):
    assert format_decimal(value) == expected


def test_format_decimal_applies_optional_grouping():
    assert format_decimal(Decimal("12345.500"), grouping=True) == "12 345,5"


def test_format_power_rounds_display_to_two_decimals():
    assert format_power(Decimal("10.938552195")) == "10,94"
    assert format_power(Decimal("150.000")) == "150"


def test_format_decimal_rejects_negative_precision():
    with pytest.raises(ValueError, match="décimales"):
        format_decimal(12, max_decimals=-1)
