"""Seed saved workflow records for Gate II storage tests; no generation implementation."""

from uuid import uuid4

from promisekeeper.application.operations import canonical, digest, instant, utcnow


def seed_completed(db, start, *, action="FOLLOW_UP", review_at=None):
    iid = start["investigation_id"]
    result = dict(investigation_id=iid, snapshot_id=start["snapshot_id"], evaluation_at=start["evaluation_at"],
                  action=action, review_at=review_at)
    with db.transaction() as con:
        row = con.execute("SELECT * FROM investigations WHERE id=?", (iid,)).fetchone()
        con.execute("UPDATE investigations SET status='COMPLETE',terminal_at=? WHERE id=?", (instant(utcnow()), iid))
        con.execute("INSERT INTO investigation_results VALUES (?,?,?,?,?,?,?,?)", (
            iid, row["demonstration_id"], row["case_id"], action, review_at, canonical(result), digest(result), "gate-ii-test-record"))
        con.execute("UPDATE cases SET latest_completed_investigation_id=? WHERE id=?", (iid, row["case_id"]))
    db.capacity.release(iid)
    db.reservations.discard(iid)
    return result


def seed_approved_draft(db, start):
    iid = start["investigation_id"]
    vid, rid = str(uuid4()), str(uuid4())
    with db.transaction() as con:
        row = con.execute("SELECT * FROM investigations WHERE id=?", (iid,)).fetchone()
        case = con.execute("SELECT * FROM cases WHERE id=?", (row["case_id"],)).fetchone()
        con.execute("INSERT INTO draft_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            vid, row["demonstration_id"], row["case_id"], iid, None, "fictional@example.invalid", case["invoice_id"],
            "Hello. Please review the fictional invoice.", 1, "a" * 64, instant(utcnow()), "VALID", "[]"))
        con.execute("UPDATE cases SET current_draft_version_id=? WHERE id=?", (vid, row["case_id"]))
        con.execute("INSERT INTO draft_reviews VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            rid, row["demonstration_id"], row["case_id"], str(uuid4()), vid, "fictional-owner", "APPROVE", instant(utcnow()),
            "Hello. Please review the fictional invoice.", "fictional@example.invalid", case["invoice_id"], "a" * 64,
            iid, case["evidence_revision"], case["review_epoch"]))
    return vid, rid
