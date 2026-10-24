"""Independent static identities and adversarial provenance, without DTO validation."""
from copy import deepcopy
from datetime import datetime
from uuid import uuid4

import pytest

from promisekeeper.application.evaluation_findings import load_inventory, score_findings
from promisekeeper.application.evaluations import evaluation_manifest


def synthetic():
    sid, vid = str(uuid4()), str(uuid4())
    packet = dict(snapshot_id=sid, snapshot_hash='a'*64, ledger_availability='AVAILABLE', ledger_complete=True,
                  evidence=[dict(id=vid, stable_source_id='M1', availability='AVAILABLE', original_content='₹🙂 pay')])
    span = dict(source_id='M1', evidence_version_id=vid, start=0, end=2, quote='₹🙂')
    expected = dict(contradictions=[], unresolved_questions=[dict(field='AMOUNT', sources=['M1'])],
                    financial_issues=[], commitment_issues=[], evidence_observations=[
                        dict(subject='LEDGER', field='availability', value='AVAILABLE', source_id=None),
                        dict(subject='LEDGER', field='complete', value=True, source_id=None)])
    actual = dict(snapshot_id=sid, snapshot_hash=packet['snapshot_hash'], findings_version='deterministic-1',
                  contradictions=[], unresolved_questions=[dict(field='AMOUNT', sources=[span])],
                  financial_facts=dict(issues=[]), commitment_issues=[], evidence_observations=[
                      dict(subject='LEDGER', field='availability', value='AVAILABLE', source=None,
                           snapshot_id=sid, snapshot_hash=packet['snapshot_hash']),
                      dict(subject='LEDGER', field='complete', value=True, source=None,
                           snapshot_id=sid, snapshot_hash=packet['snapshot_hash'])])
    return actual, packet, expected


def test_correct_literal_inventory_and_unicode_spans_pass():
    assert all(score_findings(*synthetic()).values())


@pytest.mark.parametrize('mutation,failed', [
    ('omit','findings_completeness_correct'), ('extra','findings_soundness_correct'),
    ('duplicate','findings_duplicates_correct'), ('version','findings_source_validation_correct'),
    ('unicode','findings_source_validation_correct'), ('quote','findings_source_validation_correct'),
    ('unavailable','findings_source_validation_correct'), ('snapshot','findings_source_validation_correct'),
    ('snapshot_hash','findings_source_validation_correct'), ('profile','findings_source_validation_correct'),
    ('duplicate_source','findings_source_validation_correct'), ('bool_offset','findings_source_validation_correct'),
    ('observation_value','findings_source_validation_correct'), ('observation_ref','findings_source_validation_correct'),
])
def test_tampering_fails_independent_dimension(mutation, failed):
    result, packet, expected = synthetic()
    span = result['unresolved_questions'][0]['sources'][0]
    if mutation=='omit': result['unresolved_questions']=[]
    elif mutation=='extra': result['unresolved_questions'].append(dict(field='CURRENCY',sources=[deepcopy(span)]))
    elif mutation=='duplicate': result['unresolved_questions']*=2
    elif mutation=='version': span['evidence_version_id']=str(uuid4())
    elif mutation=='unicode': span['end']=3
    elif mutation=='quote': span['quote']='fake'
    elif mutation=='unavailable': packet['evidence'][0]['availability']='UNAVAILABLE'
    elif mutation=='snapshot': result['evidence_observations'][0]['snapshot_id']=str(uuid4())
    elif mutation=='snapshot_hash': result['snapshot_hash']='b'*64
    elif mutation=='profile': result['findings_version']='old'
    elif mutation=='duplicate_source': result['unresolved_questions'][0]['sources']*=2
    elif mutation=='bool_offset': span['start']=False
    elif mutation=='observation_value': result['evidence_observations'][1]['value']=1
    elif mutation=='observation_ref': result['evidence_observations'][0]['source']=dict(source_id='M1',evidence_version_id=span['evidence_version_id'])
    assert score_findings(result,packet,expected)[failed] is False


def test_empty_inventory_still_requires_exact_snapshot_and_observations():
    result, packet, expected=synthetic()
    result['unresolved_questions']=[];expected['unresolved_questions']=[]
    assert all(score_findings(result,packet,expected).values())
    result['evidence_observations'][0]['snapshot_id']=str(uuid4())
    assert score_findings(result,packet,expected)['findings_source_validation_correct'] is False


@pytest.mark.parametrize('mutation',['missing','duplicate','foreign','wrong_source'])
def test_issue_version_refs_must_exactly_cover_owned_sources(mutation):
    result, packet, expected=synthetic()
    ref={k:v for k,v in result['unresolved_questions'][0]['sources'][0].items() if k in {'source_id','evidence_version_id'}}
    result['financial_facts']['issues']=[dict(code='UNKNOWN_AMOUNT',detail='unknown',sources=['M1'],source_versions=[ref])]
    expected['financial_issues']=[dict(code='UNKNOWN_AMOUNT',sources=['M1'])]
    assert all(score_findings(result,packet,expected).values())
    refs=result['financial_facts']['issues'][0]['source_versions']
    if mutation=='missing': refs.clear()
    elif mutation=='duplicate': refs.append(deepcopy(ref))
    elif mutation=='foreign': ref['evidence_version_id']=str(uuid4())
    else: ref['source_id']='foreign'
    assert score_findings(result,packet,expected)['findings_source_validation_correct'] is False


def test_inventory_pin_and_manifest_definitions_are_binding():
    inventory=load_inventory(evaluation_manifest())
    assert len(inventory['entries'])==51
    definitions=evaluation_manifest();definitions[0]['case_id']='PK-003'
    with pytest.raises(ValueError):load_inventory(definitions)


def test_inventory_changed_bytes_or_version_fail_closed(tmp_path,monkeypatch):
    from promisekeeper.application import evaluation_findings
    raw=evaluation_findings.INVENTORY_PATH.read_bytes()
    path=tmp_path/'inventory.json';path.write_bytes(raw+b'\n')
    monkeypatch.setattr(evaluation_findings,'INVENTORY_PATH',path)
    with pytest.raises(ValueError):load_inventory(evaluation_manifest())
    path.write_bytes(raw.replace(b'gate-iii-findings-1',b'gate-iii-findings-X'))
    with pytest.raises(ValueError):load_inventory(evaluation_manifest())


@pytest.mark.parametrize('availability',['MISSING','UNREADABLE'])
def test_all_captured_availability_enum_values_are_valid_observations(availability):
    result,packet,expected=synthetic()
    packet['ledger_availability']=availability
    result['evidence_observations'][0]['value']=availability
    expected['evidence_observations'][0]['value']=availability
    assert all(score_findings(result,packet,expected).values())


@pytest.mark.parametrize('entry',evaluation_manifest(),ids=lambda e:e['id'])
def test_all_51_oracle_projections_match_independent_inventory(entry):
    # Production derivation is ONLY the actual under test. Expected identities
    # are frozen, independently authored JSON; no derivation generates them.
    from promisekeeper.application.derived_findings import derive_findings
    from promisekeeper.domain.commitments import reconcile_commitments
    from promisekeeper.domain.recommendations import recommend
    from promisekeeper.fixtures.catalogue import fresh_copy,apply_event
    fixture=fresh_copy(entry['variant'])
    for event in entry['events']:fixture=apply_event(fixture,event)
    oracle=fixture.cases[entry['case_id']];case=oracle.evidence
    packet=dict(snapshot_id=str(uuid4()),snapshot_hash='a'*64,ledger_availability=str(case.ledger_availability),ledger_complete=case.ledger_complete,
                evidence=[dict(id=str(r.source.id),stable_source_id=r.source.source_id,availability=str(r.source.availability),original_content=r.source.original_content)
                          for r in (*case.invoices,*case.payments,*case.messages,*case.attributions)])
    recommendation=recommend(case,oracle.extraction,fixture.evaluation_at)
    actual=derive_findings(case,oracle.extraction,recommendation,reconcile_commitments(case,oracle.extraction,recommendation.financial),packet)
    actual.update(snapshot_id=packet['snapshot_id'],snapshot_hash=packet['snapshot_hash'],financial_facts=dict(issues=actual.pop('financial_issues')))
    assert all(score_findings(actual,packet,load_inventory(evaluation_manifest())['entries'][entry['id']]).values())
    assert recommendation.action==oracle.expected['action']
    assert (str(recommendation.financial.balance_minor) if recommendation.financial.balance_minor is not None else None)==oracle.expected['balance_minor']
    expected_review=oracle.expected['review_at']
    assert recommendation.review_at==(datetime.fromisoformat(expected_review) if expected_review else None)
