"""Durable bounded retries of the draft step, never of a recommendation."""
from datetime import timedelta
from uuid import uuid4
from promisekeeper.application.operations import CommandError, instant, replay, save_receipt, utcnow
from promisekeeper.application.reviews import eligibility, plan_for, attempt_view
from promisekeeper.persistence.repositories import append_event, case, demonstration, require_revision


def reserve_generation(con,row,investigation_id,operation_id,deadline_at,*,retry_of=None):
    aid=str(uuid4());now=instant(utcnow())
    con.execute('''INSERT INTO draft_generation_attempts
        (id,demonstration_id,case_id,investigation_id,operation_id,retry_of,expected_draft_head,status,started_at,deadline_at)
        VALUES (?,?,?,?,?,?,?,'RUNNING',?,?)''',(aid,row['demonstration_id'],row['id'],investigation_id,operation_id,retry_of,row['current_draft_version_id'],now,deadline_at))
    append_event(con,row,'DRAFT_GENERATION_STARTED',operation_id,dict(draft_attempt_id=aid,review_epoch=row['review_epoch'],evidence_revision=row['evidence_revision'],investigation_id=investigation_id))
    return aid


def reserve_initial(con,investigation_id):
    """Reserve required draft intent in the transaction that saves its result."""
    investigation=con.execute('SELECT * FROM investigations WHERE id=?',(investigation_id,)).fetchone()
    if investigation is None:return None
    row=case(con,investigation['demonstration_id'],investigation['case_id'])
    if eligibility(con,row,investigation_id):return None
    existing=con.execute('SELECT id FROM draft_generation_attempts WHERE investigation_id=? ORDER BY rowid DESC LIMIT 1',(investigation_id,)).fetchone()
    if existing:return existing[0]
    try:
        needed=plan_for(con,row).exact_text is not None
    except Exception:
        # A template fault is a draft failure, never a failed recommendation.
        aid=reserve_generation(con,row,investigation_id,investigation['operation_id'],investigation['deadline_at'])
        con.execute("UPDATE draft_generation_attempts SET status='FAILED',terminal_at=?,failure_code='DRAFT_PLAN_FAILED' WHERE id=?",(instant(utcnow()),aid))
        append_event(con,row,'DRAFT_FAILED',investigation['operation_id'],dict(draft_attempt_id=aid,failure_code='DRAFT_PLAN_FAILED'))
        return aid
    if not needed:return None
    return reserve_generation(con,row,investigation_id,investigation['operation_id'],investigation['deadline_at'])


def retry_draft(db,did,cid,request):
    with db.transaction() as con:
        saved=replay(con,did,'RETRY_DRAFT',cid,request)
        if saved:return saved
        row=case(con,did,cid);require_revision(row,request)
        failed=con.execute('SELECT * FROM draft_generation_attempts WHERE id=? AND demonstration_id=? AND case_id=?',(request['failed_draft_attempt_id'],did,cid)).fetchone()
        if failed is None:raise CommandError('NOT_FOUND',404)
        if failed['status']!='FAILED' or failed['investigation_id']!=request['investigation_id']:raise CommandError('INVALID_DRAFT_RETRY')
        latest=con.execute('SELECT id FROM draft_generation_attempts WHERE investigation_id=? ORDER BY rowid DESC LIMIT 1',(request['investigation_id'],)).fetchone()
        if latest is None or latest[0]!=failed['id']:raise CommandError('DRAFT_RETRY_SUPERSEDED')
        if row['current_draft_version_id']!=request['expected_draft_head']:raise CommandError('DRAFT_HEAD_CHANGED')
        blocks=eligibility(con,row,request['investigation_id'])
        if blocks:raise CommandError(blocks[0])
        if plan_for(con,row).exact_text is None:raise CommandError('NO_DRAFT_REQUIRED')
        aid=reserve_generation(con,row,request['investigation_id'],request['operation_id'],instant(utcnow()+timedelta(seconds=55)),retry_of=failed['id'])
        con.execute('UPDATE cases SET case_revision=case_revision+1 WHERE id=?',(cid,))
        return save_receipt(con,did,'RETRY_DRAFT',cid,request,'STARTED',revision=row['case_revision']+1,draft_attempt_id=aid)


def get_attempt(db,did,aid):
    with db.connection() as con:
        con.execute('BEGIN');demonstration(con,did)
        row=con.execute('SELECT * FROM draft_generation_attempts WHERE demonstration_id=? AND id=?',(did,aid)).fetchone()
        if row is None:raise CommandError('NOT_FOUND',404)
        return dict(schema_version='1',**attempt_view(con,row))
