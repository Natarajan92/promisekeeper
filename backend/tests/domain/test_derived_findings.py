from dataclasses import replace
from datetime import datetime, timezone
from uuid import uuid4

import pytest

from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.domain.recommendations import recommend
from promisekeeper.fixtures.catalogue import fresh_copy


def derive(case, extraction):
    from promisekeeper.application.derived_findings import derive_findings
    recommendation = recommend(case, extraction, datetime(2026,10,23,tzinfo=timezone.utc))
    packet = dict(snapshot_id=str(uuid4()), snapshot_hash='a'*64,
                  evidence=[dict(id=str(r.source.id), stable_source_id=r.source.source_id,
                                 availability=r.source.availability, original_content=r.source.original_content)
                            for r in (*case.invoices,*case.payments,*case.messages,*case.attributions)])
    return derive_findings(case, extraction, recommendation,
                           reconcile_commitments(case,extraction,recommendation.financial), packet)


@pytest.mark.parametrize('amount', ['-1', '1.234'])
def test_invalid_numeric_records_cannot_establish_known_disagreement(amount):
    item = fresh_copy().cases['PK-003']
    claim = item.extraction.claims[0]
    payment = replace(item.evidence.payments[0], amount_text=amount,
                      source=replace(item.evidence.payments[0].source,event_at=claim.source.event_at),
                      transaction_ref=claim.transaction_reference_text)
    result = derive(replace(item.evidence,payments=(payment,)),item.extraction)
    assert not any(c['kind']=='PAYMENT_CLAIM' for c in result['contradictions'])
    assert any(q['field']=='AMOUNT' and q['sources'][0]['source_id']==payment.source.source_id
               for q in result['unresolved_questions'])


def test_raw_vague_date_preserved_and_derived_as_unresolved():
    item = fresh_copy().cases['PK-001']
    candidate = item.extraction.commitments[0]
    raw = candidate.source.original_content.replace(candidate.date_text, 'next week')
    source = replace(candidate.source, original_content=raw)
    candidate = replace(candidate, source=source, quote=raw, start=0,end=len(raw),date_text='next week')
    case = replace(item.evidence,
                   messages=tuple(replace(m,source=source) if m.source.id==source.id else m for m in item.evidence.messages),
                   anchors=tuple(replace(a,clause_end=len(raw)) if a.evidence_version_id==source.id else a for a in item.evidence.anchors))
    result = derive(case,replace(item.extraction,commitments=(candidate,)))
    assert candidate.date_text == 'next week'
    assert any(q['field']=='PROMISE_DATE' and q['sources'][0]['quote']==raw for q in result['unresolved_questions'])


def test_nonempty_exact_spans_only_and_snapshot_observations_for_empty_sources():
    item = fresh_copy().cases['PK-001']
    invoice = replace(item.evidence.invoices[0],source=replace(item.evidence.invoices[0].source,original_content=''),amount_text=None)
    result = derive(replace(item.evidence,invoices=(invoice,)),item.extraction)
    assert all(s['quote'] for q in result['unresolved_questions'] for s in q['sources'])
    assert any(o['field']=='content_present' and o['value'] is False and
               o['source']['evidence_version_id']==str(invoice.source.id) for o in result['evidence_observations'])


def test_invalid_correction_branch_cannot_supply_known_invoice_disagreement():
    from promisekeeper.domain.record_lifecycle import project_records
    item = fresh_copy().cases['PK-001']
    original = item.evidence.invoices[0]
    invalid = replace(original, amount_text='1',source=replace(original.source,id=uuid4(),source_id='invalid',supersedes_version_id=uuid4()))
    child = replace(invalid, amount_text='2',source=replace(invalid.source,id=uuid4(),source_id='descendant',supersedes_version_id=invalid.source.id))
    projection = project_records((original, invalid, child))
    assert {invalid.source.id, child.source.id} <= projection.invalid_ids
    # The original financial selector still selects the invalid descendant.
    assert child in projection.active_records
    result = derive(replace(item.evidence,invoices=(original,invalid,child)),item.extraction)
    assert not result['contradictions']
    assert any(i['code']=='INVALID_CORRECTION' for i in result['financial_issues'])


def test_invalid_correction_retains_its_own_amount_gap_without_known_conflict():
    item = fresh_copy().cases['PK-001']
    original = item.evidence.invoices[0]
    invalid = replace(original,amount_text='-1',source=replace(original.source,id=uuid4(),source_id='negative-correction',supersedes_version_id=original.source.id))
    result = derive(replace(item.evidence,invoices=(original,invalid)),item.extraction)
    assert not result['contradictions']
    assert any(q['field']=='AMOUNT' and q['sources'][0]['source_id']=='negative-correction'
               for q in result['unresolved_questions'])


def test_duplicate_reversed_records_and_forked_descendants_are_excluded():
    from promisekeeper.domain.record_lifecycle import project_records
    item = fresh_copy('FV-06-REVERSAL').cases['PK-003']
    assert not any(c['kind']=='PAYMENT_CLAIM' for c in derive(item.evidence,item.extraction)['contradictions'])
    original = item.evidence.payments[0]
    left = replace(original,source=replace(original.source,id=uuid4(),source_id='left',supersedes_version_id=original.source.id))
    right = replace(left,source=replace(left.source,id=uuid4(),source_id='right'))
    child = replace(left,source=replace(left.source,id=uuid4(),source_id='child',supersedes_version_id=left.source.id))
    projection = project_records((original,left,right,child),payment=True)
    assert {left.source.id,right.source.id,child.source.id} <= projection.ambiguous_ids
    assert not projection.active_records


def test_currency_disagreement_does_not_turn_known_quantity_into_unknown_amount():
    item = fresh_copy('FV-07-CURRENCY').cases['PK-003']
    result = derive(item.evidence,item.extraction)
    assert any(c['kind']=='PAYMENT_CLAIM' for c in result['contradictions'])
    assert not any(q['field']=='AMOUNT' for q in result['unresolved_questions'])
    assert len([q for q in result['unresolved_questions'] if q['field']=='CURRENCY']) == 2


def test_superseded_promise_has_no_current_attribution_question():
    from promisekeeper.fixtures.catalogue import apply_event
    item = apply_event(fresh_copy(),'PK-001-U1').cases['PK-001']
    result = derive(item.evidence,item.extraction)
    assert not any(q['sources'][0]['source_id']=='PK-001-M1' for q in result['unresolved_questions'])


def reversal_case():
    from promisekeeper.domain.evidence import SourceKind
    item = fresh_copy().cases['PK-003']
    claim = item.extraction.claims[0]
    payment = replace(item.evidence.payments[0],amount_text='1',transaction_ref=claim.transaction_reference_text,
                      source=replace(item.evidence.payments[0].source,event_at=claim.source.event_at))
    reversal = replace(payment,transaction_ref='REVERSAL-TEST',reverses_payment_version_id=payment.source.id,
                       source=replace(payment.source,id=uuid4(),source_id='reversal-test',kind=SourceKind.REVERSAL))
    return item, payment, reversal


@pytest.mark.parametrize('change',[
    'unavailable','missing','unreadable','non_authoritative','unverified','unknown_verification','unsettled',
    'missing_reference','incompatible_amount','negative_amount','invalid_precision','unsupported_currency',
    'unallocated','different_invoice','invalid_correction','superseded','cyclic','forked','conflicting_reference',
])
def test_ineffective_reversal_pointer_does_not_hide_current_payment_disagreement(change):
    from promisekeeper.domain.evidence import Availability, VerificationStatus
    from promisekeeper.domain.record_lifecycle import project_records
    item, payment, reversal = reversal_case()
    extra = ()
    if change in {'unavailable','missing','unreadable'}:
        reversal = replace(reversal,source=replace(reversal.source,availability=Availability(change.upper())))
    elif change == 'non_authoritative':
        reversal = replace(reversal,source=replace(reversal.source,authoritative=False))
    elif change in {'unverified','unknown_verification'}:
        reversal = replace(reversal,verification_status=VerificationStatus.UNVERIFIED if change=='unverified' else VerificationStatus.UNKNOWN)
    elif change == 'unsettled':
        reversal = replace(reversal,settled=False)
    elif change == 'missing_reference':
        reversal = replace(reversal,transaction_ref=None)
    elif change in {'incompatible_amount','negative_amount','invalid_precision'}:
        reversal = replace(reversal,amount_text={'incompatible_amount':'2','negative_amount':'-1','invalid_precision':'1.001'}[change])
    elif change == 'unsupported_currency':
        reversal = replace(reversal,currency_text='USD')
    elif change in {'unallocated','different_invoice'}:
        reversal = replace(reversal,invoice_id=None if change=='unallocated' else 'OTHER-INVOICE')
    elif change == 'invalid_correction':
        reversal = replace(reversal,source=replace(reversal.source,supersedes_version_id=uuid4()))
    elif change == 'superseded':
        replacement = replace(reversal,reverses_payment_version_id=None,transaction_ref='REPLACEMENT-TEST',
                              source=replace(reversal.source,id=uuid4(),source_id='replacement-test',supersedes_version_id=reversal.source.id))
        extra = (replacement,)
    elif change == 'cyclic':
        reversal = replace(reversal,source=replace(reversal.source,supersedes_version_id=reversal.source.id))
    elif change == 'forked':
        parent = replace(reversal,reverses_payment_version_id=None,
                         source=replace(reversal.source,id=uuid4(),source_id='reversal-parent'))
        reversal = replace(reversal,source=replace(reversal.source,supersedes_version_id=parent.source.id))
        sibling = replace(reversal,source=replace(reversal.source,id=uuid4(),source_id='reversal-sibling'))
        extra = (parent,sibling)
    elif change == 'conflicting_reference':
        extra = (replace(reversal,amount_text='2',source=replace(reversal.source,id=uuid4(),source_id='conflicting-reversal')),)
    case = replace(item.evidence,payments=(payment,reversal,*extra))
    result = derive(case,item.extraction)
    assert any(c['kind']=='PAYMENT_CLAIM' and {s['source_id'] for s in c['sources']} ==
               {payment.source.source_id,item.extraction.claims[0].source.source_id} for c in result['contradictions'])
    assert payment.source.id not in project_records(case.payments,payment=True).reversed_ids
    assert all(s['source_id']!='reversal-test' for c in result['contradictions'] for s in c['sources'])


def test_valid_reversal_excludes_only_compatible_original_and_duplicate_aliases():
    from promisekeeper.domain.record_lifecycle import project_records
    from promisekeeper.domain.payments import reconcile_payments
    item, payment, reversal = reversal_case()
    alias = replace(payment,source=replace(payment.source,id=uuid4(),source_id='payment-alias'))
    reversal = replace(reversal,reverses_payment_version_id=alias.source.id)
    case = replace(item.evidence,payments=(payment,alias,reversal))
    assert project_records(case.payments,payment=True).reversed_ids == {payment.source.id,alias.source.id}
    assert reconcile_payments(case).reversed_payment_ids == (payment.source.id,)
    assert not any(c['kind']=='PAYMENT_CLAIM' for c in derive(case,item.extraction)['contradictions'])


def test_reversal_does_not_erase_conflicting_same_reference_originals():
    from promisekeeper.domain.record_lifecycle import project_records
    item, payment, reversal = reversal_case()
    conflicting = replace(payment,amount_text='2',source=replace(payment.source,id=uuid4(),source_id='conflicting-original'))
    case = replace(item.evidence,payments=(payment,conflicting,reversal))
    assert not project_records(case.payments,payment=True).reversed_ids
    assert any(c['kind']=='OTHER_CANDIDATE' for c in derive(case,item.extraction)['contradictions'])


def test_reversal_event_without_target_is_not_a_direct_payment_fact():
    from promisekeeper.domain.record_lifecycle import project_records
    item, payment, reversal = reversal_case()
    reversal = replace(reversal,reverses_payment_version_id=None,transaction_ref=payment.transaction_ref,amount_text='2')
    case = replace(item.evidence,payments=(payment,reversal))
    projection = project_records(case.payments,payment=True)
    assert reversal.source.id in projection.reversal_ids
    assert not projection.reversed_ids
    result = derive(case,item.extraction)
    assert any(c['kind']=='PAYMENT_CLAIM' for c in result['contradictions'])
    assert all(s['source_id']!='reversal-test' for c in result['contradictions'] for s in c['sources'])
