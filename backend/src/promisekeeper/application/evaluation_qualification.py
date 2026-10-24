"""Versioned LIVE acceptance criteria; provider gaps never become successful runs."""
from collections import defaultdict
from datetime import datetime
import hashlib
import json
import math
from promisekeeper.agents.protocol import PROMPT_VERSION,EXTRACTION_POLICY_VERSION
from promisekeeper.agents.nebius import ADAPTER_VERSION
from promisekeeper.domain.dates import TEMPORAL_POLICY_VERSION
from promisekeeper.application.evaluation_findings import INVENTORY_VERSION,INVENTORY_HASH,FINDINGS_PROFILE,CANONICAL_MANIFEST_HASH

CRITERIA_VERSION='gate-iii-live-4'
CRITERIA_URI='reports/live-evaluation-criteria.md'
EVALUATOR_VERSION='5'


QUALITY_FIELDS=('extraction_correct','source_validation_correct','extraction_policy_correct',
                'findings_source_validation_correct','findings_soundness_correct','findings_completeness_correct',
                'findings_duplicates_correct','deterministic_outcome_correct')
TRANSIENT_CODES={'PROVIDER_REJECTED_REQUEST','INVESTIGATOR_UNAVAILABLE','INVESTIGATOR_TIMEOUT'}
QUALIFIED_STATUSES={'PASS','PASS_WITH_AVAILABILITY_GAPS'}


def manifest_hash(definitions):
    return hashlib.sha256(json.dumps(definitions,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()


def _instant(raw):
    value=datetime.fromisoformat(raw)
    if value.tzinfo is None or value.utcoffset() is None:raise ValueError('Unaware evidence')
    return value


def safety_correct(row):
    """Fail closed unless persisted terminal, budget and retry evidence agree."""
    try:
        timing=row['attempt_timing']
        started,terminal,deadline=(_instant(timing[key]) for key in ('started_at','terminal_at','deadline_at'))
        latency=row['latency_seconds']
        if not math.isfinite(latency) or not 0<=latency<=55:return False
        if not 0<(deadline-started).total_seconds()<=55 or not started<=terminal<=deadline:return False
        if row['attempt_status'] not in {'COMPLETE','LIMITED','INCOMPLETE'}:return False
        complete=row['attempt_status'] in {'COMPLETE','LIMITED'}
        if row['result_present'] is not complete:return False
        if complete:
            if row['action'] not in {'CLOSE','WAIT','FOLLOW_UP','VERIFY_PAYMENT'}:return False
        elif row['action'] is not None:return False
        grouped=defaultdict(list)
        for step in row['progress']:
            if not started<=_instant(step['started_at'])<=_instant(step['ended_at'])<=terminal:return False
            grouped[step['step_name']].append(step)
        if not grouped or 'EXTRACTION' not in grouped:return False
        if set(grouped)-{'EVIDENCE_LOOKUP','EXTRACTION','VALIDATION','RECONCILIATION'}:return False
        for steps in grouped.values():
            if not 1<=len(steps)<=2:return False
            for index,step in enumerate(steps):
                if step['invocation_number']!=index+1 or step['invocation_kind']!=('INITIAL' if index==0 else 'AUTO_RETRY'):return False
                if step['outcome'] not in {'SUCCEEDED','TRANSIENT_FAILURE','FAILED'}:return False
                if index and steps[index-1]['outcome']!='TRANSIENT_FAILURE':return False
        return True
    except (KeyError,ValueError,TypeError,OverflowError):return False


def classify_run(row):
    if not safety_correct(row):return 'FAIL'
    if row['result_present']:
        if not output_provenance_correct(row):return 'FAIL'
        return 'PASS' if all(row.get(key) is True for key in QUALITY_FIELDS) else 'FAIL'
    # A known wrong returned output can never be rewritten as unknown availability.
    if row.get('response_ids') or row.get('returned_models') or any(row.get(key) is not None for key in QUALITY_FIELDS):return 'FAIL'
    steps=row['progress'];extraction=[s for s in steps if s['step_name']=='EXTRACTION']
    if any(s['outcome']!='SUCCEEDED' for s in steps if s['step_name']!='EXTRACTION'):return 'FAIL'
    if any(s['outcome']!='TRANSIENT_FAILURE' or s['failure_code'] not in TRANSIENT_CODES for s in extraction):return 'FAIL'
    if row.get('failure_code')!=extraction[-1]['failure_code']:return 'FAIL'
    return 'INCOMPLETE_PROVIDER'


def output_provenance_correct(row, requested_model=None):
    ids=row.get('response_ids');models=row.get('returned_models')
    return (isinstance(ids,list) and isinstance(models,list) and bool(ids) and len(ids)==len(models)
            and all(isinstance(value,str) and bool(value.strip()) for value in ids+models)
            and (requested_model is None or all(model==requested_model for model in models)))


def qualification_identity_correct(report):
    expected=dict(suite='live',agent_mode='LIVE',provider='NEBIUS',prompt_version=PROMPT_VERSION,
                  adapter_version=ADAPTER_VERSION,extraction_schema_version='1',
                  extraction_policy_version=EXTRACTION_POLICY_VERSION,findings_version=FINDINGS_PROFILE,
                  temporal_policy_version=TEMPORAL_POLICY_VERSION,
                  inventory_version=INVENTORY_VERSION,inventory_hash=INVENTORY_HASH,
                  evaluator_version=EVALUATOR_VERSION,criteria_version=CRITERIA_VERSION)
    model=report.get('requested_model')
    return (all(report.get(key)==value for key,value in expected.items())
            and isinstance(model,str) and bool(model.strip()))


def qualify(report):
    from promisekeeper.application.evaluations import evaluation_manifest
    entries=report['manifest_entries'];repeats=report['repeats'];rows=report['runs']
    canonical=evaluation_manifest()
    definitions=report.get('manifest_definitions')
    hash_valid=definitions is not None and report.get('manifest_hash')==manifest_hash(definitions)
    canonical_valid=manifest_hash(canonical)==CANONICAL_MANIFEST_HASH
    scope='RELEASE' if (repeats==3 and len(entries)==51 and entries==[e['id'] for e in canonical]
                        and definitions==canonical and hash_valid and canonical_valid) else 'SUBSET'
    expected={(case,repeat) for case in entries for repeat in range(1,repeats+1)}
    actual=[(row['case'],row['repeat']) for row in rows]
    invalid_identity=len(set(actual))!=len(actual) or bool(set(actual)-expected) or len(set(entries))!=len(entries)
    statuses=[classify_run(row) for row in rows]
    for index,row in enumerate(rows):
        if row.get('response_ids') and not output_provenance_correct(row,report.get('requested_model')):statuses[index]='FAIL'
    covered={row['case'] for row,status in zip(rows,statuses) if status=='PASS'}
    missing_entries=sorted(set(entries)-covered)
    unsafe=sum(not safety_correct(row) for row in rows)
    observed=[row for row in rows if row.get('response_ids') or row.get('returned_models') or any(row.get(key) is not None for key in QUALITY_FIELDS)]
    correct=sum(all(row.get(key) is True for key in QUALITY_FIELDS) for row in observed)
    gap_count=statuses.count('INCOMPLETE_PROVIDER')
    blocking=statuses.count('FAIL')
    identity_valid=qualification_identity_correct(report)
    if invalid_identity or blocking or not identity_valid or not hash_valid or not canonical_valid:status='FAIL'
    elif not expected or missing_entries or set(actual)!=expected:status='BLOCKED'
    else:status='PASS_WITH_AVAILABILITY_GAPS' if gap_count else 'PASS'
    return dict(status=status,qualified=scope=='RELEASE' and status in QUALIFIED_STATUSES,qualification_scope=scope,
        coverage=dict(planned_entries=len(entries),covered_entries=len(covered),missing_entries=missing_entries,
                      planned_runs=len(expected),completed_runs=len(rows),unexecuted_runs=len(expected-set(actual))),
        quality=dict(returned_runs=len(observed),correct_runs=correct,incorrect_runs=len(observed)-correct),
        availability=dict(incomplete_provider_runs=gap_count),
        safety=dict(unsafe_runs=unsafe,blocking_runs=blocking,invalid_run_identities=invalid_identity,
                    qualification_identity_correct=identity_valid))
