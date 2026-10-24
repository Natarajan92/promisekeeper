"""Canonical command identity and durable responses, committed with each mutation."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from uuid import UUID


class CommandError(Exception):
    def __init__(self, code, status=409, *, operation_id=None):
        super().__init__(code)
        self.code, self.status, self.operation_id = code, status, operation_id


def utcnow():
    return datetime.now(timezone.utc)


def instant(value):
    return value.astimezone(timezone.utc).isoformat()


def json_default(value):
    if isinstance(value, datetime):
        return instant(value)
    if isinstance(value, UUID):
        return str(value)
    raise TypeError(type(value).__name__)


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=json_default)


def digest(value):
    return sha256(canonical(value).encode("utf-8")).hexdigest()


def replay(con, did, operation_type, target, request):
    row = con.execute("SELECT * FROM operation_receipts WHERE operation_id=?", (request["operation_id"],)).fetchone()
    deleted = row is None
    if deleted:
        row = con.execute("SELECT * FROM operation_tombstones WHERE operation_id=?", (request["operation_id"],)).fetchone()
    if row is None:
        return None
    expected = digest(dict(operation_type=operation_type, target=target, request=request))
    if (did is not None and row["demonstration_id"] != did) or row["canonical_request_hash"] != expected:
        raise CommandError("OPERATION_PAYLOAD_MISMATCH", operation_id=request["operation_id"])
    return deleted_response(row) if deleted else json.loads(row["response_json"])


def deleted_response(row):
    return dict(schema_version="1", demonstration_id=row["demonstration_id"], receipt=dict(
        operation_id=row["operation_id"], operation_type=row["operation_type"], target_id=row["demonstration_id"],
        committed_at=row["committed_at"], outcome="DELETED", case_revision=None))


def save_receipt(con, did, operation_type, target, request, outcome, *, hash_target=None, revision=None, **fields):
    committed_at = instant(utcnow())
    receipt = dict(operation_id=request["operation_id"], operation_type=operation_type, target_id=target,
                   committed_at=committed_at, outcome=outcome, case_revision=revision)
    response = dict(schema_version="1", receipt=receipt, **fields)
    con.execute("INSERT INTO operation_receipts VALUES (?,?,?,?,?,?,?)", (
        request["operation_id"], did, operation_type,
        digest(dict(operation_type=operation_type, target=hash_target or target, request=request)),
        target, committed_at, canonical(response)))
    return response


def lookup_receipt(db, demonstration_id, operation_id):
    with db.connection() as con:
        row = con.execute("SELECT response_json FROM operation_receipts WHERE demonstration_id=? AND operation_id=?",
                          (demonstration_id, operation_id)).fetchone()
        if row is None:
            tombstone = con.execute("SELECT * FROM operation_tombstones WHERE demonstration_id=? AND operation_id=?",
                                    (demonstration_id, operation_id)).fetchone()
            if tombstone is None:
                raise CommandError("NOT_RECORDED", 404, operation_id=operation_id)
            return deleted_response(tombstone)
        return json.loads(row["response_json"])
