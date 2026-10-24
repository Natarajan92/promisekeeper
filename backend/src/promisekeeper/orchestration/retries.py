"""Step reservations are persisted before calls; retries never erase prior usage."""
from uuid import uuid4
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.application.operations import instant, utcnow

def run_step(db, attempt, name, budget, call):
    while True:
        budget.remaining()
        with db.transaction() as con:
            current=con.execute('SELECT status FROM investigations WHERE id=?',(attempt['id'],)).fetchone()
            if current is None or current[0]!='RUNNING': raise InvestigatorFailure('TERMINAL_ATTEMPT')
            rows=con.execute('SELECT * FROM step_attempts WHERE investigation_id=? AND step_name=? ORDER BY invocation_number',(attempt['id'],name)).fetchall()
            if not rows: kind='INITIAL'
            elif len(rows)==1 and rows[0]['ended_at'] and rows[0]['outcome']=='TRANSIENT_FAILURE': kind='AUTO_RETRY'
            else: raise InvestigatorFailure('STEP_RETRY_EXHAUSTED')
            sid=str(uuid4())
            con.execute('INSERT INTO step_attempts (id,demonstration_id,case_id,investigation_id,step_name,invocation_number,invocation_kind,operation_id,started_at) VALUES (?,?,?,?,?,?,?,?,?)',
                (sid,attempt['demonstration_id'],attempt['case_id'],attempt['id'],name,len(rows)+1,kind,attempt['operation_id'],instant(utcnow())))
        try:
            value=call()
            budget.remaining()
        except Exception as exc:
            transient=isinstance(exc,InvestigatorFailure) and exc.transient
            with db.transaction() as con:
                con.execute('UPDATE step_attempts SET ended_at=?,outcome=?,failure_code=? WHERE id=? AND ended_at IS NULL',
                    (instant(utcnow()),'TRANSIENT_FAILURE' if transient else 'FAILED',getattr(exc,'code','STEP_FAILED'),sid))
            if transient and kind=='INITIAL': continue
            raise
        with db.transaction() as con:
            con.execute("UPDATE step_attempts SET ended_at=?,outcome='SUCCEEDED' WHERE id=? AND ended_at IS NULL",(instant(utcnow()),sid))
        return value
