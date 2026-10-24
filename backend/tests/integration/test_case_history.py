"""Real SQL history, atomic lifecycle decisions and selected-copy deletion."""
from uuid import uuid4
import sqlite3
import pytest
from support.lifecycle import close_ready, closure, command, create_case, run, update
from promisekeeper.application.cases import get_case, delete_demonstration
from promisekeeper.application.operations import CommandError, lookup_receipt
from promisekeeper.persistence.repositories import history
from promisekeeper.persistence.sqlite import Database


def test_history_and_decisions_survive_restart_with_immutable_exact_references(tmp_path):
    from promisekeeper.application.lifecycle import close_case,reopen_case
    from promisekeeper.application.decisions import record_disposition
    path=tmp_path/'db.sqlite'
    with Database(path) as db:
        did,cid,view=close_ready(db)
        result=view['current_result']; finances=view['financial_facts']
        first=history(db,did,cid,limit=2)
        decided=record_disposition(db,did,cid,command(view,investigation_id=result['investigation_id'],decision='REJECT',reason='Review manually'))
        now=get_case(db,did,cid)
        assert now['lifecycle']=='OPEN' and now['financial_facts']==finances
        assert now['review_epoch']==view['review_epoch']
        assert record_disposition(db,did,cid,command(now,investigation_id=result['investigation_id'],decision='ACCEPT',reason=None))['disposition']['decision']=='ACCEPT'
        now=get_case(db,did,cid)
        close_case(db,did,cid,closure(now))
        now=get_case(db,did,cid)
        body=command(now,confirm=True,reason='Owner requested another review')
        reopened=reopen_case(db,did,cid,body)
        events=history(db,did,cid)['events']
        closed=next(e for e in events if e['event_type']=='CASE_CLOSED')
        assert closed['payload']['result_hash']==result['result_hash']
        assert closed['payload']['snapshot_hash']==result['snapshot_hash']
        assert {s['source_id'] for s in closed['payload']['settlement_sources']} >= {'PK-003-I1','PK-003-L1','PK-003-L2'}
        assert history(db,did,cid,limit=2)==first
        remaining=history(db,did,cid,cursor=first['next_cursor'])['events']
        assert first['events']+remaining==events
        with db.transaction() as con:
            with pytest.raises(sqlite3.IntegrityError,match='Immutable'):
                con.execute("UPDATE case_events SET event_type='MUTATED' WHERE id=?",(closed['id'],))
        saved=get_case(db,did,cid)
    with Database(path) as db:
        assert history(db,did,cid)['events']==events
        assert get_case(db,did,cid)==saved
        assert reopen_case(db,did,cid,body)==reopened
        assert lookup_receipt(db,did,decided['receipt']['operation_id'])==decided


@pytest.mark.parametrize('branch,error', [('running','INVESTIGATION_RUNNING'),('superseded','RESULT_SUPERSEDED'),('evidence','EVIDENCE_CHANGED'),('nonzero','CLOSE_NOT_RECOMMENDED'),('unknown','CLOSE_NOT_RECOMMENDED'),('revision','REVISION_CONFLICT')])
def test_closure_rejects_ineligible_results_without_event_or_receipt(tmp_path,branch,error):
    from promisekeeper.application.lifecycle import close_case
    from promisekeeper.application.start_investigation import start_investigation, finish_incomplete
    from support.closed_conflict import install_closed_conflict_event, CLOSED_CONFLICT_EVENT
    from pytest import MonkeyPatch
    with Database(tmp_path/'db.sqlite') as db, MonkeyPatch.context() as mp:
        did,cid,view=close_ready(db)
        body=closure(view)
        if branch in {'running','superseded'}:
            response=start_investigation(db,did,cid,command(view,retry_of=None))
            if branch=='superseded':
                from promisekeeper.orchestration.investigate import investigate
                from promisekeeper.agents.scripted import ScriptedInvestigator
                assert investigate(db,response['investigation_id'],ScriptedInvestigator())
        elif branch=='evidence':
            install_closed_conflict_event(mp);update(db,did,cid,CLOSED_CONFLICT_EVENT['id'])
        elif branch in {'nonzero','unknown'}:
            did,cid=create_case(db,variant='FV-05' if branch=='unknown' else None)
            view=run(db,did,cid);body=closure(view)
        if branch=='revision': body['expected_case_revision']+=1
        else: body['expected_case_revision']=get_case(db,did,cid)['case_revision']
        before=history(db,did,cid)
        with pytest.raises(CommandError,match=error):close_case(db,did,cid,body)
        assert history(db,did,cid)==before
        assert get_case(db,did,cid)['lifecycle']=='OPEN'
        with pytest.raises(CommandError,match='NOT_RECORDED'):lookup_receipt(db,did,body['operation_id'])
        if branch=='running':finish_incomplete(db,response['investigation_id'],'TEST_FINISHED')


@pytest.mark.parametrize('kind',['closure','disposition','reopening'])
def test_decision_commit_failure_rolls_back_state_history_and_receipt(tmp_path,monkeypatch,kind):
    from promisekeeper.application.lifecycle import close_case,reopen_case
    from promisekeeper.application.decisions import record_disposition
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=close_ready(db)
        if kind=='reopening':close_case(db,did,cid,closure(view));view=get_case(db,did,cid)
        function={'closure':close_case,'disposition':record_disposition,'reopening':reopen_case}[kind]
        body=closure(view) if kind=='closure' else command(view,**(dict(confirm=True,reason=None) if kind=='reopening' else dict(investigation_id=view['current_result']['investigation_id'],decision='ACCEPT',reason=None)))
        events=history(db,did,cid);commit=db.commit
        def fail(con):raise sqlite3.OperationalError('disk failure')
        monkeypatch.setattr(db,'commit',fail)
        with pytest.raises(sqlite3.OperationalError):function(db,did,cid,body)
        monkeypatch.setattr(db,'commit',commit)
        assert get_case(db,did,cid)==view
        assert history(db,did,cid)==events
        with pytest.raises(CommandError,match='NOT_RECORDED'):lookup_receipt(db,did,body['operation_id'])
        saved=function(db,did,cid,body)
        assert function(db,did,cid,body)==saved
        assert lookup_receipt(db,did,body['operation_id'])==saved
        with pytest.raises(CommandError,match='OPERATION_PAYLOAD_MISMATCH'):function(db,did,cid,body|{'expected_case_revision':999})


def test_disposition_scopes_results_allows_history_and_does_not_restore_draft_approval(tmp_path):
    from promisekeeper.application.decisions import record_disposition
    from promisekeeper.application.reviews import review_draft
    with Database(tmp_path/'db.sqlite') as db:
        did,cid=create_case(db,catalogue_case_id='PK-001');view=run(db,did,cid);old=view['current_result'];draft=view['draft']
        review_draft(db,did,cid,command(view,draft_version_id=draft['id'],payload_hash=draft['payload_hash'],expected_review_epoch=view['review_epoch'],decision='APPROVE'))
        view=run(db,did,cid);facts=view['financial_facts'];epoch=view['review_epoch']
        foreign,other=create_case(db);other_view=run(db,foreign,other)
        with pytest.raises(CommandError,match='NOT_FOUND'):
            record_disposition(db,did,cid,command(view,investigation_id=other_view['current_result']['investigation_id'],decision='ACCEPT',reason=None))
        saved=record_disposition(db,did,cid,command(view,investigation_id=old['investigation_id'],decision='REJECT',reason='Old recommendation reviewed'))
        now=get_case(db,did,cid)
        assert saved['disposition']['investigation_id']==old['investigation_id']
        assert now['financial_facts']==facts and now['lifecycle']=='OPEN' and now['review_epoch']==epoch
        assert now['review_state']=='UNAPPROVED'


def test_deletion_preserves_other_copy_and_turns_lifecycle_replay_content_free(tmp_path):
    from promisekeeper.application.lifecycle import close_case
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=close_ready(db);body=closure(view);close_case(db,did,cid,body)
        other,oid,other_view=close_ready(db);other_history=history(db,other,oid)
        deletion=dict(schema_version='1',operation_id=str(uuid4()),confirmed_demonstration_id=did,confirm=True)
        deleted=delete_demonstration(db,did,deletion)
        assert delete_demonstration(db,did,deletion)==deleted
        replay=close_case(db,did,cid,body)
        assert set(replay)=={'schema_version','demonstration_id','receipt'}
        assert replay['receipt']['outcome']=='DELETED'
        assert lookup_receipt(db,did,body['operation_id'])==replay
        assert get_case(db,other,oid)==other_view and history(db,other,oid)==other_history
        with pytest.raises(CommandError,match='NOT_FOUND'):history(db,did,cid)
        with pytest.raises(CommandError,match='OPERATION_PAYLOAD_MISMATCH'):close_case(db,other,oid,body)
        with db.connection() as con:
            assert con.execute('SELECT count(*) FROM case_events WHERE demonstration_id=?',(did,)).fetchone()[0]==0
            assert con.execute('SELECT count(*) FROM evidence_snapshots WHERE demonstration_id=?',(did,)).fetchone()[0]==0
            assert con.execute('SELECT count(*) FROM investigation_results WHERE demonstration_id=?',(did,)).fetchone()[0]==0


def test_history_read_retains_scope_snapshot_during_concurrent_selected_copy_deletion(tmp_path,monkeypatch):
    import threading
    from promisekeeper.persistence import repositories
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=close_ready(db)
        expected=history(db,did,cid)
        checked=threading.Event();finished=threading.Event();errors=[];threads=[]
        original=repositories.case
        def remove():
            checked.set()
            try:
                delete_demonstration(db,did,dict(schema_version='1',operation_id=str(uuid4()),confirmed_demonstration_id=did,confirm=True))
            except Exception as exc:errors.append(exc)
            finally:finished.set()
        def scoped(con,copy_id,case_id):
            row=original(con,copy_id,case_id)
            worker=threading.Thread(target=remove);threads.append(worker);worker.start()
            assert checked.wait(1)
            finished.wait(.08)
            return row
        monkeypatch.setattr(repositories,'case',scoped)
        assert history(db,did,cid)==expected
        for worker in threads:worker.join(2)
        assert finished.is_set() and errors==[]


def test_zero_settlement_date_only_issue_remains_eligible_for_explicit_closure(tmp_path,monkeypatch):
    from copy import deepcopy
    from promisekeeper.fixtures import catalogue
    from promisekeeper.application.lifecycle import close_case
    original=catalogue._read
    def adjusted(name):
        value=deepcopy(original(name))
        if name=='baseline.json':
            invoice=next(case for case in value['cases'] if case['id']=='PK-003')['sources'][0]
            invoice['data']['due_text']='date not specified'
            invoice['original_content']='Fictional invoice CR-312; client Cedar Retail Labs; INR 90,000.00; due date not specified.'
        return value
    monkeypatch.setattr(catalogue,'_read',adjusted)
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=close_ready(db)
        assert view['current_result']['action']=='CLOSE'
        assert view['financial_facts']['balance']['minor_units']=='0'
        assert [i['code'] for i in view['financial_facts']['issues']]==['INVOICE_DATE_UNRESOLVED']
        assert view['allowed_commands']['close']['allowed'] is True
        saved=close_case(db,did,cid,closure(view))
        assert saved['lifecycle']=='CLOSED'
        assert get_case(db,did,cid)['latest_completed_result']==view['current_result']
