import pytest

from promisekeeper.domain.money import minor_text, parse_money


@pytest.mark.parametrize("raw,want", [
    ("120,000.00", 12000000), ("0", 0), ("0.01", 1),
    ("60,000.1", 6000010), ("99999999999999999999.99", 9999999999999999999999),
])
def test_source_amounts_normalize_to_exact_integer_paise(raw, want):
    value = parse_money(raw)
    assert value.minor_units == want
    assert value.error is None
    assert value.raw == raw


@pytest.mark.parametrize("raw,currency,reason", [
    (None, "INR", "UNKNOWN_AMOUNT"), ("", "INR", "INVALID_AMOUNT"),
    ("-60,000.00", "INR", "NEGATIVE_AMOUNT"),
    ("60,000.001", "INR", "INVALID_PRECISION"),
    ("60,000", "USD", "UNSUPPORTED_CURRENCY"),
    ("60,000", None, "UNKNOWN_CURRENCY"),
    ("NaN", "INR", "INVALID_AMOUNT"), ("1e6", "INR", "INVALID_AMOUNT"),
    ("60,00.00", "INR", "INVALID_AMOUNT"),
])
def test_invalid_or_unknown_money_retains_the_original_and_never_becomes_zero(raw, currency, reason):
    value = parse_money(raw, currency)
    assert value.minor_units is None
    assert value.error == reason
    assert value.raw == raw


def test_float_money_is_rejected_instead_of_rounded():
    with pytest.raises(TypeError):
        parse_money(60000.001)


@pytest.mark.parametrize("value,want", [(0,"0"), (1,"1"), (-1000000,"-1000000"), (9999999999999999999999,"9999999999999999999999")])
def test_json_and_sqlite_minor_units_are_lossless_decimal_strings(value, want):
    assert minor_text(value) == want


def test_large_valid_amount_does_not_depend_on_float_or_machine_integer_limits():
    raw = "1" + "0" * 4500 + ".01"
    value = parse_money(raw)
    assert value.minor_units == 10 ** 4502 + 1
    assert minor_text(value.minor_units) == "1" + "0" * 4501 + "1"


@pytest.mark.parametrize("raw,want", [
    ("1,20,000.00", 12000000), ("12,34,567.89", 123456789), ("1,00,00,000", 1000000000),
    ("99,999", 9999900), ("1,234,567.89", 123456789),
])
def test_indian_and_international_digit_grouping_normalize_exactly(raw, want):
    assert parse_money(raw).minor_units == want and parse_money(raw).error is None


@pytest.mark.parametrize("raw", ["48,00,0", "1,2,000", "12,34,56", "1,234,56,789", ",120,000", "1,20,000,", "01,20,000"])
def test_malformed_digit_grouping_is_still_invalid(raw):
    assert parse_money(raw).error == "INVALID_AMOUNT"
