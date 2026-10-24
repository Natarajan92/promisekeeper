from uuid import uuid4
import pytest
from promisekeeper.application.cases import create_demonstration,get_case
from promisekeeper.application.start_investigation import start_investigation,finish_incomplete
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.orchestration.investigate import investigate,get_investigation
from promisekeeper.persistence.sqlite import Database
from promisekeeper.fixtures.catalogue import fresh_copy,variant_ids,variant_definition

def create(db,variant=None):
    did=create_demonstration(db,dict(schema_version='1',operation_id=str(uuid4()),catalogue_version='release-0.1',variant_id=variant,clock_mode='REFERENCE'))['demonstration_id']
    with db.connection() as con: rows=[dict(r) for r in con.execute('SELECT * FROM cases WHERE demonstration_id=? ORDER BY catalogue_case_id',(did,))]
    return did,rows

def start(db,did,row):
    return start_investigation(db,did,row['id'],dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=row['case_revision'],retry_of=None))['investigation_id']

@pytest.mark.parametrize('variant',[None,*variant_ids()])
def test_all_catalogue_snapshots_preserve_expected_domain_actions(tmp_path,variant):
    fixture=fresh_copy(variant)
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db,variant)
        for row in rows:
            iid=start(db,did,row)
            assert investigate(db,iid,ScriptedInvestigator()) is True,(variant,get_investigation(db,did,iid))
            result=get_investigation(db,did,iid)['result']
            expected=fixture.cases[row['catalogue_case_id']].expected
            assert result['action']==expected['action'],(variant,row['catalogue_case_id'],result)
            balance=result['financial_facts']['balance']
            assert (balance['minor_units'] if balance else None)==expected['balance_minor']

@pytest.mark.parametrize('behavior,expected_calls',[('refusal',1),('malformed',1),('unavailable',2),('transient_once',2)])
def test_persisted_retry_counts_safe_failures_and_terminal_fence(tmp_path,behavior,expected_calls):
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);iid=start(db,did,rows[0]);agent=ScriptedInvestigator(behavior)
        investigate(db,iid,agent)
        result=get_investigation(db,did,iid)
        assert agent.calls==expected_calls
        assert result['status']==('COMPLETE' if behavior=='transient_once' else 'INCOMPLETE')
        if behavior!='transient_once':assert result['result'] is None and result['action'] is None
        assert db.capacity.available
        assert investigate(db,iid,ScriptedInvestigator()) is False
        with db.connection() as con:
            steps=con.execute("SELECT invocation_kind FROM step_attempts WHERE investigation_id=? AND step_name='EXTRACTION' ORDER BY invocation_number",(iid,)).fetchall()
        assert [r[0] for r in steps]==(['INITIAL','AUTO_RETRY'] if expected_calls==2 else ['INITIAL'])

def test_midrun_confirmed_evidence_arrival_does_not_change_captured_result(tmp_path):
    from promisekeeper.application.scenario_updates import preview_event,confirm_event
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);row=rows[0];iid=start(db,did,row)
        class Arriving(ScriptedInvestigator):
            def extract(self,request,*,timeout):
                preview=preview_event(db,did,row['id'],'PK-001-U1')
                confirm_event(db,did,row['id'],dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=preview['expected_case_revision'],event_id='PK-001-U1',catalogue_version='release-0.1',confirmed_preview_hash=preview['preview_hash']))
                return super().extract(request,timeout=timeout)
        assert investigate(db,iid,Arriving())
        result=get_investigation(db,did,iid)['result']
        assert result['financial_facts']['balance']['minor_units']=='8000000'
        view=get_case(db,did,row['id'])
        assert view['financial_facts']['balance']['minor_units']=='8000000'
        assert len(view['evidence'])>len(result['timeline'])
        assert view['latest_completed_result']==result
        assert view['current_result'] is None
        assert view['freshness']=='EVIDENCE_CHANGED'

def test_duplicate_worker_dispatch_cannot_cancel_original_attempt(tmp_path):
    import threading
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);iid=start(db,did,rows[0]);entered=threading.Event();release=threading.Event()
        class Blocking(ScriptedInvestigator):
            def extract(self,request,*,timeout):
                entered.set();assert release.wait(5)
                return super().extract(request,timeout=timeout)
        worker=threading.Thread(target=investigate,args=(db,iid,Blocking()));worker.start()
        assert entered.wait(5)
        assert investigate(db,iid,ScriptedInvestigator()) is False
        release.set();worker.join(5)
        assert get_investigation(db,did,iid)['status']=='COMPLETE'

def test_provider_ignoring_timeout_does_not_overlap_retry_or_new_call():
    import threading,time
    from promisekeeper.orchestration.deadlines import bounded_call
    from promisekeeper.agents.protocol import InvestigatorFailure
    entered=threading.Event();release=threading.Event();second_called=threading.Event()
    def blocking():entered.set();release.wait(3);return 'late'
    try:
        with pytest.raises(InvestigatorFailure):bounded_call(blocking,.03)
        assert entered.is_set()
        with pytest.raises(InvestigatorFailure):bounded_call(lambda:second_called.set(),.03)
        assert not second_called.is_set()
    finally:release.set()
    time.sleep(.03)
    assert not second_called.is_set()

def test_unavailable_ledger_limitation_does_not_fabricate_missing_extraction(tmp_path):
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db,'FV-05');row=next(r for r in rows if r['catalogue_case_id']=='PK-003')
        iid=start(db,did,row);assert investigate(db,iid,ScriptedInvestigator())
        result=get_investigation(db,did,iid)['result']
        assert result['status']=='LIMITED'
        assert 'LEDGER_UNAVAILABLE' in result['limitations']
        assert 'MISSING_EXTRACTION' not in result['limitations']

def test_invalid_output_keeps_live_response_identity_without_a_result(tmp_path):
    from promisekeeper.agents.protocol import AgentResponse,PROMPT_VERSION
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);iid=start(db,did,rows[0])
        class Invalid:
            def extract(self,request,*,timeout):return AgentResponse('{',returned_model='test-returned-model',response_id='test-response-id',adapter_version='test-adapter-1')
        assert not investigate(db,iid,Invalid())
        with db.connection() as con:row=dict(con.execute('SELECT * FROM investigations WHERE id=?',(iid,)).fetchone())
        assert row['status']=='INCOMPLETE'
        assert row['returned_model']=='test-returned-model' and row['response_id']=='test-response-id'
        assert row['prompt_version']==PROMPT_VERSION and row['schema_version']=='1' and row['adapter_version']=='test-adapter-1'
        view=get_investigation(db,did,iid)
        assert view['action'] is None and view['result'] is None

def test_snapshot_preserves_original_offset_for_near_midnight_relative_source_date(tmp_path,monkeypatch):
    import json
    from dataclasses import replace
    from datetime import datetime,date
    from promisekeeper.application import cases as application_cases
    from promisekeeper.tools.evidence import read_snapshot,snapshot_case
    from promisekeeper.domain.dates import source_day
    fixture=fresh_copy();item=fixture.cases['PK-003'];original=item.evidence.messages[0]
    source=replace(original.source,event_at=datetime.fromisoformat('2026-10-23T00:30:00+05:30'))
    item=replace(item,evidence=replace(item.evidence,messages=(replace(original,source=source),)),
                 extraction=replace(item.extraction,claims=tuple(replace(c,source=source) for c in item.extraction.claims)))
    raw=json.loads(fixture._records_json)
    next(r for r in raw['PK-003']['sources'] if r['source_id']=='PK-003-M1')['event_at']='2026-10-23T00:30:00+05:30'
    fixture=replace(fixture,cases=dict(fixture.cases)|{'PK-003':item},_records_json=json.dumps(raw))
    monkeypatch.setattr(application_cases,'fresh_copy',lambda variant=None:fixture)
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);row=next(r for r in rows if r['catalogue_case_id']=='PK-003');iid=start(db,did,row)
        with db.connection() as con:
            stored=con.execute('SELECT snapshot_id FROM investigations WHERE id=?',(iid,)).fetchone()[0]
            packet=json.loads(con.execute('SELECT packet_json FROM evidence_snapshots WHERE id=?',(stored,)).fetchone()[0])
        packet=read_snapshot(db,dict(schema_version='1',snapshot_id=stored,evidence_version_ids=[r['id'] for r in packet['evidence']]))
        message=next(r for r in packet['evidence'] if r['stable_source_id']=='PK-003-M1')
        assert message['event_at']=='2026-10-22T19:00:00+00:00'
        assert message['original_event_at']=='2026-10-23T00:30:00+05:30'
        runtime=snapshot_case(packet).messages[0].source
        assert source_day('today',original_at=runtime.event_at)==source_day('today',original_at=source.event_at)==date(2026,10,23)
        finish_incomplete(db,iid,'TEST')

@pytest.mark.parametrize('status,failures,calls_expected,status_expected',[(529,1,2,'COMPLETE'),(529,2,2,'INCOMPLETE'),(400,1,1,'INCOMPLETE')])
def test_http_status_retry_budget_is_persisted_once_without_hidden_repair(tmp_path,status,failures,calls_expected,status_expected):
    import json
    import httpx
    from types import SimpleNamespace
    from openai import APIStatusError
    from promisekeeper.agents.nebius import NebiusInvestigator
    from promisekeeper.config import load_settings
    settings=load_settings({'NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path)
    class Completions:
        calls=0
        def create(self,**kwargs):
            self.calls+=1
            if self.calls<=failures:
                response=httpx.Response(status,request=httpx.Request('POST','https://api.tokenfactory.nebius.com/v1/chat/completions'))
                raise APIStatusError('fictional status response',response=response,body=None)
            request=json.loads(kwargs['messages'][1]['content'])
            output=ScriptedInvestigator().extract(request,timeout=20).output
            return SimpleNamespace(id='test-response',model=settings.model,usage=None,choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content=json.dumps(output),refusal=None))])
    completions=Completions();client=SimpleNamespace(chat=SimpleNamespace(completions=completions))
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);iid=start(db,did,rows[0])
        investigate(db,iid,NebiusInvestigator(settings,client=client))
        view=get_investigation(db,did,iid)
        assert view['status']==status_expected
        assert completions.calls==calls_expected
        with db.connection() as con:
            steps=con.execute("SELECT invocation_kind FROM step_attempts WHERE investigation_id=? AND step_name='EXTRACTION' ORDER BY invocation_number",(iid,)).fetchall()
        assert [r[0] for r in steps]==(['INITIAL','AUTO_RETRY'] if calls_expected==2 else ['INITIAL'])
        if status_expected=='INCOMPLETE':assert view['action'] is None and view['result'] is None
        assert db.capacity.available
