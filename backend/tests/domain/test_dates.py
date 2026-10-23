from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from promisekeeper.domain.dates import advance_reference, deadline, evaluation_time, ordered_timeline, parse_instant, review_boundary


@pytest.mark.parametrize("raw,want", [
    ("25 October 2026", "2026-10-25T18:30:00+00:00"),
    ("2026-10-25", "2026-10-25T18:30:00+00:00"),
    ("2026-10-25T17:00:00+02:00", "2026-10-25T15:00:00+00:00"),
])
def test_deadlines_use_exclusive_next_ist_midnight_or_the_explicit_offset(raw,want):
    result=deadline(raw)
    assert result.expires_at == datetime.fromisoformat(want)
    assert result.error is None


@pytest.mark.parametrize("raw,original", [
    ("soon", None), ("tomorrow", None), (None, None),
    ("31 February 2026", None), ("25 October", None),
])
def test_ambiguous_or_invalid_dates_do_not_get_invented_deadlines(raw,original):
    result=deadline(raw, original_at=original)
    assert result.expires_at is None
    assert result.error is not None


def test_tomorrow_uses_original_message_timezone_and_not_arrival_time():
    original=datetime.fromisoformat("2026-10-21T23:30:00+05:30")
    assert deadline("tomorrow", original_at=original).expires_at == datetime.fromisoformat("2026-10-22T18:30:00+00:00")


def test_naive_source_instants_are_rejected():
    with pytest.raises(ValueError):
        parse_instant("2026-10-23T10:00:00")


def test_source_offset_is_converted_without_changing_the_instant():
    assert parse_instant("2026-10-23T10:00:00+05:30") == datetime(2026,10,23,4,30,tzinfo=timezone.utc)


@pytest.mark.parametrize("invoice,promise", [
    ("2026-10-24T18:30:00Z", "2026-10-26T18:30:00Z"),
    ("2026-10-26T18:30:00Z", "2026-10-24T18:30:00Z"),
])
def test_fv18_selects_first_boundary_then_the_remaining_wait_boundary(invoice,promise):
    first=datetime.fromisoformat("2026-10-24T18:30:00Z")
    second=datetime.fromisoformat("2026-10-26T18:30:00Z")
    invoice=datetime.fromisoformat(invoice);promise=datetime.fromisoformat(promise)
    before=datetime.fromisoformat("2026-10-23T04:30:00Z")
    assert review_boundary(before,invoice_due=invoice,promise_expiries=(promise,)) == first
    assert review_boundary(first,invoice_due=invoice,promise_expiries=(promise,)) == second
    assert review_boundary(second,invoice_due=invoice,promise_expiries=(promise,)) is None


def test_reference_clock_cannot_move_backward_in_a_retained_copy():
    current=datetime.fromisoformat("2026-10-26T00:00:00+05:30")
    with pytest.raises(ValueError,match="backward"):
        advance_reference(current,datetime.fromisoformat("2026-10-23T10:00:00+05:30"))
    assert advance_reference(current,current) == current


def test_reference_and_real_evaluation_clocks_are_explicit():
    reference=datetime.fromisoformat("2026-10-23T10:00:00+05:30")
    real=datetime.fromisoformat("2026-10-24T10:00:00+05:30")
    assert evaluation_time("REFERENCE",reference=reference,real_now=real) == reference
    assert evaluation_time("REAL",reference=reference,real_now=real) == real


def test_timeline_ties_use_stable_source_ids_and_undated_sources_remain_separate():
    instant=datetime.fromisoformat("2026-10-23T04:30:00Z")
    a=SimpleNamespace(event_at=instant,source_id="PK-001-L1")
    b=SimpleNamespace(event_at=instant,source_id="PK-001-M1")
    undated=SimpleNamespace(event_at=None,source_id="PK-001-X1")
    assert ordered_timeline((b,undated,a)) == ((a,b),(undated,))
