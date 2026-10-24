"""Quality, coverage and safe availability are distinct acceptance dimensions."""
from copy import deepcopy
import pytest
from promisekeeper.application.evaluation_qualification import qualify, classify_run
from promisekeeper.application.evaluation_qualification import QUALITY_FIELDS,EVALUATOR_VERSION,CRITERIA_VERSION,manifest_hash
from promisekeeper.application.evaluation_findings import INVENTORY_VERSION,INVENTORY_HASH,FINDINGS_PROFILE
from promisekeeper.agents.protocol import PROMPT_VERSION,EXTRACTION_POLICY_VERSION
from promisekeeper.agents.nebius import ADAPTER_VERSION


def step(name='EXTRACTION',number=1,kind='INITIAL',outcome='TRANSIENT_FAILURE',code='PROVIDER_REJECTED_REQUEST'):
    return dict(step_name=name,invocation_number=number,invocation_kind=kind,outcome=outcome,failure_code=code,
                started_at='2026-10-24T00:00:01+00:00',ended_at='2026-10-24T00:00:03+00:00')


def run(case='A',repeat=1,*,gap=False):
    row=dict(case=case,repeat=repeat,attempt_status='INCOMPLETE' if gap else 'COMPLETE',
        failure_code='PROVIDER_REJECTED_REQUEST' if gap else None,response_ids=[] if gap else ['real-response'],returned_models=[] if gap else ['explicit-model'],
        extraction_correct=None if gap else True,source_validation_correct=None if gap else True,uncertainty_correct=None if gap else True,
        deterministic_outcome_correct=None if gap else True,latency_seconds=7,action=None if gap else 'CLOSE',result_present=not gap,
        attempt_timing=dict(started_at='2026-10-24T00:00:00+00:00',terminal_at='2026-10-24T00:00:07+00:00',deadline_at='2026-10-24T00:00:55+00:00'),
        progress=[step('EVIDENCE_LOOKUP',outcome='SUCCEEDED',code=None),
                  *([step(),step(number=2,kind='AUTO_RETRY')] if gap else [step(outcome='SUCCEEDED',code=None)])])
    row.update({key:None if gap else True for key in QUALITY_FIELDS})
    return row


def identity():
    return dict(suite='live',agent_mode='LIVE',provider='NEBIUS',requested_model='explicit-model',
                prompt_version=PROMPT_VERSION,adapter_version=ADAPTER_VERSION,extraction_schema_version='1',
                extraction_policy_version=EXTRACTION_POLICY_VERSION,findings_version=FINDINGS_PROFILE,
                inventory_version=INVENTORY_VERSION,inventory_hash=INVENTORY_HASH,temporal_policy_version='deadline-by-1',
                evaluator_version=EVALUATOR_VERSION,criteria_version=CRITERIA_VERSION)


def report(rows):
    return identity() | dict(repeats=3,manifest_entries=['A','B'],manifest_definitions=[],manifest_hash=manifest_hash([]),runs=rows)


def complete():return [run(case,repeat) for repeat in (1,2,3) for case in ('A','B')]


def test_transient_529_gap_qualifies_only_with_actual_coverage_for_every_entry():
    rows=complete();rows[0]=run('A',1,gap=True)
    result=qualify(report(rows))
    assert result['status']=='PASS_WITH_AVAILABILITY_GAPS'
    assert result['coverage']['covered_entries']==2
    assert result['quality']==dict(returned_runs=5,correct_runs=5,incorrect_runs=0)
    assert result['availability']['incomplete_provider_runs']==1
    assert classify_run(rows[0])=='INCOMPLETE_PROVIDER'
    assert rows[0]['extraction_correct'] is None


def test_all_repeats_unavailable_for_one_entry_block_qualification():
    rows=[run(case,repeat,gap=case=='A') for repeat in (1,2,3) for case in ('A','B')]
    result=qualify(report(rows))
    assert result['status']=='BLOCKED'
    assert result['coverage']['missing_entries']==['A']


def test_one_incorrect_output_blocks_even_when_other_repeats_pass():
    rows=complete();rows[0]['findings_soundness_correct']=False
    assert qualify(report(rows))['status']=='FAIL'


@pytest.mark.parametrize('code',['PROVIDER_REJECTED_REQUEST','INVESTIGATOR_REFUSAL','INVALID_INVESTIGATOR_OUTPUT','CAPABILITY_UNAVAILABLE','INVESTIGATION_FAILED'])
def test_nontransient_400_auth_refusal_and_unclassified_failures_block(code):
    rows=complete();rows[0]=run('A',1,gap=True);rows[0]['failure_code']=code
    rows[0]['progress'][-1].update(outcome='FAILED',failure_code=code)
    assert qualify(report(rows))['status']=='FAIL'


@pytest.mark.parametrize('mutation',['third_retry','action','late','over_budget','returned_invalid','unknown_code','bad_number','other_step_failed','missing_timing'])
def test_availability_cannot_hide_unsafe_or_unknown_attempts(mutation):
    row=run(gap=True)
    if mutation=='third_retry':row['progress'].append(step(number=3,kind='AUTO_RETRY'))
    elif mutation=='action':row['action']='CLOSE'
    elif mutation=='late':row['attempt_timing']['terminal_at']='2026-10-24T00:00:56+00:00'
    elif mutation=='over_budget':row['latency_seconds']=56
    elif mutation=='returned_invalid':row.update(response_ids=['invalid-response'],source_validation_correct=False)
    elif mutation=='unknown_code':row['progress'][-1]['failure_code']='UNKNOWN'
    elif mutation=='bad_number':row['progress'][-1]['invocation_number']=4
    elif mutation=='other_step_failed':row['progress'][0]['outcome']='FAILED'
    elif mutation=='missing_timing':row.pop('attempt_timing')
    assert classify_run(row)=='FAIL'


def test_missing_or_duplicate_planned_run_is_not_a_complete_qualification():
    assert qualify(report(complete()[:-1]))['status']=='BLOCKED'
    rows=complete();rows[-1]=deepcopy(rows[0])
    assert qualify(report(rows))['status']=='FAIL'


def test_successful_results_must_also_respect_safety_and_budget():
    rows=complete();rows[0]['progress'] += [step(number=2,kind='AUTO_RETRY'),step(number=3,kind='AUTO_RETRY')]
    assert qualify(report(rows))['status']=='FAIL'


def test_all_correct_actual_returns_are_plain_pass():
    result=qualify(report(complete()))
    assert result['status']=='PASS'
    assert result['safety']['unsafe_runs']==0


def test_subset_and_wrong_repeat_count_can_never_qualify_gate_iii():
    from promisekeeper.application.evaluations import evaluation_manifest
    from promisekeeper.application.evaluation_qualification import manifest_hash
    canonical=[entry['id'] for entry in evaluation_manifest()]
    assert len(canonical)==51
    for entries,repeats in [(canonical,3),(canonical,2),(canonical[:1],3)]:
        definitions=[entry for entry in evaluation_manifest() if entry['id'] in entries]
        candidate=identity() | dict(manifest_entries=entries,manifest_definitions=definitions,manifest_hash=manifest_hash(definitions),repeats=repeats,runs=[run(case,repeat) for case in entries for repeat in range(1,repeats+1)])
        result=qualify(candidate)
        assert result['status']=='PASS'
        assert result['qualified'] is (len(entries)==51 and repeats==3)
        assert result['qualification_scope']==('RELEASE' if len(entries)==51 and repeats==3 else 'SUBSET')


@pytest.mark.parametrize('field,value',[('variant','FV-07-MISSING'),('case_id','PK-002'),('events',['PK-001-U1'])])
def test_same_catalogue_ids_with_changed_definitions_are_never_release_coverage(field,value):
    from promisekeeper.application.evaluations import evaluation_manifest
    from promisekeeper.application.evaluation_qualification import manifest_hash
    definitions=evaluation_manifest();definitions[0][field]=value
    entries=[entry['id'] for entry in definitions]
    candidate=identity() | dict(manifest_entries=entries,manifest_definitions=definitions,manifest_hash=manifest_hash(definitions),repeats=3,
                   runs=[run(case,repeat) for case in entries for repeat in (1,2,3)])
    result=qualify(candidate)
    assert result['qualification_scope']=='SUBSET'
    assert result['qualified'] is False


def test_misdeclared_manifest_hash_cannot_qualify_release():
    from promisekeeper.application.evaluations import evaluation_manifest
    definitions=evaluation_manifest();entries=[entry['id'] for entry in definitions]
    candidate=identity() | dict(manifest_entries=entries,manifest_definitions=definitions,manifest_hash='0'*64,repeats=3,
                   runs=[run(case,repeat) for case in entries for repeat in (1,2,3)])
    assert qualify(candidate)['qualified'] is False


@pytest.mark.parametrize('field,value',[
    ('suite','stub'),('agent_mode','STUB'),('provider','OTHER'),('requested_model',None),
    ('prompt_version','old'),('adapter_version','old'),('extraction_schema_version','old'),
    ('extraction_policy_version','old'),('findings_version','old'),('inventory_version','old'),
    ('inventory_hash','0'*64),('evaluator_version','3'),('criteria_version','gate-iii-live-2'),
    ('temporal_policy_version','old'),
])
def test_qualification_rejects_wrong_or_missing_identity(field,value):
    candidate=report(complete());candidate[field]=value
    assert qualify(candidate)['status']=='FAIL'
    candidate.pop(field)
    assert qualify(candidate)['status'] == 'FAIL'


@pytest.mark.parametrize('mutation',['missing_model','wrong_model','missing_response','empty_response','count_mismatch'])
def test_all_true_mocked_checks_cannot_replace_returned_output_provenance(mutation):
    candidate=report(complete());row=candidate['runs'][0]
    if mutation=='missing_model':row['returned_models']=[]
    elif mutation=='wrong_model':row['returned_models']=['other-model']
    elif mutation=='missing_response':row['response_ids']=[]
    elif mutation=='empty_response':row['response_ids']=['']
    else:row['returned_models']*=2
    assert qualify(candidate)['status']=='FAIL'


@pytest.mark.parametrize('field',QUALITY_FIELDS)
def test_each_quality_dimension_blocks_qualification(field):
    candidate=report(complete());candidate['runs'][0][field]=False
    assert qualify(candidate)['status']=='FAIL'


def test_observed_failure_cannot_become_availability_after_no_response():
    row=run(gap=True);row['extraction_policy_correct']=False
    assert classify_run(row)=='FAIL'


def test_changed_runtime_manifest_cannot_redefine_the_pinned_release(monkeypatch):
    from promisekeeper.application import evaluations
    definitions=evaluations.evaluation_manifest();definitions[0]['case_id']='PK-003'
    monkeypatch.setattr(evaluations,'evaluation_manifest',lambda:definitions)
    entries=[e['id'] for e in definitions]
    candidate=identity() | dict(manifest_entries=entries,manifest_definitions=definitions,manifest_hash=manifest_hash(definitions),
        repeats=3,runs=[run(case,repeat) for case in entries for repeat in (1,2,3)])
    assert qualify(candidate)['qualified'] is False


def test_returned_model_evidence_without_response_id_is_not_a_provider_gap():
    row=run(gap=True);row['returned_models']=['explicit-model']
    assert classify_run(row)=='FAIL'
