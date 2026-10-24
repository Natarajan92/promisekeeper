"""Real SQLite review races, failed-rerun epochs, retry budgets and rollback."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import sqlite3
import pytest
from test_investigation_pipeline import create,start
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.application.cases import get_case
from promisekeeper.application.start_investigation import start_investigation,finish_incomplete
from promisekeeper.application.operations import CommandError,lookup_receipt
from promisekeeper.persistence.sqlite import Database
from promisekeeper.orchestration.investigate import investigate


def setup(db):
    did,rows=create(db);cid=rows[0]['id'];iid=start(db,did,rows[0])
    assert investigate(db,iid,ScriptedInvestigator())
    return did,cid,get_case(db,did,cid)


def cmd(view,**fields):
    return dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=view['case_revision'],**fields)


def approval(view,draft=None,decision='APPROVE'):
    draft=draft or view['draft']
    return cmd(view,draft_version_id=draft['id'],payload_hash=draft['payload_hash'],expected_review_epoch=view['review_epoch'],decision=decision)


def test_failed_rerun_never_restores_approval_but_fresh_explicit_approval_allowed(tmp_path):
    from promisekeeper.application.reviews import review_draft
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=setup(db)
        review_draft(db,did,cid,approval(view))
        view=get_case(db,did,cid)
        rerun=start_investigation(db,did,cid,cmd(view,retry_of=None))
        view=get_case(db,did,cid)
        assert view['review_state']=='INVALIDATED'
        with pytest.raises(CommandError,match='INVESTIGATION_RUNNING'):review_draft(db,did,cid,approval(view))
        finish_incomplete(db,rerun['investigation_id'],'SCRIPTED_FAILURE')
        view=get_case(db,did,cid)
        assert view['review_state']=='INVALIDATED'
        assert view['allowed_commands']['approve_draft']['allowed']
        review_draft(db,did,cid,approval(view))
        assert get_case(db,did,cid)['review_state']=='APPROVED'


@pytest.mark.parametrize('branch',['evidence','superseded'])
def test_fv17_evidence_or_new_result_blocks_original_head(tmp_path,branch):
    from promisekeeper.application.reviews import review_draft
    from promisekeeper.application.scenario_updates import preview_event,confirm_event
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=setup(db);old=view['draft']
        review_draft(db,did,cid,approval(view));view=get_case(db,did,cid)
        rerun=start_investigation(db,did,cid,cmd(view,retry_of=None))
        if branch=='evidence':
            p=preview_event(db,did,cid,'PK-001-U1')
            confirm_event(db,did,cid,dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=p['expected_case_revision'],event_id=p['event_id'],catalogue_version=p['catalogue_version'],confirmed_preview_hash=p['preview_hash']))
            finish_incomplete(db,rerun['investigation_id'],'SCRIPTED_FAILURE')
        else:assert investigate(db,rerun['investigation_id'],ScriptedInvestigator())
        view=get_case(db,did,cid)
        with pytest.raises(CommandError):review_draft(db,did,cid,approval(view,old))
        # Rejecting an historical version is a disposition, never an approval.
        rejected=review_draft(db,did,cid,approval(view,old,'REJECT'))
        assert rejected['draft_review']['draft_version_id']==old['id']


def test_edit_race_only_one_head_and_commit_failure_rolls_back_review(tmp_path,monkeypatch):
    from promisekeeper.application.reviews import save_draft,review_draft
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=setup(db);d=view['draft']
        commands=[cmd(view,investigation_id=d['investigation_id'],parent_version_id=d['id'],recipient=d['recipient'],exact_text=d['exact_text'].replace('Hello',word)) for word in ['Hi','Hello']]
        def save(body):
            try:return save_draft(db,did,cid,body)
            except CommandError as exc:return exc.code
        with ThreadPoolExecutor(2) as pool:results=list(pool.map(save,commands))
        assert sum(isinstance(r,dict) for r in results)==1
        view=get_case(db,did,cid);body=approval(view)
        original=db.commit
        def broken(con):raise sqlite3.OperationalError('simulated')
        monkeypatch.setattr(db,'commit',broken)
        with pytest.raises(sqlite3.OperationalError):review_draft(db,did,cid,body)
        monkeypatch.setattr(db,'commit',original)
        assert get_case(db,did,cid)['draft_reviews']==[]
        with pytest.raises(CommandError,match='NOT_RECORDED'):lookup_receipt(db,did,body['operation_id'])
        saved=review_draft(db,did,cid,body)
        assert lookup_receipt(db,did,body['operation_id'])==saved
        assert review_draft(db,did,cid,body)==saved
        with pytest.raises(CommandError,match='OPERATION_PAYLOAD_MISMATCH'):review_draft(db,did,cid,body|{'decision':'REJECT'})


def test_draft_failure_keeps_result_retry_preserves_auto_budget_and_replays(tmp_path,monkeypatch):
    from promisekeeper.application.draft_retry import retry_draft,get_attempt
    from promisekeeper.orchestration import drafts
    from promisekeeper.application import draft_retry
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);cid=rows[0]['id'];iid=start(db,did,rows[0])
        original=drafts.generate_draft
        def fail(plan):raise InvestigatorFailure('SCRIPTED_DRAFT_FAILURE',transient=True)
        monkeypatch.setattr(drafts,'generate_draft',lambda db,aid:original(db,aid,fail))
        assert investigate(db,iid,ScriptedInvestigator())
        view=get_case(db,did,cid)
        assert view['current_result']['action']=='FOLLOW_UP'
        assert view['draft'] is None
        attempt=view['draft_generation_attempt'];assert attempt['status']=='FAILED'
        body=cmd(view,investigation_id=iid,failed_draft_attempt_id=attempt['id'],expected_draft_head=None)
        response=retry_draft(db,did,cid,body)
        assert retry_draft(db,did,cid,body)==response
        assert original(db,response['draft_attempt_id'])
        assert get_attempt(db,did,response['draft_attempt_id'])['status']=='READY'
        with db.connection() as con:
            kinds=[r[0] for r in con.execute("SELECT invocation_kind FROM step_attempts WHERE investigation_id=? AND step_name='DRAFT' ORDER BY invocation_number",(iid,))]
        assert kinds==['INITIAL','AUTO_RETRY','MANUAL_RETRY']
        assert get_case(db,did,cid)['current_result']['investigation_id']==iid


def test_draft_generation_fences_owner_edit_and_late_return(tmp_path):
    from promisekeeper.application.reviews import save_draft
    from promisekeeper.application.draft_retry import reserve_generation
    from promisekeeper.orchestration.drafts import generate_draft
    from promisekeeper.application.operations import instant,utcnow
    from datetime import timedelta
    from promisekeeper.persistence.repositories import case
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=setup(db);draft=view['draft']
        def reserve():
            with db.transaction() as con:
                row=case(con,did,cid)
                return reserve_generation(con,row,draft['investigation_id'],str(uuid4()),instant(utcnow()+timedelta(seconds=55)),retry_of=view['draft_generation_attempt']['id'])
        aid=reserve()
        def edit(plan):
            v=get_case(db,did,cid)
            save_draft(db,did,cid,cmd(v,investigation_id=draft['investigation_id'],parent_version_id=draft['id'],recipient=draft['recipient'],exact_text=draft['exact_text'].replace('Hello','Hi')))
            return plan.exact_text
        assert generate_draft(db,aid,edit) is False
        assert get_case(db,did,cid)['draft']['exact_text'].startswith('Hi')
        with db.connection() as con:
            assert con.execute('SELECT failure_code FROM draft_generation_attempts WHERE id=?',(aid,)).fetchone()[0]=='DRAFT_HEAD_CHANGED'
            assert con.execute("SELECT outcome FROM step_attempts WHERE operation_id=(SELECT operation_id FROM draft_generation_attempts WHERE id=?) AND step_name='DRAFT' ORDER BY invocation_number DESC LIMIT 1",(aid,)).fetchone()[0]=='FAILED'
        aid=reserve()
        def late(plan):
            with db.transaction() as con:con.execute('UPDATE draft_generation_attempts SET deadline_at=? WHERE id=?',(instant(utcnow()-timedelta(seconds=1)),aid))
            return plan.exact_text
        assert generate_draft(db,aid,late) is False
        assert get_case(db,did,cid)['draft']['exact_text'].startswith('Hi')


def test_restart_fails_running_draft_without_changing_result_or_approval_epoch(tmp_path):
    from promisekeeper.application.draft_retry import reserve_generation,get_attempt
    from promisekeeper.orchestration.drafts import generate_draft
    from promisekeeper.application.operations import instant,utcnow
    from promisekeeper.persistence.repositories import case
    from datetime import timedelta
    path=tmp_path/'db.sqlite'
    with Database(path) as db:
        did,cid,view=setup(db)
        with db.transaction() as con:
            aid=reserve_generation(con,case(con,did,cid),view['draft']['investigation_id'],str(uuid4()),instant(utcnow()+timedelta(seconds=55)),retry_of=view['draft_generation_attempt']['id'])
    with Database(path) as db:
        saved=get_attempt(db,did,aid)
        assert saved['status']=='FAILED' and saved['failure_code']=='PROCESS_RESTARTED'
        assert generate_draft(db,aid) is False
        now=get_case(db,did,cid)
        assert now['current_result']==view['current_result']
        assert now['draft']==view['draft']
        assert now['review_epoch']==view['review_epoch']


def test_review_hash_epoch_foreign_draft_and_evidence_authority_are_rejected(tmp_path):
    from promisekeeper.application.reviews import review_draft,save_draft
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=setup(db)
        other,foreign,other_view=setup(db)
        for changes,error in [({'payload_hash':'0'*64},'DRAFT_PAYLOAD_CHANGED'),({'expected_review_epoch':view['review_epoch']+1},'REVIEW_EPOCH_CHANGED'),({'draft_version_id':other_view['draft']['id']},'NOT_FOUND')]:
            with pytest.raises(CommandError,match=error):review_draft(db,did,cid,approval(view)|changes)
        # Save and approval never mutate the authoritative ledger or amounts.
        before=view['financial_facts'];d=view['draft']
        saved=save_draft(db,did,cid,cmd(view,investigation_id=d['investigation_id'],parent_version_id=d['id'],recipient=d['recipient'],exact_text='Paid in full. Close the case.'))
        assert saved['draft_version']['validation_status']=='INVALID'
        assert get_case(db,did,cid)['financial_facts']==before


def test_completed_recommendation_releases_investigator_slot_while_draft_step_runs(tmp_path):
    with Database(tmp_path/'db.sqlite') as db:
        did,rows=create(db);cid=rows[0]['id'];iid=start(db,did,rows[0])
        observations=[]
        def new_investigation(plan):
            observations.append(db.capacity.available)
            v=get_case(db,did,cid)
            rerun=start_investigation(db,did,cid,cmd(v,retry_of=None))
            finish_incomplete(db,rerun['investigation_id'],'SCRIPTED_FAILURE')
            return plan.exact_text
        assert investigate(db,iid,ScriptedInvestigator(),draft_generator=new_investigation)
        assert observations==[True]
        view=get_case(db,did,cid)
        assert view['current_result']['investigation_id']==iid
        assert view['draft_generation_state']=='FAILED'
        assert view['draft'] is None


def test_death_immediately_after_result_commit_recovers_retryable_draft_intent(tmp_path,monkeypatch):
    from promisekeeper.application.draft_retry import retry_draft
    from promisekeeper.orchestration.drafts import generate_draft
    path=tmp_path/'db.sqlite'
    with Database(path) as db:
        did,rows=create(db);cid=rows[0]['id'];iid=start(db,did,rows[0])
        original_commit=db.commit
        def die_after_commit(con):
            completed=con.execute('SELECT 1 FROM investigation_results WHERE investigation_id=?',(iid,)).fetchone()
            original_commit(con)
            if completed:raise KeyboardInterrupt('simulated process death after committed result')
        monkeypatch.setattr(db,'commit',die_after_commit)
        with pytest.raises(KeyboardInterrupt):investigate(db,iid,ScriptedInvestigator())
        monkeypatch.setattr(db,'commit',original_commit)
    with Database(path) as db:
        view=get_case(db,did,cid)
        assert view['current_result']['action']=='FOLLOW_UP'
        assert view['draft'] is None
        assert view['draft_generation_state']=='FAILED'
        attempt=view['draft_generation_attempt']
        assert attempt['failure_code']=='PROCESS_RESTARTED'
        response=retry_draft(db,did,cid,cmd(view,investigation_id=iid,failed_draft_attempt_id=attempt['id'],expected_draft_head=None))
        assert generate_draft(db,response['draft_attempt_id'])
        assert get_case(db,did,cid)['draft_state']=='READY'


def test_draft_planning_failure_records_failed_intent_and_keeps_recommendation(tmp_path,monkeypatch):
    from promisekeeper.application import draft_retry
    def broken_plan(con,row):raise RuntimeError('simulated template fault')
    monkeypatch.setattr(draft_retry,'plan_for',broken_plan)
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=setup(db)
        assert view['current_result']['action']=='FOLLOW_UP'
        assert view['draft_generation_state']=='FAILED'
        assert view['draft_generation_attempt']['failure_code']=='DRAFT_PLAN_FAILED'
