from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from promisekeeper.domain.evidence import Extraction
from promisekeeper.domain.money import minor_text
from promisekeeper.domain.recommendations import recommend
from promisekeeper.fixtures.catalogue import apply_event, fresh_copy, variant_definition, variant_ids


FINANCIAL_IDS=[vid for vid in variant_ids() if "workflow" not in variant_definition(vid)]


def assert_expected(fixture,at):
    result=recommend(fixture.evidence,fixture.extraction,at)
    expected=fixture.expected
    assert result.action==expected["action"]
    balance=result.financial.balance_minor
    assert (minor_text(balance) if balance is not None else None)==expected["balance_minor"]
    review=datetime.fromisoformat(expected["review_at"]) if expected["review_at"] else None
    assert result.review_at==review
    assert result.source_refs
    assert result.reason_code and result.next_step
    return result


@pytest.mark.parametrize("cid,action,balance",[("PK-001","FOLLOW_UP",8000000),("PK-002","WAIT",5000000),("PK-003","VERIFY_PAYMENT",6000000),
                                               ("PK-004","FOLLOW_UP",6000000),("PK-005","VERIFY_PAYMENT",4500000),("PK-006","CLOSE",0)])
def test_baseline_business_facts_and_action_are_literal_acceptance_expectations(cid,action,balance):
    demo=fresh_copy();fixture=demo.cases[cid]
    result=assert_expected(fixture,demo.evaluation_at)
    assert result.action==action and result.financial.balance_minor==balance


@pytest.mark.parametrize("event,cid",[("PK-001-U1","PK-001"),("PK-002-U1","PK-002"),("PK-003-U1","PK-003")])
def test_staged_updates_produce_their_supported_new_action(event,cid):
    old=fresh_copy();demo=apply_event(old,event)
    assert_expected(demo.cases[cid],demo.evaluation_at)
    assert old.evaluation_at==datetime.fromisoformat("2026-10-23T10:00:00+05:30")


@pytest.mark.parametrize("variant",FINANCIAL_IDS)
def test_every_registered_financial_branch_has_the_exact_expected_action_and_balance(variant):
    demo=fresh_copy(variant);definition=variant_definition(variant)
    assert_expected(demo.cases[definition["case_id"]],demo.evaluation_at)


@pytest.mark.parametrize("branch",["A","B"])
def test_fv18_review_does_not_turn_wait_into_a_premature_follow_up(branch):
    demo=fresh_copy("FV-18-"+branch)
    initial=assert_expected(demo.cases["PK-002"],demo.evaluation_at)
    assert initial.review_at==datetime.fromisoformat("2026-10-25T00:00:00+05:30")
    before=recommend(demo.cases["PK-002"].evidence,demo.cases["PK-002"].extraction,initial.review_at-timedelta(microseconds=1))
    assert before.action=="WAIT" and before.review_at==initial.review_at
    first=apply_event(demo,f"FV-18-{branch}-CLOCK-1")
    middle=assert_expected(first.cases["PK-002"],first.evaluation_at)
    assert middle.action=="WAIT" and middle.review_at==datetime.fromisoformat("2026-10-27T00:00:00+05:30")
    last=apply_event(first,f"FV-18-{branch}-CLOCK-2")
    assert assert_expected(last.cases["PK-002"],last.evaluation_at).action=="FOLLOW_UP"


def test_customer_claim_is_not_settlement_and_missing_reference_requests_clarification():
    demo=fresh_copy("FV-13")
    result=assert_expected(demo.cases["PK-003"],demo.evaluation_at)
    assert result.claims[0].customer_clarification and not result.claims[0].resolved


def test_empty_extraction_cannot_hide_the_unverified_payment_claim():
    demo=fresh_copy();case=demo.cases["PK-003"]
    result=recommend(case.evidence,Extraction(),demo.evaluation_at)
    assert result.action=="VERIFY_PAYMENT"
    assert result.status=="LIMITED"


def test_source_instructions_cannot_verify_payments_or_change_authority():
    demo=fresh_copy("FV-12")
    result=assert_expected(demo.cases["PK-001"],demo.evaluation_at)
    assert result.financial.paid_minor==4000000


def test_incomplete_attempt_has_no_new_recommendation():
    demo=fresh_copy();case=demo.cases["PK-001"]
    result=recommend(case.evidence,case.extraction,demo.evaluation_at,attempt_complete=False)
    assert result.status=="INCOMPLETE" and result.action is None


def test_no_other_active_promise_allows_follow_up_after_partial_fulfillment():
    demo=fresh_copy("FV-16-LINKED");case=demo.cases["PK-002"]
    result=assert_expected(case,demo.evaluation_at)
    assert result.action=="FOLLOW_UP" and result.review_at is None
