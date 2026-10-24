"""Durable start plumbing; Gate III will supply the Investigator worker."""

from datetime import timedelta
from uuid import uuid4

from promisekeeper.application.operations import CommandError, instant, replay, save_receipt, utcnow
from promisekeeper.persistence.repositories import append_event, capture_snapshot, case, demonstration, evaluation_at, require_revision


def start_investigation(db, did, cid, request, *, agent_mode="STUB", requested_model=None):
    with db.connection() as con:
        existing = replay(con, did, "START_INVESTIGATION", cid, request)
        if existing:
            return existing
    iid = str(uuid4())
    if not db.capacity.reserve(iid):
        db.capacity.await_start()
        with db.connection() as con:
            existing = replay(con, did, "START_INVESTIGATION", cid, request)
            if existing:
                return existing
        raise CommandError("INVESTIGATOR_BUSY", 503, operation_id=request["operation_id"])
    db.reservations.add(iid)
    persisted = False
    try:
        with db.transaction() as con:
            existing = replay(con, did, "START_INVESTIGATION", cid, request)
            if existing:
                return existing
            row = case(con, did, cid)
            require_revision(row, request)
            if row["lifecycle"] != "OPEN":
                raise CommandError("CASE_CLOSED")
            if request["retry_of"] is not None:
                previous = con.execute("SELECT status FROM investigations WHERE demonstration_id=? AND case_id=? AND id=?",
                                       (did, cid, request["retry_of"])).fetchone()
                if previous is None or previous[0] != "INCOMPLETE":
                    raise CommandError("INVALID_REQUEST", 422)
            sid = capture_snapshot(con, row)
            started = utcnow()
            evaluated = evaluation_at(demonstration(con, did))
            deadline = started + timedelta(seconds=55)
            con.execute("""INSERT INTO investigations
                (id,demonstration_id,case_id,operation_id,retry_of,started_at,evaluation_at,deadline_at,snapshot_id,status,agent_mode,requested_model)
                VALUES (?,?,?,?,?,?,?,?,?,'RUNNING',?,?)""", (
                iid, did, cid, request["operation_id"], request["retry_of"], instant(started), instant(evaluated), instant(deadline), sid, agent_mode, requested_model))
            con.execute("UPDATE cases SET case_revision=case_revision+1,review_epoch=review_epoch+1 WHERE id=?", (cid,))
            append_event(con, row, "APPROVAL_INVALIDATED", request["operation_id"], {"reason": "INVESTIGATION_STARTED"})
            append_event(con, row, "INVESTIGATION_STARTED", request["operation_id"], {"investigation_id": iid, "snapshot_id": sid})
            response = save_receipt(con, did, "START_INVESTIGATION", cid, request, "STARTED",
                                    revision=row["case_revision"] + 1, investigation_id=iid, snapshot_id=sid,
                                    evaluation_at=instant(evaluated), deadline_at=instant(deadline))
        persisted = True
        db.capacity.persisted(iid)
        return response
    finally:
        if not persisted:
            db.capacity.release(iid)
            db.reservations.discard(iid)


def finish_incomplete(db, investigation_id, failure_code):
    with db.transaction() as con:
        row = con.execute("SELECT * FROM investigations WHERE id=? AND status='RUNNING'", (investigation_id,)).fetchone()
        if row is None:
            return False
        con.execute("UPDATE investigations SET status='INCOMPLETE',terminal_at=?,failure_code=? WHERE id=? AND status='RUNNING'",
                    (instant(utcnow()), failure_code, investigation_id))
        append_event(con, dict(id=row["case_id"], demonstration_id=row["demonstration_id"]),
                     "INVESTIGATION_INCOMPLETE", row["operation_id"], {"investigation_id": investigation_id, "failure_code": failure_code})
    db.capacity.release(investigation_id)
    db.reservations.discard(investigation_id)
    return True
