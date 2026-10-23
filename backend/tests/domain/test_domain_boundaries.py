from dataclasses import replace
from uuid import uuid4

import pytest

from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.domain.evidence import (
    Availability, CommitmentAnchor, CommitmentCandidate, Extraction, SourceKind, commitment_id,
)
from promisekeeper.domain.payments import reconcile_payments
from promisekeeper.domain.recommendations import recommend
from promisekeeper.fixtures.catalogue import apply_event, fresh_copy


def test_reversal_of_an_identical_duplicate_version_reverses_the_transaction_once():
    demo=fresh_copy("FV-06-DUPLICATE");case=demo.cases["PK-003"].evidence
    duplicate=case.payments[-1]
    reversal=replace(duplicate,source=replace(duplicate.source,id=uuid4(),source_id="PK-003-TEST-R1",kind=SourceKind.REVERSAL),
                     transaction_ref="TEST-REVERSAL",reverses_payment_version_id=duplicate.source.id)
    facts=reconcile_payments(replace(case,payments=(*case.payments,reversal)))
    assert facts.paid_minor==3000000 and facts.balance_minor==6000000


def test_promise_link_to_an_identical_duplicate_version_credits_the_transaction_once():
    demo=fresh_copy("FV-16-LINKED");fixture=demo.cases["PK-002"];case=fixture.evidence
    original=case.payments[-1]
    duplicate=replace(original,source=replace(original.source,id=uuid4(),source_id="PK-002-TEST-L1"))
    link=replace(case.attributions[0],payment_version_id=duplicate.source.id)
    changed=replace(case,payments=(*case.payments,duplicate),attributions=(link,))
    result=recommend(changed,fixture.extraction,demo.evaluation_at)
    assert result.action=="FOLLOW_UP" and result.financial.balance_minor==3000000
    assert result.commitments[0].credited_minor==2000000


def test_numeric_substring_cannot_stand_in_for_the_stated_amount_token():
    fixture=fresh_copy("FV-16-LINKED").cases["PK-002"]
    candidate=replace(fixture.extraction.commitments[0],amount_text="20")
    with pytest.raises(ValueError,match="token"):
        reconcile_commitments(fixture.evidence,Extraction((candidate,),()),reconcile_payments(fixture.evidence))


def test_stated_amount_omitted_by_extraction_is_a_limitation_not_an_unstated_promise():
    demo=fresh_copy("FV-16-LINKED");fixture=demo.cases["PK-002"]
    candidate=replace(fixture.extraction.commitments[0],amount_text=None,currency_text=None)
    result=recommend(fixture.evidence,Extraction((candidate,),()),demo.evaluation_at)
    assert result.action=="VERIFY_PAYMENT" and result.status=="LIMITED"


def test_unavailable_message_cannot_supply_a_successful_extraction():
    fixture=fresh_copy().cases["PK-002"]
    message=fixture.evidence.messages[0]
    unavailable=replace(message.source,availability=Availability.UNAVAILABLE)
    case=replace(fixture.evidence,messages=(replace(message,source=unavailable),))
    candidate=replace(fixture.extraction.commitments[0],source=unavailable)
    with pytest.raises(ValueError,match="unavailable"):
        reconcile_commitments(case,Extraction((candidate,),()),reconcile_payments(case))


def test_each_anchored_clause_must_be_extracted_even_when_the_message_is_covered():
    demo=fresh_copy();fixture=demo.cases["PK-001"];case=fixture.evidence
    first="We will pay INR 80,000 by 20 October 2026."
    second="We will pay INR 80,000 by 25 October 2026."
    source=replace(case.messages[0].source,id=uuid4(),source_id="PK-001-TEST-M1",original_content=first+" "+second)
    key1,key2="PK-001-TEST-M1-C1","PK-001-TEST-M1-C2"
    anchors=(CommitmentAnchor(commitment_id(demo.id,source.id,key1),demo.id,case.case_id,source.id,key1,0,len(first)),
             CommitmentAnchor(commitment_id(demo.id,source.id,key2),demo.id,case.case_id,source.id,key2,len(first)+1,len(source.original_content)))
    changed=replace(case,messages=(replace(case.messages[0],source=source),),anchors=anchors)
    candidate=replace(fixture.extraction.commitments[0],source=source,quote=first,end=len(first),commitment_key=key1)
    result=recommend(changed,Extraction((candidate,),()),demo.evaluation_at)
    assert result.action=="VERIFY_PAYMENT" and result.status=="LIMITED"


def test_explicit_replacement_cycles_remain_a_conflict():
    demo=apply_event(fresh_copy(),"PK-001-U1");fixture=demo.cases["PK-001"];case=fixture.evidence
    first=fixture.extraction.commitments[0]
    text="We explicitly replace our 25 October promise: INR 80,000 by 20 October 2026."
    source=replace(first.source,original_content=text)
    changed=replace(case,messages=(replace(case.messages[0],source=source),case.messages[1]),
                    anchors=(replace(case.anchors[0],clause_end=len(text)),case.anchors[1]))
    candidate=replace(first,source=source,quote=text,end=len(text),explicitly_replaces_source_id="PK-001-M2")
    result=recommend(changed,Extraction((candidate,fixture.extraction.commitments[1]),()),demo.evaluation_at)
    assert result.action=="VERIFY_PAYMENT"


def test_explicit_invoice_and_payment_corrections_preserve_originals_and_rederive_totals():
    fixture=fresh_copy().cases["PK-001"];case=fixture.evidence
    invoice=case.invoices[0];payment=case.payments[0]
    corrected_invoice=replace(invoice,source=replace(invoice.source,id=uuid4(),source_id="PK-001-TEST-I2",supersedes_version_id=invoice.source.id),amount_text="125,000.00")
    corrected_payment=replace(payment,source=replace(payment.source,id=uuid4(),source_id="PK-001-TEST-L2",supersedes_version_id=payment.source.id),amount_text="45,000.00")
    result=reconcile_payments(replace(case,invoices=(invoice,corrected_invoice),payments=(payment,corrected_payment)))
    assert result.balance_minor==8000000
    assert invoice.amount_text=="120,000.00" and payment.amount_text=="40,000.00"


def test_verified_reversal_rederives_fulfillment_without_transferring_or_restoring_credit():
    demo=fresh_copy("FV-16-LINKED");fixture=demo.cases["PK-002"];case=fixture.evidence
    payment=case.payments[-1]
    # Isolate reversal: no other unallocated payment may leave attribution unresolved.
    case=replace(case,payments=(payment,))
    reversal=replace(payment,source=replace(payment.source,id=uuid4(),source_id="PK-002-TEST-R1",kind=SourceKind.REVERSAL),
                     transaction_ref="TEST-REVERSAL",reverses_payment_version_id=payment.source.id)
    result=recommend(replace(case,payments=(*case.payments,reversal)),fixture.extraction,demo.evaluation_at)
    assert result.financial.balance_minor==7500000
    assert result.commitments[0].credited_minor==0 and not result.commitments[0].fulfilled
    assert result.action=="WAIT"


def test_reversed_link_does_not_resolve_another_material_unattributed_payment():
    demo=fresh_copy("FV-16-LINKED");fixture=demo.cases["PK-002"];case=fixture.evidence
    payment=case.payments[-1]
    reversal=replace(payment,source=replace(payment.source,id=uuid4(),source_id="PK-002-TEST-R1",kind=SourceKind.REVERSAL),
                     transaction_ref="TEST-REVERSAL",reverses_payment_version_id=payment.source.id)
    result=recommend(replace(case,payments=(*case.payments,reversal)),fixture.extraction,demo.evaluation_at)
    assert result.financial.balance_minor==5000000
    assert result.commitments[0].credited_minor==0 and not result.commitments[0].fulfilled
    assert result.action=="VERIFY_PAYMENT" and result.reason_code=="COMMITMENT_ATTRIBUTION_UNRESOLVED"


def test_negated_replacement_wording_cannot_supersede_an_existing_promise():
    demo=apply_event(fresh_copy(),"PK-001-U1");fixture=demo.cases["PK-001"];case=fixture.evidence
    candidate=fixture.extraction.commitments[1]
    text="We do not explicitly replace our 20 October promise: INR 80,000 by 25 October 2026."
    source=replace(candidate.source,original_content=text)
    changed=replace(case,messages=(case.messages[0],replace(case.messages[1],source=source)),
                    anchors=(case.anchors[0],replace(case.anchors[1],clause_end=len(text))))
    extraction=Extraction((fixture.extraction.commitments[0],replace(candidate,source=source,quote=text,end=len(text))),())
    with pytest.raises(ValueError,match="Replacement"):
        reconcile_commitments(changed,extraction,reconcile_payments(changed))
