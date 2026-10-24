"""Immutable pre-update scope, exact confirmation, and rollback at the commit boundary."""

import json
import sqlite3
from uuid import uuid4

import pytest

from test_sqlite_invariants import create
from test_attempt_transactions import cases, request


def test_arrival_mid_run_preserves_packet_anchors_and_closed_lifecycle(tmp_path):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.start_investigation import start_investigation
    from promisekeeper.application.scenario_updates import preview_event, confirm_event
    with Database(tmp_path / "db.sqlite") as db:
        did = create(db)["demonstration_id"]
        cid = cases(db, did)[0]["id"]
        start = start_investigation(db, did, cid, request())
        with db.connection() as con:
            before = dict(con.execute("SELECT * FROM evidence_snapshots WHERE id=?", (start["snapshot_id"],)).fetchone())
            anchors = [dict(r) for r in con.execute("SELECT * FROM commitment_anchors WHERE case_id=?", (cid,))]
        p = preview_event(db, did, cid, "PK-001-U1")
        body = dict(schema_version="1", operation_id=str(uuid4()), expected_case_revision=1,
                    event_id=p["event_id"], catalogue_version=p["catalogue_version"], confirmed_preview_hash=p["preview_hash"])
        confirm_event(db, did, cid, body)
        with db.connection() as con:
            assert dict(con.execute("SELECT * FROM evidence_snapshots WHERE id=?", (start["snapshot_id"],)).fetchone()) == before
            assert all(dict(con.execute("SELECT * FROM commitment_anchors WHERE id=?", (a["id"],)).fetchone()) == a for a in anchors)
            assert "PK-001-M2" not in before["packet_json"]
            assert con.execute("SELECT review_epoch FROM cases WHERE id=?", (cid,)).fetchone()[0] == 2
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        # No closure command is implemented here: seed lifecycle directly to test preservation.
        with db.transaction() as con:
            con.execute("UPDATE cases SET lifecycle='CLOSED' WHERE id=?", (cases(db, did)[2]["id"],))
        closed = cases(db, did)[2]["id"]
        p = preview_event(db, did, closed, "PK-003-U1")
        confirm_event(db, did, closed, body | {"operation_id": str(uuid4()), "expected_case_revision": p["expected_case_revision"],
                                             "event_id": p["event_id"], "confirmed_preview_hash": p["preview_hash"]})
        assert cases(db, did)[2]["lifecycle"] == "CLOSED"


def test_confirmation_commit_failure_leaves_no_arrival_or_receipt(tmp_path, monkeypatch):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.scenario_updates import preview_event, confirm_event
    with Database(tmp_path / "db.sqlite") as db:
        did = create(db)["demonstration_id"]
        cid = cases(db, did)[0]["id"]
        p = preview_event(db, did, cid, "PK-001-U1")
        body = dict(schema_version="1", operation_id=str(uuid4()), expected_case_revision=0,
                    event_id=p["event_id"], catalogue_version=p["catalogue_version"], confirmed_preview_hash=p["preview_hash"])
        def fail(con):
            raise sqlite3.OperationalError("simulated disk failure")
        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(sqlite3.OperationalError):
            confirm_event(db, did, cid, body)
        assert preview_event(db, did, cid, "PK-001-U1") == p
        with db.connection() as con:
            assert con.execute("SELECT count(*) FROM operation_receipts WHERE operation_id=?", (body["operation_id"],)).fetchone()[0] == 0
