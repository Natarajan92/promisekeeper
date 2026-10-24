"""Start transactions must own capacity before invalidating persisted review state."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from test_sqlite_invariants import create


def cases(db, demo_id):
    with db.connection() as con:
        return [dict(r) for r in con.execute("SELECT * FROM cases WHERE demonstration_id=? ORDER BY catalogue_case_id", (demo_id,))]


def request(revision=0):
    return dict(schema_version="1", operation_id=str(uuid4()), expected_case_revision=revision, retry_of=None)


@pytest.mark.parametrize("same_case", [True, False])
def test_concurrent_starts_reserve_one_global_slot_and_replay_before_busy(tmp_path, same_case):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.start_investigation import start_investigation, finish_incomplete
    from promisekeeper.application.operations import CommandError
    with Database(tmp_path / "db.sqlite") as db:
        did = create(db)["demonstration_id"]
        rows = cases(db, did)
        pairs = [(rows[0]["id"], request()), (rows[0 if same_case else 1]["id"], request())]
        def start(pair):
            try:
                return start_investigation(db, did, *pair)
            except CommandError as exc:
                return exc.code
        with ThreadPoolExecutor(2) as pool:
            outcomes = list(pool.map(start, pairs))
        saved = [r for r in outcomes if isinstance(r, dict)]
        assert len(saved) == 1
        assert [r for r in outcomes if isinstance(r, str)] == ["INVESTIGATOR_BUSY"]
        index = next(i for i, r in enumerate(outcomes) if isinstance(r, dict))
        assert start(pairs[index]) == saved[0]
        with db.connection() as con:
            assert con.execute("SELECT count(*) FROM investigations WHERE status='RUNNING'").fetchone()[0] == 1
            assert sum(r["review_epoch"] for r in cases(db, did)) == 1
        finish_incomplete(db, saved[0]["investigation_id"], "SCRIPTED_FAILURE")
        assert db.capacity.available


def test_failed_start_commit_releases_capacity_and_preserves_revision(tmp_path, monkeypatch):
    import sqlite3
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.start_investigation import start_investigation
    with Database(tmp_path / "db.sqlite") as db:
        did = create(db)["demonstration_id"]
        row = cases(db, did)[0]
        def fail(con):
            raise sqlite3.OperationalError("simulated failed commit")
        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(sqlite3.OperationalError):
            start_investigation(db, did, row["id"], request())
        assert db.capacity.available
        assert cases(db, did)[0]["review_epoch"] == 0
        with db.connection() as con:
            assert con.execute("SELECT count(*) FROM investigations").fetchone()[0] == 0
            assert con.execute("SELECT count(*) FROM evidence_snapshots").fetchone()[0] == 0


def test_restart_marks_running_incomplete_fences_late_writes_and_keeps_epoch(tmp_path):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.start_investigation import start_investigation, finish_incomplete
    path = tmp_path / "db.sqlite"
    with Database(path) as db:
        did = create(db)["demonstration_id"]
        cid = cases(db, did)[0]["id"]
        started = start_investigation(db, did, cid, request())
    with Database(path) as db:
        with db.connection() as con:
            old = dict(con.execute("SELECT * FROM investigations").fetchone())
            assert old["status"] == "INCOMPLETE"
            assert old["failure_code"] == "PROCESS_RESTARTED"
            assert cases(db, did)[0]["review_epoch"] == 1
            assert con.execute("SELECT count(*) FROM investigation_results").fetchone()[0] == 0
        assert finish_incomplete(db, started["investigation_id"], "LATE_OUTPUT") is False
        again = start_investigation(db, did, cid, request(1))
        assert again["investigation_id"] != started["investigation_id"]


def test_same_operation_concurrently_replays_exact_start(tmp_path):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.start_investigation import start_investigation
    with Database(tmp_path / "db.sqlite") as db:
        did = create(db)["demonstration_id"]
        cid = cases(db, did)[0]["id"]
        payload = request()
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: start_investigation(db, did, cid, payload), range(2)))
        assert results[0] == results[1]


def test_recovery_preserves_result_draft_review_epochs_and_retry_budget(tmp_path):
    import sqlite3
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.start_investigation import start_investigation
    from support.workflow_records import seed_completed, seed_approved_draft
    path = tmp_path / "db.sqlite"
    with Database(path) as db:
        did = create(db)["demonstration_id"]
        cid = cases(db, did)[0]["id"]
        first = start_investigation(db, did, cid, request())
        seed_completed(db, first)
        vid, rid = seed_approved_draft(db, first)
        rerun = start_investigation(db, did, cid, request(1))
        with db.transaction() as con:
            con.execute("""INSERT INTO draft_generation_attempts
                (id,demonstration_id,case_id,investigation_id,operation_id,expected_draft_head,status,started_at,deadline_at)
                VALUES (?,?,?,?,?,?,'RUNNING',?,?)""", (str(uuid4()), did, cid, first["investigation_id"], str(uuid4()),
                    vid, first["evaluation_at"], rerun["deadline_at"]))
            con.execute("INSERT INTO step_attempts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                str(uuid4()), did, cid, first["investigation_id"], "DRAFT", 2, "AUTO_RETRY", str(uuid4()),
                first["evaluation_at"], None, None, None))
    with Database(path) as db:
        with db.connection() as con:
            row = cases(db, did)[0]
            assert row["review_epoch"] == 2
            assert row["current_draft_version_id"] == vid
            assert row["latest_completed_investigation_id"] == first["investigation_id"]
            assert con.execute("SELECT count(*) FROM investigation_results").fetchone()[0] == 1
            assert con.execute("SELECT status FROM draft_generation_attempts").fetchone()[0] == "FAILED"
            review = con.execute("SELECT * FROM draft_reviews WHERE id=?", (rid,)).fetchone()
            assert review["review_epoch"] == 1 != row["review_epoch"]
            assert con.execute("SELECT count(*) FROM step_attempts WHERE invocation_kind='AUTO_RETRY'").fetchone()[0] == 1
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("INSERT INTO step_attempts VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", (
                str(uuid4()), did, cid, first["investigation_id"], "DRAFT", 3, "AUTO_RETRY", str(uuid4()),
                first["evaluation_at"], None, None, None))
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("UPDATE investigations SET status='COMPLETE' WHERE id=?", (rerun["investigation_id"],))
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("UPDATE draft_generation_attempts SET status='READY'")
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("UPDATE step_attempts SET invocation_kind='MANUAL_RETRY'")
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("DELETE FROM step_attempts")
