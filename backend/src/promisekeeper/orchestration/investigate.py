"""Captured evidence -> candidates -> validation -> pure rules -> atomic result, run as the case graph."""
from dataclasses import replace
import json
import threading
from promisekeeper.agents.roster import AgentSet
from promisekeeper.application.agent_activity import activity_totals, list_agent_activity
from promisekeeper.application.operations import CommandError
from promisekeeper.application.start_investigation import finish_incomplete
from promisekeeper.orchestration.case_graph import build_case_graph, graph_config
from promisekeeper.persistence.repositories import demonstration

_dispatch_lock=threading.Lock()
_dispatched=set()

def investigate(db, investigation_id, investigator, *, draft_generator=None, agents=None):
    """Run the case graph. True only when a recommendation was committed for this attempt.

    Without an AgentSet the drafting agents are absent and the standard template is used,
    which keeps direct callers on the reviewed single-Investigator behaviour.
    """
    with _dispatch_lock:
        if investigation_id in _dispatched:return False
        _dispatched.add(investigation_id)
    try:
        with db.connection() as con:
            row=con.execute("SELECT * FROM investigations WHERE id=? AND status='RUNNING'",(investigation_id,)).fetchone()
            if row is None: return False
            attempt=dict(row)
        agent_set=replace(agents,investigator=investigator) if agents else AgentSet(investigator,None,None,None)
        try:
            graph=build_case_graph(db,agent_set,draft_generator=draft_generator)
        except Exception:
            # Without the checkpoint store the owner pause is unavailable; investigation still runs.
            graph=build_case_graph(db,agent_set,draft_generator=draft_generator,pause_for_owner=False)
        try:
            graph.invoke(dict(investigation_id=investigation_id,demonstration_id=attempt['demonstration_id'],case_id=attempt['case_id'],revisions=0),
                         graph_config(investigation_id))
        except Exception as exc:
            finish_incomplete(db,investigation_id,getattr(exc,'code','INVESTIGATION_FAILED'))
        with db.connection() as con:
            saved=con.execute('SELECT 1 FROM investigation_results WHERE investigation_id=?',(investigation_id,)).fetchone()
        return saved is not None
    finally:
        db.capacity.release(investigation_id)
        db.reservations.discard(investigation_id)
        with _dispatch_lock:_dispatched.discard(investigation_id)

def get_investigation(db,did,iid,*,token_rates=None):
    with db.connection() as con:
        con.execute('BEGIN')
        demonstration(con,did)
        row=con.execute('SELECT i.*,s.hash FROM investigations i JOIN evidence_snapshots s ON s.id=i.snapshot_id WHERE i.id=? AND i.demonstration_id=?',(iid,did)).fetchone()
        if row is None: raise CommandError('NOT_FOUND',404)
        saved=con.execute('SELECT result_json FROM investigation_results WHERE investigation_id=?',(iid,)).fetchone()
        result=json.loads(saved[0]) if saved else None
        activity=list_agent_activity(con,investigation_id=iid)
        draft_attempt=con.execute('SELECT status FROM draft_generation_attempts WHERE investigation_id=? ORDER BY rowid DESC LIMIT 1',(iid,)).fetchone()
        return dict(schema_version='1',id=iid,investigation_id=iid,demonstration_id=did,case_id=row['case_id'],status=row['status'],snapshot_id=row['snapshot_id'],snapshot_hash=row['hash'],
            evaluation_at=row['evaluation_at'],deadline_at=row['deadline_at'],limitations=result['limitations'] if result else [],failure_code=row['failure_code'],result=result,action=result['action'] if result else None,
            draft_status=draft_attempt[0] if draft_attempt else 'NONE',progress=[dict(r) for r in con.execute('SELECT step_name,invocation_number,invocation_kind,started_at,ended_at,outcome,failure_code FROM step_attempts WHERE investigation_id=? AND step_name<>? ORDER BY rowid',(iid,'DRAFT'))],
            agent_activity=activity,agent_totals=activity_totals(activity,token_rates or {}))
