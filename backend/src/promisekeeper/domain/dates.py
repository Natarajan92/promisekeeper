"""Aware source and business clocks; behavior follows the domain tests."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import re
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
TEMPORAL_POLICY_VERSION = 'deadline-by-1'
_MONTHS = {name: index for index, name in enumerate(
    ("january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"), 1)}


@dataclass(frozen=True, slots=True)
class DateValue:
    raw: str | None
    expires_at: datetime | None
    error: str | None


def _aware(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Instant requires an explicit timezone")
    return value


def parse_instant(raw: str) -> datetime:
    if not isinstance(raw, str):
        raise ValueError("Instant must be source text")
    return _aware(datetime.fromisoformat(raw)).astimezone(timezone.utc)


def _calendar_day(raw: str, original_at: datetime | None, *, allow_weekday=False) -> date:
    value = raw.strip()
    if value.lower() in {"today", "tomorrow"}:
        original = _aware(original_at)
        return original.date() + timedelta(days=value.lower() == "tomorrow")
    weekday=re.fullmatch(r'next (Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)',value,re.I)
    if allow_weekday and weekday:
        original=_aware(original_at).date()
        target=['monday','tuesday','wednesday','thursday','friday','saturday','sunday'].index(weekday[1].lower())
        return original+timedelta(days=(target-original.weekday())%7 or 7)
    if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return date.fromisoformat(value)
    match = re.fullmatch(r"([0-9]{1,2}) ([A-Za-z]+) ([0-9]{4})", value)
    if match and match[2].lower() in _MONTHS:
        return date(int(match[3]), _MONTHS[match[2].lower()], int(match[1]))
    raise ValueError("Unsupported or ambiguous source date")


def source_day(raw: str | None, *, original_at: datetime | None = None) -> date | None:
    try:
        return _calendar_day(raw, original_at) if raw is not None else None
    except (ValueError, TypeError, OverflowError):
        return None


def deadline(raw, *, original_at=None, allow_weekday=False):
    if raw is None:
        return DateValue(raw, None, "UNKNOWN_DATE")
    try:
        # A deadline connector is not evidence of an actual payment day.
        # Keep the original raw value and leave shared calendar parsing strict.
        expression = re.sub(r"^by ", "", raw, count=1, flags=re.IGNORECASE)
        if re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt]", expression):
            instant = parse_instant(expression)
        else:
            day = _calendar_day(expression, original_at,allow_weekday=allow_weekday) + timedelta(days=1)
            instant = datetime.combine(day, time.min, IST).astimezone(timezone.utc)
        return DateValue(raw, instant, None)
    except (ValueError, TypeError, OverflowError):
        return DateValue(raw, None, "UNRESOLVED_DATE")


def review_boundary(now, *, invoice_due=None, promise_expiries=()):
    _aware(now)
    boundaries = [instant for instant in (invoice_due, *promise_expiries)
                  if instant is not None and _aware(instant) > now]
    return min(boundaries) if boundaries else None


def advance_reference(current, target):
    if _aware(target) < _aware(current):
        raise ValueError("Reference time cannot move backward")
    return target


def evaluation_time(mode, *, reference, real_now):
    if mode == "REFERENCE":
        return _aware(reference)
    if mode == "REAL":
        return _aware(real_now)
    raise ValueError("Unknown business clock mode")


def ordered_timeline(items):
    dated = [item for item in items if item.event_at is not None]
    undated = [item for item in items if item.event_at is None]
    key = lambda item: (item.source_id, getattr(item, "version", 0), str(getattr(item, "id", "")))
    return (tuple(sorted(dated, key=lambda item: (_aware(item.event_at), *key(item)))),
            tuple(sorted(undated, key=key)))
