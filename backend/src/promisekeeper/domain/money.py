"""Exact monetary normalization; behavior follows the domain tests."""

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class MoneyValue:
    raw: str | None
    minor_units: int | None
    error: str | None


def parse_money(raw, currency="INR"):
    if raw is not None and not isinstance(raw, str):
        raise TypeError("Source money must be text or null")
    error = None
    value = raw.strip() if raw is not None else None
    if currency is None:
        error = "UNKNOWN_CURRENCY"
    elif currency != "INR":
        error = "UNSUPPORTED_CURRENCY"
    elif value is None:
        error = "UNKNOWN_AMOUNT"
    elif value.startswith("-"):
        error = "NEGATIVE_AMOUNT"
    elif re.fullmatch(r"[0-9,]+\.[0-9]{3,}", value):
        error = "INVALID_PRECISION"
    elif not re.fullmatch(r"(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:,[0-9]{3})+)(?:\.[0-9]{1,2})?", value):
        error = "INVALID_AMOUNT"
    if error:
        return MoneyValue(raw, None, error)
    whole, _, fraction = value.replace(",", "").partition(".")
    digits = whole + fraction.ljust(2, "0")
    integer = 0
    # Small chunks avoid Python's text/int digit limit without changing global limits.
    for start in range(0, len(digits), 9):
        chunk = digits[start:start + 9]
        integer = integer * 10 ** len(chunk) + int(chunk)
    return MoneyValue(raw, integer, None)


def minor_text(value):
    if type(value) is not int:
        raise TypeError("Minor units must be an integer")
    sign = "-" if value < 0 else ""
    value = abs(value)
    chunks = []
    while value >= 1_000_000_000:
        value, remainder = divmod(value, 1_000_000_000)
        chunks.append(f"{remainder:09}")
    return sign + str(value) + "".join(reversed(chunks))
