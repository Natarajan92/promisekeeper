"""Durability tests use real files; failures must not leave a receipt or half a copy."""

import json
import sqlite3
from uuid import uuid4

import pytest


def create(db, operation_id=None, variant=None):
    from promisekeeper.application.cases import create_demonstration
    return create_demonstration(db, dict(schema_version="1", operation_id=str(operation_id or uuid4()),
                                        catalogue_version="release-0.1", variant_id=variant,
                                        clock_mode="REFERENCE"))


def test_migrations_replay_constraints_and_immutable_history(tmp_path):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.operations import CommandError
    from promisekeeper.application.cases import list_demonstrations
    with Database(tmp_path / "db.sqlite") as db:
        op = str(uuid4())
        first = create(db, op)
        assert create(db, op) == first
        assert len(list_demonstrations(db)["demonstrations"]) == 1
        with pytest.raises(CommandError, match="OPERATION_PAYLOAD_MISMATCH"):
            create(db, op, "FV-16-LINKED")
        with db.connection() as con:
            assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
            assert con.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
            assert con.execute("PRAGMA synchronous").fetchone()[0] == 3
            assert con.execute("PRAGMA busy_timeout").fetchone()[0] == 250
            assert con.execute("SELECT count(*) FROM cases").fetchone()[0] == 6
            assert con.execute("PRAGMA foreign_key_check").fetchall() == []
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("UPDATE evidence_versions SET original_content='changed'")
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("UPDATE case_events SET event_type='changed'")
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("UPDATE cases SET demonstration_id=?", (str(uuid4()),))
    with Database(tmp_path / "db.sqlite") as db:
        assert create(db, op) == first
        assert len(list_demonstrations(db)["demonstrations"]) == 1


def test_failed_commit_rolls_back_copy_events_and_receipt(tmp_path, monkeypatch):
    from promisekeeper.persistence.sqlite import Database
    with Database(tmp_path / "db.sqlite") as db:
        def fail(con):
            raise sqlite3.OperationalError("simulated disk failure")
        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(sqlite3.OperationalError):
            create(db)
        with db.connection() as con:
            for table in ("demonstrations", "cases", "evidence_versions", "case_events", "operation_receipts"):
                assert con.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


def test_selected_copy_deletion_retains_content_free_replay(tmp_path):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.cases import delete_demonstration, list_demonstrations
    from promisekeeper.application.operations import lookup_receipt
    with Database(tmp_path / "db.sqlite") as db:
        a, b = create(db), create(db)
        aid = a["demonstration_id"]
        payload = dict(schema_version="1", operation_id=str(uuid4()), confirmed_demonstration_id=aid, confirm=True)
        deleted = delete_demonstration(db, aid, payload)
        assert delete_demonstration(db, aid, payload) == deleted
        assert lookup_receipt(db, aid, payload["operation_id"]) == deleted
        assert [d["id"] for d in list_demonstrations(db)["demonstrations"]] == [b["demonstration_id"]]
        with db.connection() as con:
            assert con.execute("SELECT count(*) FROM cases WHERE demonstration_id=?", (aid,)).fetchone()[0] == 0
            rows = con.execute("SELECT response_json FROM operation_receipts WHERE demonstration_id=?", (aid,)).fetchall()
            assert len(rows) == 1
            assert all(word not in json.dumps([tuple(r) for r in rows]) for word in ("Northstar", "original_content", "PK-001"))


def test_second_process_cannot_recover_owned_database(tmp_path, run_python):
    from promisekeeper.persistence.sqlite import Database
    with Database(tmp_path / "owned.sqlite"):
        result = run_python(f'''
from promisekeeper.persistence.sqlite import Database
try:
    with Database({str(tmp_path / 'owned.sqlite')!r}): pass
except Exception as error:
    print(type(error).__name__)
else: raise SystemExit(2)
''')
        assert result.returncode == 0, result.stderr
        assert "OwnershipError" in result.stdout


def test_cross_copy_anchor_attribution_is_rejected(tmp_path):
    from promisekeeper.persistence.sqlite import Database
    with Database(tmp_path / "db.sqlite") as db:
        create(db)
        create(db)
        with db.connection() as con:
            anchors = con.execute("SELECT * FROM commitment_anchors ORDER BY demonstration_id, id").fetchall()
            a = anchors[0]
            b = next(row for row in anchors if row["demonstration_id"] != a["demonstration_id"])
            payment = con.execute("SELECT * FROM payment_projections WHERE demonstration_id=? LIMIT 1", (b["demonstration_id"],)).fetchone()
        with pytest.raises(sqlite3.IntegrityError), db.transaction() as con:
            con.execute("INSERT INTO commitment_attributions VALUES (?,?,?,?,?,?,?,?)", (
                a["evidence_version_id"], a["demonstration_id"], a["case_id"], payment["evidence_version_id"], b["id"], "100.00", "INR", "10000"))


def test_delayed_create_retry_after_deletion_never_creates_a_new_copy(tmp_path):
    from promisekeeper.persistence.sqlite import Database
    from promisekeeper.application.cases import delete_demonstration, list_demonstrations
    from promisekeeper.application.operations import CommandError, lookup_receipt
    path = tmp_path / "db.sqlite"
    operation_id = str(uuid4())
    with Database(path) as db:
        original = create(db, operation_id)
        did = original["demonstration_id"]
        delete_demonstration(db, did, dict(schema_version="1", operation_id=str(uuid4()), confirmed_demonstration_id=did, confirm=True))
    with Database(path) as db:
        replay = create(db, operation_id)
        assert replay["demonstration_id"] == did
        assert replay["receipt"]["outcome"] == "DELETED"
        assert lookup_receipt(db, did, operation_id) == replay
        assert list_demonstrations(db)["demonstrations"] == []
        with pytest.raises(CommandError, match="OPERATION_PAYLOAD_MISMATCH"):
            create(db, operation_id, "FV-16-LINKED")
