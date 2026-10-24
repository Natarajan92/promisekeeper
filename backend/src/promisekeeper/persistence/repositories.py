"""Copy-scoped immutable evidence, snapshots, and append-only audit sequences."""

from datetime import datetime
import json
from uuid import UUID, uuid4

from promisekeeper.application.operations import CommandError, canonical, digest, instant, utcnow
from promisekeeper.domain.money import parse_money
from promisekeeper.fixtures.catalogue import _build


def demonstration(con, did):
    row = con.execute("SELECT * FROM demonstrations WHERE id=? AND deleted=0", (did,)).fetchone()
    if row is None:
        raise CommandError("NOT_FOUND", 404)
    return dict(row)


def case(con, did, cid):
    demonstration(con, did)
    row = con.execute("SELECT * FROM cases WHERE demonstration_id=? AND id=?", (did, cid)).fetchone()
    if row is None:
        raise CommandError("NOT_FOUND", 404)
    return dict(row)


def require_revision(row, request):
    if row["case_revision"] != request["expected_case_revision"]:
        raise CommandError("REVISION_CONFLICT", operation_id=request["operation_id"])


def evaluation_at(demo):
    return utcnow() if demo["clock_mode"] == "REAL" else datetime.fromisoformat(demo["reference_at"])


def load_fixture(con, did):
    demo = demonstration(con, did)
    raw = {}
    for row in con.execute("SELECT * FROM cases WHERE demonstration_id=? ORDER BY catalogue_case_id", (did,)):
        records = con.execute("SELECT record_json FROM evidence_versions WHERE case_id=? ORDER BY rowid", (row["id"],)).fetchall()
        raw[row["catalogue_case_id"]] = dict(id=row["catalogue_case_id"], client=row["client"], invoice_id=row["invoice_id"],
                                          ledger_availability=row["ledger_availability"], ledger_complete=bool(row["ledger_complete"]),
                                          sources=[json.loads(r[0]) for r in records], expected={})
    return _build(UUID(did), demo["selected_variant_id"], demo["catalogue_version"], evaluation_at(demo),
                  raw, json.loads(demo["applied_events_json"]))


def append_event(con, row, event_type, operation_id, payload=None):
    seq = con.execute("SELECT next_event_sequence FROM cases WHERE id=?", (row["id"],)).fetchone()[0]
    con.execute("INSERT INTO case_events VALUES (?,?,?,?,?,?,?,?)", (
        str(uuid4()), row["demonstration_id"], row["id"], seq, event_type, operation_id,
        canonical(payload or {}), instant(utcnow())))
    con.execute("UPDATE cases SET next_event_sequence=next_event_sequence+1 WHERE id=?", (row["id"],))


def append_evidence(con, fixture):
    raw = json.loads(fixture._records_json)
    for cid, item in fixture.cases.items():
        ev = item.evidence
        did, case_id = str(ev.demonstration_id), str(ev.case_id)
        sources = {r["source_id"]: r for r in raw[cid]["sources"]}
        records = [*ev.invoices, *ev.payments, *ev.messages, *ev.attributions]
        for record in records:
            s = record.source
            if con.execute("SELECT 1 FROM evidence_versions WHERE id=?", (str(s.id),)).fetchone():
                continue
            con.execute("INSERT INTO evidence_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                str(s.id), did, case_id, s.source_id, s.version, s.kind, s.original_content,
                instant(s.event_at) if s.event_at else None, instant(s.arrived_at), s.availability, int(s.authoritative),
                str(s.supersedes_version_id) if s.supersedes_version_id else None, canonical(sources[s.source_id])))
        for inv in ev.invoices:
            if con.execute("SELECT 1 FROM invoice_projections WHERE evidence_version_id=?", (str(inv.source.id),)).fetchone():
                continue
            money = parse_money(inv.amount_text, inv.currency_text)
            con.execute("INSERT INTO invoice_projections VALUES (?,?,?,?,?,?,?,?,?,?)", (
                str(inv.source.id), did, case_id, inv.invoice_id, inv.client, inv.amount_text,
                inv.currency_text, inv.due_text, str(money.minor_units) if money.minor_units is not None else None, money.error))
        for payment in ev.payments:
            if con.execute("SELECT 1 FROM payment_projections WHERE evidence_version_id=?", (str(payment.source.id),)).fetchone():
                continue
            money = parse_money(payment.amount_text, payment.currency_text)
            con.execute("INSERT INTO payment_projections VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
                str(payment.source.id), did, case_id, payment.transaction_ref, payment.amount_text, payment.currency_text,
                payment.invoice_id, str(money.minor_units) if money.minor_units is not None else None, money.error,
                payment.verification_status, int(payment.settled),
                str(payment.reverses_payment_version_id) if payment.reverses_payment_version_id else None,
                str(payment.suspected_duplicate_of) if payment.suspected_duplicate_of else None))
        for anchor in ev.anchors:
            if not con.execute("SELECT 1 FROM commitment_anchors WHERE id=?", (str(anchor.id),)).fetchone():
                con.execute("INSERT INTO commitment_anchors VALUES (?,?,?,?,?,?,?)", (
                    str(anchor.id), did, case_id, str(anchor.evidence_version_id), anchor.commitment_key,
                    anchor.clause_start, anchor.clause_end))
        for link in ev.attributions:
            if not con.execute("SELECT 1 FROM commitment_attributions WHERE evidence_version_id=?", (str(link.source.id),)).fetchone():
                money = parse_money(link.attributed_amount_text, link.currency_text)
                con.execute("INSERT INTO commitment_attributions VALUES (?,?,?,?,?,?,?,?)", (
                    str(link.source.id), did, case_id, str(link.payment_version_id), str(link.commitment_stable_id),
                    link.attributed_amount_text, link.currency_text, str(money.minor_units) if money.minor_units is not None else None))


def source_view(con, row):
    item = {k: row[k] for k in ("id", "demonstration_id", "case_id", "stable_source_id", "version", "kind",
                               "original_content", "event_at", "arrived_at", "availability", "supersedes_version_id")}
    item["authoritative"] = bool(row["authoritative"])
    item["schema_version"] = "1"
    raw = json.loads(row["record_json"])
    # Catalogue candidate answers are fixture expectations, never public source facts.
    item["data"] = {k: v for k, v in raw["data"].items() if k != "candidate"}
    item["commitment_anchors"] = [dict(a) for a in con.execute(
        "SELECT id,evidence_version_id,commitment_key,clause_start,clause_end FROM commitment_anchors WHERE evidence_version_id=? ORDER BY clause_start", (row["id"],))]
    return item


def capture_snapshot(con, row):
    records = list(con.execute(
        "SELECT * FROM evidence_versions WHERE demonstration_id=? AND case_id=? ORDER BY stable_source_id,version,id",
        (row["demonstration_id"], row["id"])))
    sources = [source_view(con, r) | dict(original_event_at=json.loads(r['record_json'])['event_at']) for r in records]
    packet = dict(schema_version="1", demonstration_id=row["demonstration_id"], case_id=row["id"],
                  evidence_revision=row["evidence_revision"], evidence=sources,
                  ledger_availability=row["ledger_availability"], ledger_complete=bool(row["ledger_complete"]))
    sid = str(uuid4())
    con.execute("INSERT INTO evidence_snapshots VALUES (?,?,?,?,?,?,?)", (
        sid, row["demonstration_id"], row["id"], row["evidence_revision"], instant(utcnow()), canonical(packet), digest(packet)))
    return sid


def history(db, did, cid, cursor=0, limit=50):
    with db.connection() as con:
        case(con, did, cid)
        rows = con.execute("SELECT * FROM case_events WHERE case_id=? AND sequence>? ORDER BY sequence LIMIT ?",
                           (cid, cursor, limit + 1)).fetchall()
        items = [{**dict(r), "payload": json.loads(r["payload_json"])} for r in rows[:limit]]
        for item in items:
            del item["payload_json"]
        return dict(schema_version="1", events=items, next_cursor=items[-1]["sequence"] if len(rows) > limit else None)
