"""Persisted deterministic findings and legacy hash boundaries, entirely offline."""
from copy import deepcopy
import json

import pytest

from promisekeeper.agents.protocol import AgentResponse
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.operations import digest
from promisekeeper.orchestration.investigate import investigate, get_investigation
from promisekeeper.persistence.sqlite import Database
from test_investigation_pipeline import create, start


def test_persisted_source_literal_by_deadline_has_known_expiry_without_false_question(tmp_path):
    from datetime import datetime
    class ByDeadline(ScriptedInvestigator):
        def extract(self,request,*,timeout):
            response=super().extract(request,timeout=timeout)
            candidate=response.output['commitments'][0]
            assert candidate['source']['quote']=='We will pay INR 80,000 by 20 October 2026.'
            candidate['date_text']='by 20 October 2026'
            return response
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db,'FV-10-EVIDENCE')
        row=next(r for r in rows if r['catalogue_case_id']=='PK-001')
        iid=start(db,did,row)
        assert investigate(db,iid,ByDeadline())
        view=get_investigation(db,did,iid)
        result=view['result']
        assert result['action']=='FOLLOW_UP'
        assert datetime.fromisoformat(result['commitments'][0]['expires_at'])==datetime.fromisoformat('2026-10-20T18:30:00+00:00')
        assert not any(q['field']=='PROMISE_DATE' for q in result['unresolved_questions'])
        assert result['result_hash']==digest({k:v for k,v in result.items() if k!='result_hash'})
        assert get_investigation(db,did,iid)==view


@pytest.mark.parametrize('field', ['contradictions', 'unresolved'])
def test_model_findings_reject_without_persisted_result_or_action(tmp_path, field):
    class FindingAgent(ScriptedInvestigator):
        def extract(self, request, *, timeout):
            response = super().extract(request, timeout=timeout)
            output = deepcopy(response.output)
            span = output['commitments'][0]['source']
            output[field] = ([dict(kind='PROMISED_AMOUNT', sources=[span, span])]
                             if field == 'contradictions' else [dict(field='AMOUNT', sources=[span])])
            return AgentResponse(output)
    with Database(tmp_path/'db.sqlite') as db:
        did, rows = create(db)
        iid = start(db, did, rows[0])
        assert not investigate(db, iid, FindingAgent())
        view = get_investigation(db, did, iid)
        assert view['status'] == 'INCOMPLETE'
        assert view['result'] is None and view['action'] is None
        with db.connection() as con:
            assert con.execute('SELECT count(*) FROM investigation_results').fetchone()[0] == 0


def test_new_profile_and_source_less_incomplete_lookup_observation(tmp_path):
    with Database(tmp_path/'db.sqlite') as db:
        did, rows = create(db)
        row = rows[0]
        with db.transaction() as con:
            con.execute('UPDATE cases SET ledger_complete=0 WHERE id=?', (row['id'],))
        iid = start(db, did, row)
        assert investigate(db, iid, ScriptedInvestigator())
        result = get_investigation(db, did, iid)['result']
        assert result['findings_version'] == 'deterministic-1'
        observation = next(o for o in result['evidence_observations'] if o['field'] == 'complete')
        assert observation == dict(subject='LEDGER', field='complete', value=False,
                                   snapshot_id=result['snapshot_id'], snapshot_hash=result['snapshot_hash'], source=None)
        assert not any(q['field'] == 'AMOUNT' for q in result['unresolved_questions'])
        assert result['result_hash'] == digest({k:v for k,v in result.items() if k != 'result_hash'})


def test_complete_attempt_retains_commitment_issues(tmp_path, monkeypatch):
    from dataclasses import replace
    from promisekeeper.application import cases as application_cases
    from promisekeeper.fixtures.catalogue import fresh_copy
    fixture = fresh_copy()
    records = json.loads(fixture._records_json)
    message = next(r for r in records['PK-001']['sources'] if r['source_id']=='PK-001-M1')
    original = fixture.cases['PK-001'].extraction.commitments[0]
    message['original_content'] = original.source.original_content.replace(original.amount_text, original.amount_text+'.001')
    item = fixture.cases['PK-001']
    source = replace(original.source,original_content=message['original_content'])
    evidence = replace(item.evidence,
        messages=tuple(replace(m,source=source) if m.source.id==source.id else m for m in item.evidence.messages),
        anchors=tuple(replace(a,clause_end=a.clause_end+4) if a.evidence_version_id==source.id else a for a in item.evidence.anchors))
    modified = replace(fixture,cases=fixture.cases | {'PK-001':replace(item,evidence=evidence)},_records_json=json.dumps(records))
    monkeypatch.setattr(application_cases, 'fresh_copy', lambda variant=None:modified)
    class InvalidPrecision(ScriptedInvestigator):
        def extract(self, request, *, timeout):
            message = next(r for r in request['packet']['evidence'] if r['stable_source_id']=='PK-001-M1')
            text = message['original_content']
            return AgentResponse(dict(schema_version='1',snapshot_id=request['snapshot_id'],contradictions=[],unresolved=[],payment_claims=[],
                commitments=[dict(candidate_id='candidate',commitment_key=original.commitment_key,
                    source=dict(evidence_version_id=message['id'],source_id=message['stable_source_id'],start=0,end=len(text),quote=text),
                    speaker=original.speaker,amount_text=original.amount_text+'.001',currency_text=original.currency_text,
                    date_text=original.date_text,explicitly_replaces_source_id=None)]))
    with Database(tmp_path/'db.sqlite') as db:
        did, rows = create(db)
        iid = start(db, did, rows[0])
        assert investigate(db, iid, InvalidPrecision())
        result = get_investigation(db, did, iid)['result']
        assert result['status'] == 'COMPLETE'
        issue = next(i for i in result['commitment_issues'] if i['code']=='INVALID_PROMISE_AMOUNT')
        assert issue['sources'] == ['PK-001-M1']
        assert issue['source_versions'][0]['source_id'] == 'PK-001-M1'
        assert result['findings_version'] == 'deterministic-1'


def test_strict_new_profile_and_legacy_read_preserve_hash_payload(tmp_path):
    from pydantic import ValidationError
    from promisekeeper.contracts.investigations import Result, InvestigationView
    with Database(tmp_path/'db.sqlite') as db:
        did, rows = create(db)
        iid = start(db, did, rows[0])
        assert investigate(db, iid, ScriptedInvestigator())
        view = get_investigation(db, did, iid)
        new = view['result']
        legacy = {k:v for k,v in new.items() if k not in {'findings_version', 'commitment_issues', 'evidence_observations'}}
        for issue in legacy['financial_facts']['issues']:
            issue.pop('source_versions', None)
        legacy['result_hash'] = digest({k:v for k,v in legacy.items() if k != 'result_hash'})
        with pytest.raises(ValidationError):
            Result.model_validate(legacy)
        parsed = InvestigationView.model_validate(view | {'result':legacy})
        assert parsed.model_dump(exclude_unset=True)['result'] == legacy
        for key in ('commitment_issues', 'evidence_observations'):
            broken = deepcopy(new)
            broken.pop(key)
            with pytest.raises(ValidationError):
                InvestigationView.model_validate(view | {'result':broken})
