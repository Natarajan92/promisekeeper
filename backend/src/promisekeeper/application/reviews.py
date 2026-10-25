"""Atomic immutable edits, exact reviews and server-derived eligibility."""
import json
from datetime import datetime
from uuid import uuid4

from promisekeeper.application.operations import CommandError, canonical, digest, instant, replay, save_receipt, utcnow
from promisekeeper.application.draft_templates import build_draft_plan
from promisekeeper.application.feedback import record_edit_diff
from promisekeeper.domain.draft_validation import validate_draft
from promisekeeper.persistence.repositories import append_event, case, demonstration, evaluation_at, require_revision


def result_context(con, row, investigation_id):
    result = con.execute('''SELECT r.*,s.evidence_revision,s.hash AS snapshot_hash,i.snapshot_id FROM investigation_results r
        JOIN investigations i ON i.id=r.investigation_id JOIN evidence_snapshots s ON s.id=i.snapshot_id
        WHERE r.investigation_id=? AND r.case_id=? AND r.demonstration_id=?''',
        (investigation_id,row['id'],row['demonstration_id'])).fetchone()
    if result is None:
        raise CommandError('NOT_FOUND',404)
    return dict(result)


def eligibility(con, row, investigation_id):
    context=result_context(con,row,investigation_id)
    blocks=[]
    if row['lifecycle']!='OPEN': blocks.append('CASE_CLOSED')
    if row['latest_completed_investigation_id']!=investigation_id: blocks.append('RESULT_SUPERSEDED')
    if context['evidence_revision']!=row['evidence_revision']: blocks.append('EVIDENCE_CHANGED')
    if context['review_at'] and evaluation_at(demonstration(con,row['demonstration_id']))>=datetime.fromisoformat(context['review_at']): blocks.append('TIME_EXPIRED')
    if con.execute("SELECT 1 FROM investigations WHERE case_id=? AND status='RUNNING'",(row['id'],)).fetchone(): blocks.append('INVESTIGATION_RUNNING')
    return blocks


def draft_view(con, draft):
    value=dict(draft)
    value['validation_reasons']=json.loads(value.pop('validation_reasons_json'))
    value['evidence_revision']=con.execute('''SELECT s.evidence_revision FROM investigations i
        JOIN evidence_snapshots s ON s.id=i.snapshot_id WHERE i.id=?''',(value['investigation_id'],)).fetchone()[0]
    return value


def get_draft(con, did, cid, vid):
    value=con.execute('SELECT * FROM draft_versions WHERE id=? AND case_id=? AND demonstration_id=?',(vid,cid,did)).fetchone()
    if value is None: raise CommandError('NOT_FOUND',404)
    return dict(value)


def plan_for(con, row):
    from promisekeeper.application.cases import _case_view
    from promisekeeper.persistence.repositories import load_fixture
    return build_draft_plan(_case_view(con,row['demonstration_id'],row['id'],load_fixture(con,row['demonstration_id']),demonstration(con,row['demonstration_id']),include_reviews=False))


def insert_draft(con, row, investigation_id, parent, exact_text, recipient, operation_id):
    plan=plan_for(con,row)
    if recipient not in plan.allowed_recipients: raise CommandError('UNSUPPORTED_RECIPIENT',422)
    reasons=validate_draft(plan,exact_text,recipient)
    context=result_context(con,row,investigation_id)
    vid=str(uuid4())
    version=con.execute('SELECT coalesce(max(version),0)+1 FROM draft_versions WHERE case_id=?',(row['id'],)).fetchone()[0]
    payload_hash=digest(dict(hash_version='draft-1',demonstration_id=row['demonstration_id'],case_id=row['id'],
        draft_version_id=vid,investigation_id=investigation_id,recipient=recipient,invoice_id=row['invoice_id'],exact_text=exact_text,
        result_hash=context['result_hash'],snapshot_id=context['snapshot_id'],snapshot_hash=context['snapshot_hash'],evidence_revision=context['evidence_revision']))
    con.execute('''INSERT INTO draft_versions
        (id,demonstration_id,case_id,investigation_id,parent_version_id,recipient,invoice_id,exact_text,version,payload_hash,created_at,validation_status,validation_reasons_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',(vid,row['demonstration_id'],row['id'],investigation_id,parent,recipient,row['invoice_id'],exact_text,version,payload_hash,instant(utcnow()),'INVALID' if reasons else 'VALID',canonical(reasons)))
    con.execute('UPDATE cases SET current_draft_version_id=?,case_revision=case_revision+1,review_epoch=review_epoch+1 WHERE id=?',(vid,row['id']))
    append_event(con,row,'DRAFT_SAVED',operation_id,dict(draft_version_id=vid,investigation_id=investigation_id))
    return draft_view(con,get_draft(con,row['demonstration_id'],row['id'],vid))


def save_draft(db,did,cid,request):
    with db.transaction() as con:
        saved=replay(con,did,'SAVE_DRAFT',cid,request)
        if saved: return saved
        row=case(con,did,cid);require_revision(row,request)
        get_draft(con,did,cid,request['parent_version_id'])
        if request['parent_version_id']!=row['current_draft_version_id']: raise CommandError('DRAFT_HEAD_CHANGED')
        blocks=eligibility(con,row,request['investigation_id'])
        if blocks: raise CommandError(blocks[0])
        parent=get_draft(con,did,cid,request['parent_version_id'])
        if parent['investigation_id']!=request['investigation_id']: raise CommandError('RESULT_SUPERSEDED')
        draft=insert_draft(con,row,request['investigation_id'],parent['id'],request['exact_text'],request['recipient'],request['operation_id'])
        return save_receipt(con,did,'SAVE_DRAFT',cid,request,'SAVED',revision=row['case_revision']+1,draft_version=draft)


def review_draft(db,did,cid,request):
    with db.transaction() as con:
        saved=replay(con,did,'REVIEW_DRAFT',cid,request)
        if saved: return saved
        row=case(con,did,cid);require_revision(row,request)
        draft=get_draft(con,did,cid,request['draft_version_id'])
        if request['payload_hash']!=draft['payload_hash']: raise CommandError('DRAFT_PAYLOAD_CHANGED')
        if request['expected_review_epoch']!=row['review_epoch']: raise CommandError('REVIEW_EPOCH_CHANGED')
        if request['decision']=='APPROVE':
            if row['current_draft_version_id']!=draft['id']: raise CommandError('DRAFT_HEAD_CHANGED')
            blocks=eligibility(con,row,draft['investigation_id'])
            if blocks: raise CommandError(blocks[0])
            reasons=validate_draft(plan_for(con,row),draft['exact_text'],draft['recipient'])
            if reasons: raise CommandError(reasons[0])
        context=result_context(con,row,draft['investigation_id'])
        review=dict(id=str(uuid4()),demonstration_id=did,case_id=cid,operation_id=request['operation_id'],draft_version_id=draft['id'],owner_actor='fictional-owner',decision=request['decision'],decided_at=instant(utcnow()),exact_text=draft['exact_text'],recipient=draft['recipient'],invoice_id=draft['invoice_id'],payload_hash=draft['payload_hash'],investigation_id=draft['investigation_id'],evidence_revision=context['evidence_revision'],review_epoch=row['review_epoch'])
        con.execute('''INSERT INTO draft_reviews
            (id,demonstration_id,case_id,operation_id,draft_version_id,owner_actor,decision,decided_at,exact_text,recipient,invoice_id,payload_hash,investigation_id,evidence_revision,review_epoch)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',tuple(review.values()))
        if request['decision']=='APPROVE':
            # Learning signal only: a failure here never blocks the owner's approval.
            con.execute('SAVEPOINT edit_feedback')
            try:
                record_edit_diff(con,draft)
                con.execute('RELEASE edit_feedback')
            except Exception:
                con.execute('ROLLBACK TO edit_feedback');con.execute('RELEASE edit_feedback')
        con.execute('UPDATE cases SET case_revision=case_revision+1 WHERE id=?',(cid,))
        append_event(con,row,'DRAFT_REVIEWED',request['operation_id'],dict(draft_review_id=review['id'],decision=request['decision'],draft_version_id=draft['id']))
        return save_receipt(con,did,'REVIEW_DRAFT',cid,request,'RECORDED',revision=row['case_revision']+1,draft_review=review)


def attempt_view(con, attempt):
    value=dict(attempt)
    event=con.execute("SELECT payload_json FROM case_events WHERE case_id=? AND event_type='DRAFT_READY' AND json_extract(payload_json,'$.draft_attempt_id')=? ORDER BY sequence DESC LIMIT 1",(value['case_id'],value['id'])).fetchone()
    value['draft_version_id']=json.loads(event[0])['draft_version_id'] if event else None
    return value


def review_projection(con,row,view):
    draft=draft_view(con,get_draft(con,row['demonstration_id'],row['id'],row['current_draft_version_id'])) if row['current_draft_version_id'] else None
    reviews=[dict(r) for r in con.execute('SELECT * FROM draft_reviews WHERE case_id=? ORDER BY rowid',(row['id'],))]
    attempt=con.execute('SELECT * FROM draft_generation_attempts WHERE case_id=? AND investigation_id=? ORDER BY rowid DESC LIMIT 1',(row['id'],row['latest_completed_investigation_id'])).fetchone()
    plan=build_draft_plan(view)
    state='UNAPPROVED' if draft else 'NONE'
    current_reviews=[r for r in reviews if draft and r['draft_version_id']==draft['id']]
    if current_reviews:
        latest=current_reviews[-1]
        if latest['decision']=='REJECT': state='REJECTED'
        elif latest['review_epoch']==row['review_epoch'] and not eligibility(con,row,draft['investigation_id']): state='APPROVED'
        else: state='INVALIDATED'
    blocks=eligibility(con,row,draft['investigation_id']) if draft else ['NO_DRAFT']
    edit_blocks=list(blocks)
    approve_blocks=list(blocks)+(draft['validation_reasons'] if draft else [])
    view['allowed_commands']['edit_draft']=dict(allowed=not edit_blocks,blocking_reasons=edit_blocks)
    view['allowed_commands']['approve_draft']=dict(allowed=not approve_blocks,blocking_reasons=approve_blocks)
    view['allowed_commands']['reject_draft']=dict(allowed=bool(draft),blocking_reasons=[] if draft else ['NO_DRAFT'])
    retry_blocks=eligibility(con,row,attempt['investigation_id']) if attempt else ['NO_FAILED_DRAFT_ATTEMPT']
    if attempt and attempt['status']!='FAILED': retry_blocks.append('NO_FAILED_DRAFT_ATTEMPT')
    if plan.exact_text is None: retry_blocks.append('NO_DRAFT_REQUIRED')
    view['allowed_commands']['retry_draft']=dict(allowed=not retry_blocks,blocking_reasons=retry_blocks)
    view.update(draft=draft,draft_reviews=reviews,draft_generation_attempt=attempt_view(con,attempt) if attempt else None,
        no_draft_reason=plan.no_draft_reason,draft_state='READY' if draft else 'NONE',review_state=state,draft_generation_state=attempt['status'] if attempt else 'NONE')
    return view
