"""Reproducible LIVE extraction evaluation; STUB cannot satisfy acceptance."""
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
import json
import re
from pathlib import Path
import tempfile
import time
from uuid import UUID,uuid4
from copy import deepcopy
from promisekeeper.agents.nebius import NebiusInvestigator,ADAPTER_VERSION,request_parameters
from promisekeeper.agents.protocol import PROMPT_VERSION,EXTRACTION_POLICY_VERSION
from promisekeeper.application.cases import create_demonstration
from promisekeeper.application.operations import instant,utcnow
from promisekeeper.application.provider_usage import usage_recorder
from promisekeeper.application.scenario_updates import preview_event,confirm_event
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.application.evaluation_qualification import qualify,classify_run,manifest_hash,EVALUATOR_VERSION,CRITERIA_VERSION,CRITERIA_URI
from promisekeeper.fixtures.catalogue import fresh_copy,variant_ids,variant_definition,apply_event
from promisekeeper.orchestration.investigate import investigate,get_investigation
from promisekeeper.persistence.sqlite import Database
from promisekeeper.domain.dates import TEMPORAL_POLICY_VERSION
from promisekeeper.application.evaluation_uncertainty import uncertainty_correct as _uncertainty_correct
from promisekeeper.application.evaluation_findings import (load_inventory,score_findings,findings_view,
    INVENTORY_VERSION,INVENTORY_HASH,FINDINGS_PROFILE,CHECKS)

def evaluation_manifest():
    entries=[dict(id='baseline:'+cid,variant=None,case_id=cid,events=[]) for cid in ('PK-001','PK-002','PK-003')]
    entries += [dict(id=event,variant=None,case_id=event[:6],events=[event]) for event in ('PK-001-U1','PK-002-U1','PK-003-U1')]
    for variant in variant_ids():
        definition=variant_definition(variant)
        entries.append(dict(id=variant,variant=variant,case_id=definition['case_id'],events=[]))
        previous=[]
        for event in definition['events']:
            previous.append(event['id'])
            entries.append(dict(id=event['id'],variant=variant,case_id=definition['case_id'],events=list(previous)))
    return entries

def candidate_fact_view(extraction):
    """Auditable validated raw fields, independent of generated IDs and quotes."""
    commitments=[dict(source_id=c.source.source_id,commitment_key=c.commitment_key,speaker=c.speaker,
        amount_text=c.amount_text,currency_text=c.currency_text,date_text=c.date_text,
        explicitly_replaces_source_id=c.explicitly_replaces_source_id) for c in extraction.commitments]
    claims=[dict(source_id=c.source.source_id,speaker=c.speaker,amount_text=c.amount_text,currency_text=c.currency_text,
        payment_date_text=c.payment_date_text,transaction_reference_text=c.transaction_reference_text) for c in extraction.claims]
    return dict(commitments=sorted(commitments,key=lambda c:(c['source_id'],c['commitment_key'] or '')),
                payment_claims=sorted(claims,key=lambda c:c['source_id']))


def _raw_facts(raw):
    commitments=[dict(source_id=c['source']['source_id'],**{key:c[key] for key in
        ('commitment_key','speaker','amount_text','currency_text','date_text','explicitly_replaces_source_id')}) for c in raw['commitments']]
    claims=[dict(source_id=c['source']['source_id'],**{key:c[key] for key in
        ('speaker','amount_text','currency_text','payment_date_text','transaction_reference_text')}) for c in raw['payment_claims']]
    return dict(commitments=sorted(commitments,key=lambda c:(c['source_id'],c['commitment_key'] or '')),
                payment_claims=sorted(claims,key=lambda c:c['source_id']))


def _known_deadline_expression(raw, original_at):
    """Evaluator-only support guard; never use product date/derived findings logic.

    This proves only that an unchanged literal remainder is known, not that
    differently written dates are equivalent. Calendar rollover is checked to
    exclude dates whose exclusive next-day boundary cannot be represented.
    """
    try:
        if re.match(r'^[0-9]{4}-[0-9]{2}-[0-9]{2}[Tt]', raw):
            value=datetime.fromisoformat(raw)
            if value.tzinfo is None or value.utcoffset() is None:return False
            value.astimezone(timezone.utc)
            return True
        value=raw.strip()
        if value.lower() in {'today','tomorrow'}:
            original=datetime.fromisoformat(original_at)
            if original.tzinfo is None or original.utcoffset() is None:return False
            day=original.date()+timedelta(days=value.lower()=='tomorrow')
        elif re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}',value):
            day=date.fromisoformat(value)
        else:
            match=re.fullmatch(r'([0-9]{1,2}) ([A-Za-z]+) ([0-9]{4})',value)
            months=('january','february','march','april','may','june','july','august','september','october','november','december')
            if match is None or match[2].lower() not in months:return False
            day=date(int(match[3]),months.index(match[2].lower())+1,int(match[1]))
        day+timedelta(days=1)
        return True
    except (ValueError,TypeError,OverflowError):return False


def candidate_facts_equal(actual,expected,packet):
    """Strict raw comparison except one leading by on a known commitment date.

    Neither input is rewritten: reports retain both literal fact views. Payment
    claims and every other commitment field retain exact equality requirements.
    """
    if actual['payment_claims']!=expected['payment_claims']:return False
    if len(actual['commitments'])!=len(expected['commitments']):return False
    for left,right in zip(actual['commitments'],expected['commitments']):
        if {k:v for k,v in left.items() if k!='date_text'}!={k:v for k,v in right.items() if k!='date_text'}:return False
        a,b=left['date_text'],right['date_text']
        if a==b:continue
        if not isinstance(a,str) or not isinstance(b,str):return False
        if a[:3].lower()=='by ' and a[3:]==b:expression=b
        elif b[:3].lower()=='by ' and b[3:]==a:expression=a
        else:return False
        records=[r for r in packet['evidence'] if r['stable_source_id']==left['source_id']]
        if len(records)!=1:return False
        record=records[0]
        if not _known_deadline_expression(expression,record.get('original_event_at',record.get('event_at'))):return False
    return True


def _candidate_sources_valid(raw,packet):
    """Independent source check, including rejected nonempty model findings."""
    try:
        if raw['snapshot_id']!=packet['snapshot_id']:return False
        UUID(raw['snapshot_id'])
        records={r['id']:r for r in packet['evidence']}
        candidates=[*raw['commitments'],*raw['payment_claims']]
        spans=[(c['source'],True) for c in candidates]
        spans += [(s,False) for key in ('contradictions','unresolved') for item in raw[key] for s in item['sources']]
        for span,candidate in spans:
            UUID(span['evidence_version_id'])
            record=records[span['evidence_version_id']];start,end=span['start'],span['end']
            if (span['source_id']!=record['stable_source_id'] or record['availability']!='AVAILABLE'
                    or (candidate and record['kind']!='MESSAGE') or type(start) is not int or type(end) is not int
                    or not 0<=start<end<=len(record['original_content'])
                    or not span['quote'] or record['original_content'][start:end]!=span['quote']):return False
        return True
    except (KeyError,ValueError,TypeError,AttributeError):return False


def _observed(previous,current):
    """A later response or missing response cannot erase an observed failure."""
    return current if previous is None else previous and current

def evaluate(settings,*,catalogue,repeats,output,manifest=None):
    if catalogue!='release-0.1' or repeats<1:raise ValueError('Unsupported evaluation request')
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    root=Path(__file__).resolve().parents[4]
    entries=list(evaluation_manifest() if manifest is None else manifest)
    canonical=evaluation_manifest()
    inventory=load_inventory(canonical)
    if any(entry not in canonical for entry in entries):raise ValueError('Noncanonical evaluation definition')
    report=dict(schema_version='1',suite='live',agent_mode='LIVE',provider='NEBIUS',catalogue_version=catalogue,requested_model=settings.model,
        prompt_version=PROMPT_VERSION,extraction_schema_version='1',adapter_version=ADAPTER_VERSION,request_parameters=request_parameters(settings.model),repeats=repeats,started_at=instant(utcnow()),
        evaluator_version=EVALUATOR_VERSION,criteria_version=CRITERIA_VERSION,criteria_uri=CRITERIA_URI,
        extraction_policy_version=EXTRACTION_POLICY_VERSION,findings_version=FINDINGS_PROFILE,
        temporal_policy_version=TEMPORAL_POLICY_VERSION,
        inventory_version=INVENTORY_VERSION,inventory_hash=INVENTORY_HASH,
        manifest_entries=[e['id'] for e in entries],manifest_definitions=entries,manifest_hash=manifest_hash(entries),
        qualification_scope='RELEASE' if repeats==3 and entries==canonical else 'SUBSET',
        status='RUNNING',qualified=False,blocking_reason=None,runs=[])
    def save():output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if not settings.api_key:
        report.update(qualify(report),blocking_reason='CAPABILITY_UNAVAILABLE',finished_at=instant(utcnow()));save();return report
    sink=usage_recorder(root/'.runtime'/'application-provider-usage.jsonl')
    save()
    class CheckingInvestigator(NebiusInvestigator):
        def __init__(self,oracle,evaluation_at):
            super().__init__(replace(settings,agent_mode='LIVE'),usage_sink=sink)
            self.expected=oracle.extraction;self.oracle=oracle;self.evaluation_at=evaluation_at
            self.check=None;self.source_valid=None;self.policy=None;self.models=[];self.responses=[];self.validated_uncertainty=None;self.actual_candidate_facts=None
            self.policy_evidence=None;self.packet=None;self.outputs=[]
        def extract(self,request,*,timeout):
            self.packet=deepcopy(request['packet'])
            response=super().extract(request,timeout=timeout)
            self.models.append(response.returned_model);self.responses.append(response.response_id)
            self.actual_candidate_facts=None;self.policy_evidence=None;self.validated_uncertainty=None
            try:
                raw=json.loads(response.output) if isinstance(response.output,str) else deepcopy(response.output)
                self.policy_evidence={key:raw.get(key) for key in ('contradictions','unresolved')}
                self.validated_uncertainty=self.policy_evidence
                self.policy=_observed(self.policy,all(type(raw.get(key)) is list and raw[key]==[] for key in ('contradictions','unresolved')))
                self.source_valid=_observed(self.source_valid,_candidate_sources_valid(raw,request['packet']))
                self.actual_candidate_facts=_raw_facts(raw)
                self.check=_observed(self.check,candidate_facts_equal(self.actual_candidate_facts,candidate_fact_view(self.expected),request['packet']))
            except (ValueError,KeyError,TypeError,AttributeError):
                self.policy=_observed(self.policy,False);self.source_valid=_observed(self.source_valid,False);self.check=_observed(self.check,False)
            self.outputs.append(dict(candidate_facts=deepcopy(self.actual_candidate_facts),model_policy_evidence=deepcopy(self.policy_evidence),
                extraction_correct=self.check,source_validation_correct=self.source_valid,extraction_policy_correct=self.policy,
                response_id=response.response_id,returned_model=response.returned_model,adapter_version=response.adapter_version))
            return response
    runroot=root/'.runtime'/'gate-iii'/'live';runroot.mkdir(parents=True,exist_ok=True)
    for repeat in range(1,repeats+1):
        for entry in entries:
            begin=time.monotonic()
            expected_fixture=fresh_copy(entry['variant'])
            for event in entry['events']:expected_fixture=apply_event(expected_fixture,event)
            oracle=expected_fixture.cases[entry['case_id']]
            with tempfile.TemporaryDirectory(prefix='eval-',dir=runroot) as directory:
                with Database(Path(directory)/'evaluation.sqlite') as db:
                    did=create_demonstration(db,dict(schema_version='1',operation_id=str(uuid4()),catalogue_version=catalogue,variant_id=entry['variant'],clock_mode='REFERENCE'))['demonstration_id']
                    with db.connection() as con:cid=con.execute('SELECT id FROM cases WHERE demonstration_id=? AND catalogue_case_id=?',(did,entry['case_id'])).fetchone()[0]
                    for event in entry['events']:
                        preview=preview_event(db,did,cid,event)
                        confirm_event(db,did,cid,dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=preview['expected_case_revision'],event_id=event,catalogue_version=catalogue,confirmed_preview_hash=preview['preview_hash']))
                    with db.connection() as con:revision=con.execute('SELECT case_revision FROM cases WHERE id=?',(cid,)).fetchone()[0]
                    started=start_investigation(db,did,cid,dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=revision,retry_of=None),agent_mode='LIVE',requested_model=settings.model)
                    worker=CheckingInvestigator(oracle,expected_fixture.evaluation_at)
                    investigate(db,started['investigation_id'],worker)
                    view=get_investigation(db,did,started['investigation_id']);result=view['result']
                    finding_checks=score_findings(result,worker.packet,inventory['entries'][entry['id']]) if result else dict.fromkeys(CHECKS,None)
                    financial_ok=False if worker.responses else None
                    if result:
                        balance=result['financial_facts']['balance'];balance=balance['minor_units'] if balance else None
                        review=result['review_at'];expected_review=oracle.expected['review_at']
                        review_ok=(review is None and expected_review is None) or (review is not None and expected_review is not None and datetime.fromisoformat(review)==datetime.fromisoformat(expected_review))
                        financial_ok=result['action']==oracle.expected['action'] and balance==oracle.expected['balance_minor'] and review_ok
                    elapsed=time.monotonic()-begin
                    with db.connection() as con:
                        timing=dict(con.execute('SELECT started_at,terminal_at,deadline_at FROM investigations WHERE id=?',(started['investigation_id'],)).fetchone())
                    row=dict(case=entry['id'],repeat=repeat,attempt_status=view['status'],failure_code=view['failure_code'],
                        returned_models=worker.models,response_ids=worker.responses,extraction_correct=worker.check,source_validation_correct=worker.source_valid,extraction_policy_correct=worker.policy,
                        validated_uncertainty=worker.validated_uncertainty,actual_candidate_facts=worker.actual_candidate_facts,
                        model_policy_evidence=worker.policy_evidence,returned_outputs=worker.outputs,
                        actual_findings=findings_view(result) if result else None,expected_findings=inventory['entries'][entry['id']],**finding_checks,
                        expected_candidate_facts=candidate_fact_view(worker.expected),deterministic_outcome_correct=financial_ok,latency_seconds=round(elapsed,3),
                        action=result['action'] if result else None,result_present=result is not None,progress=view['progress'],attempt_timing=timing)
                    row['status']=classify_run(row)
                    report['runs'].append(row)
                    save()
    report.update(qualify(report),finished_at=instant(utcnow()))
    save();return report
