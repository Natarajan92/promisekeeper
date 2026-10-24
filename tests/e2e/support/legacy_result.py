"""One insert-only pre-profile fixture for a stopped, test-owned SQLite server."""

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys
from uuid import uuid4

from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.persistence.sqlite import Database


def stored(con, iid):
    row = con.execute(
        'SELECT result_json,result_hash FROM investigation_results WHERE investigation_id=?', (iid,)
    ).fetchone()
    assert row is not None, 'Expected a completed fixture result'
    return dict(result_json=row[0], result_hash=row[1], utf8_hex=row[0].encode('utf-8').hex())


def main():
    database = Path(sys.argv[1]).resolve()
    owned_root = Path(__file__).resolve().parents[3] / '.runtime' / 'e2e'
    assert database.is_relative_to(owned_root) and database.name == 'fresh.sqlite'
    assert database.is_file(), 'Only an existing test-owned database may be used'
    mode, *ids = sys.argv[2:]
    if mode == 'inspect':
        with sqlite3.connect(database.as_uri() + '?mode=ro', uri=True) as con:
            return {iid: stored(con, iid) for iid in ids}
    assert mode == 'seed' and len(ids) == 1
    original_id = ids[0]
    with Database(database) as db:
        with db.connection() as con:
            original = stored(con, original_id)
            current = json.loads(original['result_json'])
            did, cid = con.execute(
                'SELECT demonstration_id,case_id FROM investigation_results WHERE investigation_id=?', (original_id,)
            ).fetchone()
            revision = con.execute('SELECT case_revision FROM cases WHERE id=?', (cid,)).fetchone()[0]
        started = start_investigation(db, did, cid, dict(
            schema_version='1', operation_id=str(uuid4()), expected_case_revision=revision, retry_of=None
        ))
        iid = started['investigation_id']
        try:
            legacy = deepcopy(current)
            for field in ('findings_version', 'commitment_issues', 'evidence_observations'):
                del legacy[field]
            for issue in legacy['financial_facts']['issues']:
                issue.pop('source_versions', None)
            assert legacy['financial_facts']['issues'], 'Fixture must cover legacy financial source references'
            legacy.update(investigation_id=iid, snapshot_id=started['snapshot_id'])
            with db.transaction() as con:
                legacy['snapshot_hash'] = con.execute(
                    'SELECT hash FROM evidence_snapshots WHERE id=?', (started['snapshot_id'],)
                ).fetchone()[0]
                # Independent literal canonicalization: expected bytes/hash precede INSERT and any GET.
                canonical = lambda value: json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
                legacy['result_hash'] = sha256(canonical({
                    key: value for key, value in legacy.items() if key != 'result_hash'
                }).encode('utf-8')).hexdigest()
                payload = canonical(legacy)
                con.execute('UPDATE investigations SET status=?,terminal_at=? WHERE id=?',
                            (legacy['status'], datetime.now(timezone.utc).isoformat(), iid))
                con.execute('INSERT INTO investigation_results VALUES (?,?,?,?,?,?,?,?)',
                            (iid, did, cid, legacy['action'], legacy['review_at'], payload, legacy['result_hash'], 'rules-1'))
                con.execute('UPDATE cases SET latest_completed_investigation_id=? WHERE id=?', (iid, cid))
                assert stored(con, original_id) == original
            return dict(investigation_id=iid, original=original, legacy=dict(
                result_json=payload, result_hash=legacy['result_hash'], utf8_hex=payload.encode('utf-8').hex()
            ))
        finally:
            db.capacity.release(iid)
            db.reservations.discard(iid)


if __name__ == '__main__':
    print(json.dumps(main()))
