from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from promisekeeper.domain.dates import deadline
from promisekeeper.domain.evidence import Extraction
from promisekeeper.domain.payments import reconcile_payments
from promisekeeper.domain.recommendations import recommend
from promisekeeper.fixtures.catalogue import apply_event, fresh_copy


def settled_claim():
    demo = apply_event(fresh_copy(), "PK-003-U1")
    return demo, demo.cases["PK-003"]


def rewrite_claim(fixture, text, **candidate_changes):
    message = fixture.evidence.messages[0]
    source = replace(message.source, original_content=text)
    case = replace(fixture.evidence, messages=(replace(message, source=source),))
    candidate = replace(fixture.extraction.claims[0], source=source, quote=text,
                        start=0, end=len(text), **candidate_changes)
    return case, Extraction((), (candidate,))


def test_partial_promise_date_cannot_turn_future_promise_into_follow_up():
    demo = fresh_copy()
    fixture = demo.cases["PK-002"]
    candidate = replace(fixture.extraction.commitments[0], date_text="5 October 2026")
    with pytest.raises(ValueError, match="token"):
        recommend(fixture.evidence, Extraction((candidate,), ()), demo.evaluation_at)


@pytest.mark.parametrize("source_reference", ["CR-T20", "XCR-T2", "CR-T2/EXTRA", "CR-T2.1"])
def test_partial_claim_reference_cannot_match_a_different_ledger_transaction(source_reference):
    demo, fixture = settled_claim()
    text = fixture.evidence.messages[0].source.original_content.replace("CR-T2", source_reference)
    case, extraction = rewrite_claim(fixture, text)
    with pytest.raises(ValueError, match="token"):
        recommend(case, extraction, demo.evaluation_at)


def test_partial_claim_date_cannot_hide_a_settlement_date_contradiction():
    demo, fixture = settled_claim()
    text = fixture.evidence.messages[0].source.original_content.replace("today", "22 October 2026")
    case, extraction = rewrite_claim(fixture, text, payment_date_text="2 October 2026")
    with pytest.raises(ValueError, match="token"):
        recommend(case, extraction, demo.evaluation_at)


def test_competing_corrections_are_unknown_not_two_independent_settlements():
    demo = fresh_copy()
    fixture = demo.cases["PK-001"]
    original = fixture.evidence.payments[0]
    successors = tuple(replace(original, amount_text="60,000.00", transaction_ref=f"CORRECTION-{index}",
        source=replace(original.source, id=uuid4(), source_id=f"PK-001-C{index}",
                       supersedes_version_id=original.source.id)) for index in (1, 2))
    case = replace(fixture.evidence, payments=(original, *successors))
    result = recommend(case, fixture.extraction, demo.evaluation_at)
    assert result.action == "VERIFY_PAYMENT" and result.status == "LIMITED"
    assert result.financial.paid_minor is None and result.financial.balance_minor is None
    assert not result.financial.eligible_payments
    assert any(issue.code == "CONFLICTING_CORRECTIONS" for issue in result.financial.issues)


def test_linear_correction_chain_and_identical_transaction_alias_still_count_once():
    original = fresh_copy().cases["PK-001"].evidence
    first = original.payments[0]
    second = replace(first, amount_text="50,000.00", source=replace(first.source,
        id=uuid4(), source_id="PK-001-C1", supersedes_version_id=first.source.id))
    third = replace(second, amount_text="60,000.00", source=replace(second.source,
        id=uuid4(), source_id="PK-001-C2", supersedes_version_id=second.source.id))
    duplicate = replace(third, source=replace(third.source, id=uuid4(), source_id="PK-001-D1",
                                             supersedes_version_id=None))
    facts = reconcile_payments(replace(original, payments=(first, second, third, duplicate)))
    assert facts.paid_minor == 6000000 and facts.balance_minor == 6000000
    assert not facts.issues and len(facts.eligible_payments) == 1


@pytest.mark.parametrize("stated_date", ["today", "22 October 2026", "2026-10-22"])
def test_omitted_stated_claim_date_remains_limited_even_when_money_balances(stated_date):
    demo, fixture = settled_claim()
    text = fixture.evidence.messages[0].source.original_content.replace("today", stated_date)
    case, extraction = rewrite_claim(fixture, text, payment_date_text=None)
    payment = case.payments[1]
    case = replace(case, payments=(case.payments[0], replace(payment,
        source=replace(payment.source, event_at=payment.source.event_at - timedelta(days=1)))))
    result = recommend(case, extraction, demo.evaluation_at)
    assert result.financial.balance_minor == 0
    assert result.action == "VERIFY_PAYMENT" and result.status == "LIMITED"
    assert not result.claims[0].resolved


def test_truly_unstated_claim_date_does_not_require_an_invented_date():
    demo, fixture = settled_claim()
    text = fixture.evidence.messages[0].source.original_content.replace(" today", "")
    case, extraction = rewrite_claim(fixture, text, payment_date_text=None)
    result = recommend(case, extraction, demo.evaluation_at)
    assert result.action == "CLOSE" and result.claims[0].resolved


def test_stated_claim_date_cannot_be_confirmed_by_an_unknown_settlement_day():
    demo, fixture = settled_claim()
    payment = fixture.evidence.payments[1]
    case = replace(fixture.evidence, payments=(fixture.evidence.payments[0],
        replace(payment, source=replace(payment.source, event_at=None))))
    result = recommend(case, fixture.extraction, demo.evaluation_at)
    assert result.action == "VERIFY_PAYMENT" and not result.claims[0].resolved


@pytest.mark.parametrize("raw", ["Tomorrow", "TOMORROW", "Today", "TODAY"])
def test_supported_relative_dates_are_case_insensitive(raw):
    original = datetime.fromisoformat("2026-10-21T23:30:00+05:30")
    assert deadline(raw, original_at=original) == replace(
        deadline(raw.lower(), original_at=original), raw=raw)
