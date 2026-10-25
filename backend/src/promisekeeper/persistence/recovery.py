"""Recovery runs only after exclusive ownership and never repeats model work."""

from promisekeeper.application.operations import instant, utcnow
from promisekeeper.persistence.repositories import append_event


def recover(db):
    with db.transaction() as con:
        now = instant(utcnow())
        for row in con.execute("SELECT * FROM investigations WHERE status='RUNNING'").fetchall():
            con.execute("UPDATE investigations SET status='INCOMPLETE',terminal_at=?,failure_code='PROCESS_RESTARTED' WHERE id=?", (now, row["id"]))
            append_event(con, dict(id=row["case_id"], demonstration_id=row["demonstration_id"]), "INVESTIGATION_INCOMPLETE",
                         row["operation_id"], {"investigation_id": row["id"], "failure_code": "PROCESS_RESTARTED"})
        for row in con.execute("SELECT * FROM draft_generation_attempts WHERE status='RUNNING'").fetchall():
            con.execute("UPDATE draft_generation_attempts SET status='FAILED',terminal_at=?,failure_code='PROCESS_RESTARTED' WHERE id=?", (now, row["id"]))
            append_event(con, dict(id=row["case_id"], demonstration_id=row["demonstration_id"]), "DRAFT_FAILED",
                         row["operation_id"], {"draft_attempt_id": row["id"], "failure_code": "PROCESS_RESTARTED"})
        # An interrupted morning review would otherwise block every later review of its copy.
        con.execute("UPDATE morning_reviews SET status='FAILED',terminal_at=?,failure_code='PROCESS_RESTARTED' WHERE status='RUNNING'", (now,))
