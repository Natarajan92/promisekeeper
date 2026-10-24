"""Captured evidence -> candidates -> validation -> pure rules -> atomic result."""
from datetime import datetime
import json
import threading
from promisekeeper.agents.protocol import InvestigatorFailure, PROMPT_VERSION, EXTRACTION_POLICY_VERSION
from promisekeeper.agents.validation import validate_output
from promisekeeper.application.findings import result_view
from promisekeeper.application.derived_findings import derive_findings
from promisekeeper.application.operations import CommandError, canonical, instant, utcnow
from promisekeeper.application.start_investigation import finish_incomplete
from promisekeeper.contracts.investigations import Result
from promisekeeper.domain.recommendations import recommend
from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.orchestration.deadlines import Budget, bounded_call
from promisekeeper.orchestration.retries import run_step
from promisekeeper.persistence.repositories import append_event, demonstration
from promisekeeper.tools.evidence import read_snapshot, snapshot_case

_dispatch_lock=threading.Lock()
_dispatched=set()

def investigate(db, investigation_id, investigator):
    with _dispatch_lock:
        if investigation_id in _dispatched:return False
        _dispatched.add(investigation_id)
    try:
        with db.connection() as con:
            row=con.execute("SELECT * FROM investigations WHERE id=? AND status='RUNNING'",(investigation_id,)).fetchone()
            if row is None: return False
            attempt=dict(row)
            raw=json.loads(con.execute('SELECT packet_json FROM evidence_snapshots WHERE id=?',(attempt['snapshot_id'],)).fetchone()[0])
        budget=Budget(attempt['deadline_at'])
        packet=run_step(db,attempt,'EVIDENCE_LOOKUP',budget,lambda:read_snapshot(db,dict(schema_version='1',snapshot_id=attempt['snapshot_id'],evidence_version_ids=[r['id'] for r in raw['evidence']])))
        case=snapshot_case(packet)
        request=dict(schema_version='1',investigation_id=investigation_id,snapshot_id=attempt['snapshot_id'],snapshot_hash=packet['snapshot_hash'],packet=packet,prompt_version=PROMPT_VERSION,extraction_policy_version=EXTRACTION_POLICY_VERSION)
        def extraction():
            timeout=min(20,budget.remaining())
            return bounded_call(lambda:investigator.extract(request,timeout=timeout),timeout)
        response=run_step(db,attempt,'EXTRACTION',budget,extraction)
        with db.transaction() as con:
            con.execute("UPDATE investigations SET returned_model=?,response_id=?,prompt_version=?,schema_version=?,adapter_version=? WHERE id=? AND status='RUNNING'",
                (response.returned_model,response.response_id,PROMPT_VERSION,'1',response.adapter_version,investigation_id))
        output,extracted=run_step(db,attempt,'VALIDATION',budget,lambda:validate_output(response.output,packet,case))
        recommendation=run_step(db,attempt,'RECONCILIATION',budget,lambda:recommend(case,extracted,datetime.fromisoformat(attempt['evaluation_at'])))
        commitment_facts=reconcile_commitments(case,extracted,recommendation.financial)
        limitations=sorted({i.code for i in (*recommendation.financial.issues,*commitment_facts.issues)}) if recommendation.status=='LIMITED' else []
        derived=derive_findings(case,extracted,recommendation,commitment_facts,packet)
        result=result_view(attempt,packet,recommendation,derived,limitations=limitations)
        Result.model_validate(result)
        budget.remaining()
        with db.transaction() as con:
            current=con.execute("SELECT status,deadline_at FROM investigations WHERE id=?",(investigation_id,)).fetchone()
            if current is None or current['status']!='RUNNING': return False
            if utcnow()>=datetime.fromisoformat(current['deadline_at']): raise InvestigatorFailure('INVESTIGATION_DEADLINE')
            con.execute('UPDATE investigations SET status=?,terminal_at=?,returned_model=?,response_id=?,prompt_version=?,schema_version=?,adapter_version=? WHERE id=? AND status=\'RUNNING\'',
                (recommendation.status,instant(utcnow()),response.returned_model,response.response_id,PROMPT_VERSION,'1',response.adapter_version,investigation_id))
            con.execute('INSERT INTO investigation_results VALUES (?,?,?,?,?,?,?,?)',
                (investigation_id,attempt['demonstration_id'],attempt['case_id'],result['action'],result['review_at'],canonical(result),result['result_hash'],'rules-1'))
            con.execute('UPDATE cases SET latest_completed_investigation_id=?,case_revision=case_revision+1 WHERE id=?',(investigation_id,attempt['case_id']))
            append_event(con,dict(id=attempt['case_id'],demonstration_id=attempt['demonstration_id']),'INVESTIGATION_COMPLETED',attempt['operation_id'],dict(investigation_id=investigation_id,status=recommendation.status,result_hash=result['result_hash']))
        return True
    except Exception as exc:
        finish_incomplete(db,investigation_id,getattr(exc,'code','INVESTIGATION_FAILED'))
        return False
    finally:
        db.capacity.release(investigation_id)
        db.reservations.discard(investigation_id)
        with _dispatch_lock:_dispatched.discard(investigation_id)

def get_investigation(db,did,iid):
    with db.connection() as con:
        con.execute('BEGIN')
        demonstration(con,did)
        row=con.execute('SELECT i.*,s.hash FROM investigations i JOIN evidence_snapshots s ON s.id=i.snapshot_id WHERE i.id=? AND i.demonstration_id=?',(iid,did)).fetchone()
        if row is None: raise CommandError('NOT_FOUND',404)
        saved=con.execute('SELECT result_json FROM investigation_results WHERE investigation_id=?',(iid,)).fetchone()
        result=json.loads(saved[0]) if saved else None
        return dict(schema_version='1',id=iid,investigation_id=iid,demonstration_id=did,case_id=row['case_id'],status=row['status'],snapshot_id=row['snapshot_id'],snapshot_hash=row['hash'],
            evaluation_at=row['evaluation_at'],deadline_at=row['deadline_at'],limitations=result['limitations'] if result else [],failure_code=row['failure_code'],result=result,action=result['action'] if result else None,
            draft_status='NOT_IMPLEMENTED',progress=[dict(r) for r in con.execute('SELECT step_name,invocation_number,invocation_kind,started_at,ended_at,outcome,failure_code FROM step_attempts WHERE investigation_id=? ORDER BY rowid',(iid,))])
