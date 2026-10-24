"""Independent, typed boundaries for candidate uncertainty scoring."""
from dataclasses import replace
from datetime import datetime
from uuid import uuid4

import pytest

from promisekeeper.application.evaluations import _uncertainty_correct
from promisekeeper.contracts.investigations import InvestigatorOutput
from promisekeeper.fixtures.catalogue import fresh_copy,apply_event,variant_definition


def context(variant=None, *, updated=False, case_id=None):
    fixture=fresh_copy(variant)
    if updated:fixture=apply_event(fixture,'PK-003-U1')
    case_id=case_id or (variant_definition(variant)['case_id'] if variant else 'PK-003')
    return fixture.cases[case_id],fixture.evaluation_at


def output(*,kind=None,field=None,sources=()):
    spans=[dict(evidence_version_id=str(s.id),source_id=s.source_id,start=0,end=len(s.original_content),quote=s.original_content) for s in sources]
    return InvestigatorOutput.model_validate(dict(schema_version='1',snapshot_id=str(uuid4()),commitments=[],payment_claims=[],
        contradictions=[dict(kind=kind,sources=spans)] if kind else [],unresolved=[dict(field=field,sources=spans)] if field else []))


def ledger(oracle,suffix='L2'):
    return next(p for p in oracle.evidence.payments if p.source.source_id.endswith('-'+suffix))


def change_payment(oracle,payment,**fields):
    changed=replace(payment,**fields)
    return replace(oracle,evidence=replace(oracle.evidence,payments=tuple(changed if p.source.id==payment.source.id else p for p in oracle.evidence.payments)))


@pytest.mark.parametrize('variant',['FV-07-CURRENCY','FV-07-OVERPAYMENT'])
def test_same_reference_claim_ledger_known_disagreement_is_supported(variant):
    oracle,at=context(variant);claim=oracle.extraction.claims[0];payment=ledger(oracle)
    assert _uncertainty_correct(output(kind='PAYMENT_CLAIM',sources=[claim.source,payment.source]),oracle,at) is True


@pytest.mark.parametrize('change',['unrelated_reference','non_authoritative','unavailable','matching_format','invoice_arithmetic'])
def test_claim_disagreement_rejects_unrelated_untrusted_equivalent_and_arithmetic(change):
    oracle,at=context(updated=True);claim=oracle.extraction.claims[0];payment=ledger(oracle)
    if change=='unrelated_reference':oracle=change_payment(oracle,payment,transaction_ref='OTHER',amount_text='70,000.00')
    elif change=='non_authoritative':oracle=change_payment(oracle,payment,source=replace(payment.source,authoritative=False),amount_text='70,000.00')
    elif change=='unavailable':oracle=change_payment(oracle,payment,source=replace(payment.source,availability='UNAVAILABLE'),amount_text='70,000.00')
    elif change=='matching_format':oracle=change_payment(oracle,payment,amount_text='60000')
    sources=[claim.source,oracle.evidence.invoices[0].source] if change=='invoice_arithmetic' else [claim.source,ledger(oracle).source]
    assert _uncertainty_correct(output(kind='PAYMENT_CLAIM',sources=sources),oracle,at) is False


@pytest.mark.parametrize('day,expected',[('2026-10-21T18:45:00+00:00',False),('2026-10-23T12:00:00+05:30',True)])
def test_claim_payment_day_is_compared_in_original_claim_timezone(day,expected):
    oracle,at=context(updated=True);payment=ledger(oracle)
    oracle=change_payment(oracle,payment,source=replace(payment.source,event_at=datetime.fromisoformat(day)))
    assert _uncertainty_correct(output(kind='PAYMENT_CLAIM',sources=[oracle.extraction.claims[0].source,ledger(oracle).source]),oracle,at) is expected


def test_valid_correction_removes_obsolete_claim_disagreement():
    oracle,at=context('FV-07-OVERPAYMENT');old=ledger(oracle)
    corrected=replace(old,amount_text='60,000.00',source=replace(old.source,id=uuid4(),source_id='PK-003-CORRECTION',version=2,supersedes_version_id=old.source.id))
    oracle=replace(oracle,evidence=replace(oracle.evidence,payments=(*oracle.evidence.payments,corrected)))
    assert _uncertainty_correct(output(kind='PAYMENT_CLAIM',sources=[oracle.extraction.claims[0].source,old.source]),oracle,at) is False
    assert _uncertainty_correct(output(field='AMOUNT',sources=[old.source]),oracle,at) is False


@pytest.mark.parametrize('kind,expected',[('OTHER_CANDIDATE',True),('INVOICE_FACT',False),('PAYMENT_CLAIM',False)])
def test_ledger_conflict_has_explicit_category_boundary(kind,expected):
    oracle,at=context('FV-14-PAYMENT');payments=oracle.evidence.payments
    assert _uncertainty_correct(output(kind=kind,sources=[p.source for p in payments]),oracle,at) is expected


@pytest.mark.parametrize('variant,field,expected',[
    ('FV-07-MISSING','AMOUNT',True),('FV-07-PRECISION','AMOUNT',True),('FV-07-CURRENCY','CURRENCY',True),
    ('FV-07-CURRENCY','AMOUNT',False),('FV-07-MISSING','CURRENCY',False),('FV-07-OVERPAYMENT','AMOUNT',True),
])
def test_financial_unknown_is_supported_only_for_the_exact_missing_invalid_or_disputed_field(variant,field,expected):
    oracle,at=context(variant)
    assert _uncertainty_correct(output(field=field,sources=[ledger(oracle).source]),oracle,at) is expected


def test_unrelated_known_invoice_field_does_not_inherit_another_record_gap():
    oracle,at=context('FV-07-MISSING')
    assert _uncertainty_correct(output(field='AMOUNT',sources=[oracle.evidence.invoices[0].source]),oracle,at) is False


def test_invoice_formatting_equivalence_is_not_a_contradiction():
    oracle,at=context(case_id='PK-001');invoice=oracle.evidence.invoices[0]
    second=replace(invoice,amount_text='120000',due_text='2026-10-10',source=replace(invoice.source,id=uuid4(),source_id='PK-001-I2'))
    oracle=replace(oracle,evidence=replace(oracle.evidence,invoices=(invoice,second)))
    assert _uncertainty_correct(output(kind='INVOICE_FACT',sources=[invoice.source,second.source]),oracle,at) is False


def test_actual_invoice_record_conflict_is_supported():
    oracle,at=context('FV-14-INVOICE')
    assert _uncertainty_correct(output(kind='INVOICE_FACT',sources=[i.source for i in oracle.evidence.invoices]),oracle,at) is True


def test_resolved_ledger_correction_is_not_an_active_conflict():
    oracle,at=context('FV-14-PAYMENT');first,old=oracle.evidence.payments
    corrected=replace(old,amount_text=first.amount_text,source=replace(old.source,id=uuid4(),source_id='PK-001-CORRECTION',version=2,supersedes_version_id=old.source.id))
    oracle=replace(oracle,evidence=replace(oracle.evidence,payments=(*oracle.evidence.payments,corrected)))
    assert _uncertainty_correct(output(kind='OTHER_CANDIDATE',sources=[first.source,old.source]),oracle,at) is False


def test_ledger_reference_is_required_even_when_amounts_differ():
    oracle,at=context('FV-14-PAYMENT');payment=oracle.evidence.payments[-1]
    oracle=change_payment(oracle,payment,transaction_ref='OTHER')
    assert _uncertainty_correct(output(kind='OTHER_CANDIDATE',sources=[p.source for p in oracle.evidence.payments]),oracle,at) is False


@pytest.mark.parametrize('use_reversal',[True,False])
def test_reversal_lifecycle_is_not_a_factual_contradiction_of_the_earlier_payment_claim(use_reversal):
    oracle,at=context('FV-06-REVERSAL')
    reversal=next(p for p in oracle.evidence.payments if p.reverses_payment_version_id is not None)
    source=reversal.source if use_reversal else next(p.source for p in oracle.evidence.payments if p.source.id==reversal.reverses_payment_version_id)
    assert _uncertainty_correct(output(kind='PAYMENT_CLAIM',sources=[oracle.extraction.claims[0].source,source]),oracle,at) is False
