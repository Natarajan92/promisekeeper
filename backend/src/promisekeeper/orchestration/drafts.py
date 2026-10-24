"""Draft workers are independently fenced after the saved recommendation."""
from datetime import datetime
import json
import threading
from uuid import uuid4
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.application.operations import CommandError,instant,utcnow
from promisekeeper.application.reviews import eligibility,insert_draft,plan_for
from promisekeeper.orchestration.deadlines import Budget,bounded_call
from promisekeeper.persistence.repositories import append_event,case

_lock=threading.Lock()
_dispatched=set()


def failure(db,aid,code):
    with db.transaction() as con:
        attempt=con.execute("SELECT * FROM draft_generation_attempts WHERE id=? AND status='RUNNING'",(aid,)).fetchone()
        if attempt is None:return False
        con.execute("UPDATE draft_generation_attempts SET status='FAILED',terminal_at=?,failure_code=? WHERE id=? AND status='RUNNING'",(instant(utcnow()),code,aid))
        con.execute("UPDATE step_attempts SET ended_at=?,outcome='FAILED',failure_code=? WHERE operation_id=? AND step_name='DRAFT' AND ended_at IS NULL",(instant(utcnow()),code,attempt['operation_id']))
        append_event(con,dict(id=attempt['case_id'],demonstration_id=attempt['demonstration_id']),'DRAFT_FAILED',attempt['operation_id'],dict(draft_attempt_id=aid,failure_code=code))
        return True


def _fence(con,attempt):
    current=con.execute('SELECT status,deadline_at FROM draft_generation_attempts WHERE id=?',(attempt['id'],)).fetchone()
    if current is None or current[0]!='RUNNING':raise CommandError('TERMINAL_DRAFT_ATTEMPT')
    if utcnow()>=datetime.fromisoformat(current['deadline_at']):raise CommandError('DRAFT_DEADLINE')
    row=case(con,attempt['demonstration_id'],attempt['case_id'])
    event=con.execute("SELECT payload_json FROM case_events WHERE case_id=? AND event_type='DRAFT_GENERATION_STARTED' AND json_extract(payload_json,'$.draft_attempt_id')=?",(row['id'],attempt['id'])).fetchone()
    if event is None:raise CommandError('DRAFT_CONTEXT_MISSING')
    captured=json.loads(event[0])
    if row['current_draft_version_id']!=attempt['expected_draft_head']:raise CommandError('DRAFT_HEAD_CHANGED')
    if row['review_epoch']!=captured['review_epoch']:raise CommandError('REVIEW_EPOCH_CHANGED')
    blocks=eligibility(con,row,attempt['investigation_id'])
    if blocks:raise CommandError(blocks[0])
    return row


def generate_draft(db,aid,generator=None):
    with _lock:
        if aid in _dispatched:return False
        _dispatched.add(aid)
    try:
        with db.connection() as con:
            saved=con.execute("SELECT * FROM draft_generation_attempts WHERE id=? AND status='RUNNING'",(aid,)).fetchone()
            if saved is None:return False
            attempt=dict(saved)
        budget=Budget(attempt['deadline_at'])
        manual=bool(attempt['retry_of']);first=True
        while True:
            budget.remaining()
            with db.transaction() as con:
                row=_fence(con,attempt);plan=plan_for(con,row)
                steps=con.execute("SELECT * FROM step_attempts WHERE investigation_id=? AND step_name='DRAFT' ORDER BY invocation_number",(attempt['investigation_id'],)).fetchall()
                kind=('MANUAL_RETRY' if manual else 'INITIAL') if first else 'AUTO_RETRY'
                sid=str(uuid4())
                con.execute('''INSERT INTO step_attempts
                    (id,demonstration_id,case_id,investigation_id,step_name,invocation_number,invocation_kind,operation_id,started_at)
                    VALUES (?,?,?,?,'DRAFT',?,?,?,?)''',(sid,attempt['demonstration_id'],attempt['case_id'],attempt['investigation_id'],len(steps)+1,kind,attempt['operation_id'],instant(utcnow())))
            try:
                text=bounded_call(lambda:generator(plan) if generator else plan.exact_text,min(20,budget.remaining()))
                budget.remaining()
                if not isinstance(text,str) or not 1<=len(text)<=8000:raise InvestigatorFailure('INVALID_GENERATED_DRAFT')
            except Exception as exc:
                transient=isinstance(exc,InvestigatorFailure) and exc.transient
                with db.transaction() as con:
                    con.execute('UPDATE step_attempts SET ended_at=?,outcome=?,failure_code=? WHERE id=? AND ended_at IS NULL',(instant(utcnow()),'TRANSIENT_FAILURE' if transient else 'FAILED',getattr(exc,'code','DRAFT_FAILED'),sid))
                    consumed=con.execute("SELECT 1 FROM step_attempts WHERE investigation_id=? AND step_name='DRAFT' AND invocation_kind='AUTO_RETRY'",(attempt['investigation_id'],)).fetchone()
                if transient and not consumed and first:
                    first=False;continue
                raise
            with db.transaction() as con:
                row=_fence(con,attempt)
                draft=insert_draft(con,row,attempt['investigation_id'],attempt['expected_draft_head'],text,plan.recipient,attempt['operation_id'])
                con.execute("UPDATE step_attempts SET ended_at=?,outcome='SUCCEEDED' WHERE id=? AND ended_at IS NULL",(instant(utcnow()),sid))
                con.execute("UPDATE draft_generation_attempts SET status='READY',terminal_at=? WHERE id=? AND status='RUNNING'",(instant(utcnow()),aid))
                append_event(con,row,'DRAFT_READY',attempt['operation_id'],dict(draft_attempt_id=aid,draft_version_id=draft['id']))
            return True
    except Exception as exc:
        failure(db,aid,getattr(exc,'code','DRAFT_FAILED'));return False
    finally:
        with _lock:_dispatched.discard(aid)
