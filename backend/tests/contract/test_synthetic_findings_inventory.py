"""Hand-declared synthetic identities complement the 51 frozen projections.

Production findings are the actual under test, never the expected generator.
Lifecycle reversal/fork descendants also have dedicated Task 1 boundary tests.
"""
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

import pytest

from promisekeeper.application.evaluation_findings import score_findings
from promisekeeper.fixtures.catalogue import fresh_copy,apply_event


def expected(*,questions=(),contradictions=(),financial=(),commitment=(),observations=()):
    return dict(contradictions=[dict(kind=kind,sources=list(sources)) for kind,sources in contradictions],
        unresolved_questions=[dict(field=field,sources=[source]) for field,source in questions],
        financial_issues=[dict(code=code,sources=list(sources)) for code,sources in financial],
        commitment_issues=[dict(code=code,sources=list(sources)) for code,sources in commitment],
        evidence_observations=[dict(subject='LEDGER',field='availability',value='AVAILABLE',source_id=None),
            dict(subject='LEDGER',field='complete',value=True,source_id=None),*observations])


def actual(case,extraction,at):
    from promisekeeper.application.derived_findings import derive_findings
    from promisekeeper.domain.recommendations import recommend
    from promisekeeper.domain.commitments import reconcile_commitments
    packet=dict(snapshot_id=str(uuid4()),snapshot_hash='b'*64,ledger_availability=str(case.ledger_availability),ledger_complete=case.ledger_complete,
        evidence=[dict(id=str(r.source.id),stable_source_id=r.source.source_id,availability=str(r.source.availability),original_content=r.source.original_content)
                  for r in (*case.invoices,*case.payments,*case.messages,*case.attributions)])
    recommendation=recommend(case,extraction,at)
    result=derive_findings(case,extraction,recommendation,reconcile_commitments(case,extraction,recommendation.financial),packet)
    result.update(snapshot_id=packet['snapshot_id'],snapshot_hash=packet['snapshot_hash'],financial_facts=dict(issues=result.pop('financial_issues')))
    return result,packet,recommendation


def check(case,extraction,at,wanted):
    result,packet,recommendation=actual(case,extraction,at)
    checks=score_findings(result,packet,wanted)
    assert all(checks.values()),(checks,result,wanted)
    return recommendation


@pytest.mark.parametrize('amount',['60,000','60000.0','60000.00'])
def test_equivalent_money_formatting_has_no_findings(amount):
    fixture=apply_event(fresh_copy(),'PK-003-U1');item=fixture.cases['PK-003']
    payments=tuple(replace(p,amount_text=amount) if p.source.source_id=='PK-003-L2' else p for p in item.evidence.payments)
    result=check(replace(item.evidence,payments=payments),item.extraction,fixture.evaluation_at,expected())
    assert result.action=='CLOSE' and result.financial.balance_minor==0


@pytest.mark.parametrize('timestamp,dispute',[
    ('2026-10-22T04:30:00+00:00',False), # same original instant in UTC
    ('2026-10-23T10:00:00+05:30',True), # a different known payment day
])
def test_equivalent_timezone_and_different_known_payment_day(timestamp,dispute):
    fixture=apply_event(fresh_copy(),'PK-003-U1');item=fixture.cases['PK-003']
    payments=tuple(replace(p,source=replace(p.source,event_at=datetime.fromisoformat(timestamp))) if p.source.source_id=='PK-003-L2' else p for p in item.evidence.payments)
    wanted=(expected(contradictions=[('PAYMENT_CLAIM',['PK-003-L2','PK-003-M1'])],
        questions=[('PAYMENT_DATE','PK-003-L2'),('PAYMENT_DATE','PK-003-M1')]) if dispute else expected())
    check(replace(item.evidence,payments=payments),item.extraction,fixture.evaluation_at,wanted)


@pytest.mark.parametrize('field,value,questions,issues',[
    ('speaker',None,[('SPEAKER','PK-003-M1')],[]),
    ('transaction_reference_text',None,[('PAYMENT_REFERENCE','PK-003-M1')],[]),
    ('payment_date_text',None,[('PAYMENT_DATE','PK-003-M1')],[('MISSING_EXTRACTION',['PK-003-M1'])]),
])
def test_exact_claim_field_gaps_do_not_spread_to_other_sources(field,value,questions,issues):
    fixture=apply_event(fresh_copy(),'PK-003-U1');item=fixture.cases['PK-003']
    extraction=replace(item.extraction,claims=(replace(item.extraction.claims[0],**{field:value}),))
    check(item.evidence,extraction,fixture.evaluation_at,expected(questions=questions,commitment=issues))


def test_unknown_promise_amount_without_any_payment_is_not_attribution():
    fixture=fresh_copy('FV-02-PROMISE');item=fixture.cases['PK-001']
    check(replace(item.evidence,payments=()),item.extraction,fixture.evaluation_at,
          expected(questions=[('AMOUNT','PK-001-M1'),('CURRENCY','PK-001-M1')]))


def test_unavailable_empty_invoice_uses_metadata_and_issue_refs_without_fake_spans():
    fixture=fresh_copy();item=fixture.cases['PK-001'];invoice=item.evidence.invoices[0]
    invoice=replace(invoice,amount_text=None,source=replace(invoice.source,availability='UNREADABLE',original_content=''))
    check(replace(item.evidence,invoices=(invoice,)),item.extraction,fixture.evaluation_at,
          expected(questions=[('ATTRIBUTION','PK-001-M1')],financial=[('INVOICE_UNAVAILABLE',['PK-001-I1']),('MISSING_INVOICE_AUTHORITY',['PK-001-I1'])],
                   observations=[dict(subject='SOURCE',field='availability',value='UNREADABLE',source_id='PK-001-I1'),
                                 dict(subject='SOURCE',field='content_present',value=False,source_id='PK-001-I1')]))


def test_incomplete_lookup_retains_known_source_fields_and_exact_issue_refs():
    fixture=fresh_copy();item=fixture.cases['PK-001']
    # Controller ruling: frozen financial rules clear eligible credits for an
    # incomplete lookup; no actual unresolved eligible link exists here.
    wanted=expected(financial=[('LEDGER_INCOMPLETE',['PK-001-L1'])])
    wanted['evidence_observations'][1]['value']=False
    check(replace(item.evidence,ledger_complete=False),item.extraction,fixture.evaluation_at,wanted)


@pytest.mark.parametrize('kind',['valid','invalid_target','cycle','fork'])
def test_correction_lifecycle_has_explicit_inventory(kind):
    fixture=fresh_copy();item=fixture.cases['PK-001'];invoice=item.evidence.invoices[0]
    new=replace(invoice,source=replace(invoice.source,id=uuid4(),source_id='correction',supersedes_version_id=invoice.source.id))
    financial=[]
    if kind=='invalid_target':
        new=replace(new,source=replace(new.source,supersedes_version_id=uuid4()))
        financial=[('INVALID_CORRECTION',['correction'])]
    elif kind=='cycle':
        new=replace(new,source=replace(new.source,supersedes_version_id=new.source.id))
        financial=[('CYCLIC_CORRECTION',['correction'])]
    records=(invoice,new)
    if kind=='fork':
        sibling=replace(new,source=replace(new.source,id=uuid4(),source_id='sibling'))
        records=(*records,sibling)
        financial=[('CONFLICTING_CORRECTIONS',['PK-001-I1','correction','sibling']),('MISSING_INVOICE_AUTHORITY',[])]
    check(replace(item.evidence,invoices=records),item.extraction,fixture.evaluation_at,
          expected(questions=[('ATTRIBUTION','PK-001-M1')],financial=financial))


def test_complete_close_retains_invoice_issue_without_inventing_invoice_date_question():
    fixture=apply_event(fresh_copy(),'PK-003-U1');item=fixture.cases['PK-003']
    invoice=replace(item.evidence.invoices[0],due_text=None)
    recommendation=check(replace(item.evidence,invoices=(invoice,)),item.extraction,fixture.evaluation_at,
                         expected(financial=[('INVOICE_DATE_UNRESOLVED',['PK-003-I1'])]))
    assert recommendation.status=='COMPLETE' and recommendation.action=='CLOSE' and recommendation.financial.balance_minor==0


def test_multiple_issues_are_scored_separately_when_extraction_changes_action():
    fixture=apply_event(fresh_copy(),'PK-003-U1');item=fixture.cases['PK-003']
    invoice=replace(item.evidence.invoices[0],due_text=None)
    claim=replace(item.extraction.claims[0],payment_date_text=None)
    recommendation=check(replace(item.evidence,invoices=(invoice,)),replace(item.extraction,claims=(claim,)),fixture.evaluation_at,
        expected(questions=[('PAYMENT_DATE','PK-003-M1')],financial=[('INVOICE_DATE_UNRESOLVED',['PK-003-I1'])],
                 commitment=[('MISSING_EXTRACTION',['PK-003-M1'])]))
    # Missing extraction deliberately remains a LIMITED/VERIFY_PAYMENT trigger;
    # the invoice issue still survives independently of this action decision.
    assert recommendation.status=='LIMITED' and recommendation.action=='VERIFY_PAYMENT' and recommendation.financial.balance_minor==0


def test_multiple_issues_survive_complete_close_without_changing_balance_or_action():
    fixture=fresh_copy();item=fixture.cases['PK-001'];candidate=item.extraction.commitments[0]
    raw=candidate.source.original_content.replace(candidate.amount_text,candidate.amount_text+'.001')
    source=replace(candidate.source,original_content=raw)
    candidate=replace(candidate,source=source,quote=raw,start=0,end=len(raw),amount_text=candidate.amount_text+'.001')
    case=replace(item.evidence,invoices=(replace(item.evidence.invoices[0],due_text=None),),
        payments=(replace(item.evidence.payments[0],amount_text='120000'),),
        messages=tuple(replace(m,source=source) if m.source.id==source.id else m for m in item.evidence.messages),
        anchors=tuple(replace(a,clause_end=len(raw)) if a.evidence_version_id==source.id else a for a in item.evidence.anchors))
    recommendation=check(case,replace(item.extraction,commitments=(candidate,)),fixture.evaluation_at,
        expected(questions=[('AMOUNT','PK-001-M1'),('ATTRIBUTION','PK-001-M1')],
            financial=[('INVOICE_DATE_UNRESOLVED',['PK-001-I1'])],commitment=[('INVALID_PROMISE_AMOUNT',['PK-001-M1'])]))
    assert recommendation.action=='CLOSE' and recommendation.status=='COMPLETE' and recommendation.financial.balance_minor==0


@pytest.mark.parametrize('different_days',[False,True])
def test_three_conflicting_payments_have_each_true_pair_once(different_days):
    fixture=fresh_copy();item=fixture.cases['PK-003'];payment=item.evidence.payments[0]
    records=tuple(replace(payment,amount_text=str(i),transaction_ref='SAME',source=replace(payment.source,id=uuid4(),source_id=f'L{i}',
        event_at=datetime.fromisoformat(f'2026-10-{20+i if different_days else 21}T10:00:00+05:30'))) for i in (1,2,3))
    case=replace(item.evidence,payments=records,messages=(),anchors=())
    questions=[('AMOUNT','L1'),('AMOUNT','L2'),('AMOUNT','L3')]
    if different_days:questions += [('PAYMENT_DATE','L1'),('PAYMENT_DATE','L2'),('PAYMENT_DATE','L3')]
    check(case,replace(item.extraction,claims=()),fixture.evaluation_at,
        expected(questions=questions,contradictions=[('OTHER_CANDIDATE',['L1','L2']),('OTHER_CANDIDATE',['L1','L3']),('OTHER_CANDIDATE',['L2','L3'])],
            financial=[('CONFLICTING_PAYMENTS',['L1','L2','L3'])]))
