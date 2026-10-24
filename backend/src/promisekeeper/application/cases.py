"""Explicit new-copy creation and read-only discovery; never seed on a read."""

import json
from datetime import datetime

from promisekeeper.application.operations import CommandError, canonical, instant, replay, save_receipt, utcnow
from promisekeeper.fixtures.catalogue import fresh_copy
from promisekeeper.domain.payments import reconcile_payments
from promisekeeper.domain.dates import deadline
from promisekeeper.persistence.repositories import (
    append_event, append_evidence, case, demonstration, evaluation_at, load_fixture, source_view,
)


def create_demonstration(db, request):
    with db.transaction() as con:
        previous = replay(con, None, "CREATE_DEMONSTRATION", "new-demonstration", request)
        if previous:
            return previous
        if request["catalogue_version"] != "release-0.1" or request["clock_mode"] not in {"REFERENCE", "REAL"}:
            raise CommandError("UNAPPROVED_CATALOGUE_ENTRY", 422)
        try:
            fixture = fresh_copy(request["variant_id"])
        except ValueError:
            raise CommandError("UNAPPROVED_CATALOGUE_ENTRY", 422) from None
        did = str(fixture.id)
        con.execute("""INSERT INTO demonstrations
            (id,catalogue_version,created_at,clock_mode,reference_at,selected_variant_id,applied_events_json)
            VALUES (?,?,?,?,?,?,?)""", (did, fixture.catalogue_version, instant(utcnow()), request["clock_mode"],
                                       instant(fixture.evaluation_at), fixture.variant_id, canonical(fixture.applied_events)))
        for item in fixture.cases.values():
            evidence = item.evidence
            con.execute("""INSERT INTO cases
                (id,demonstration_id,catalogue_case_id,client,invoice_id,ledger_availability,ledger_complete)
                VALUES (?,?,?,?,?,?,?)""", (str(evidence.case_id), did, evidence.catalogue_case_id,
                                           evidence.client, evidence.invoice_id, evidence.ledger_availability, int(evidence.ledger_complete)))
        append_evidence(con, fixture)
        for item in fixture.cases.values():
            append_event(con, dict(id=str(item.evidence.case_id), demonstration_id=did), "COPY_CREATED", request["operation_id"])
        return save_receipt(con, did, "CREATE_DEMONSTRATION", did, request, "CREATED",
                            hash_target="new-demonstration", demonstration_id=did)


def list_demonstrations(db):
    with db.connection() as con:
        rows = con.execute("""SELECT id,catalogue_version,created_at,clock_mode,selected_variant_id
                              FROM demonstrations WHERE deleted=0 ORDER BY created_at,id""").fetchall()
        return dict(schema_version="1", demonstrations=[dict(r) for r in rows])


def delete_demonstration(db, did, request):
    with db.transaction() as con:
        previous = replay(con, did, "DELETE_DEMONSTRATION", did, request)
        if previous:
            return previous
        demonstration(con, did)
        if request["confirmed_demonstration_id"] != did or request["confirm"] is not True:
            raise CommandError("INVALID_REQUEST", 422)
        if con.execute("SELECT 1 FROM investigations WHERE demonstration_id=? AND status='RUNNING'", (did,)).fetchone():
            raise CommandError("INVESTIGATION_RUNNING")
        con.execute("UPDATE demonstrations SET deleted=1 WHERE id=?", (did,))
        con.execute("DELETE FROM cases WHERE demonstration_id=?", (did,))
        con.execute("DELETE FROM agent_activity WHERE demonstration_id=?", (did,))
        con.execute("DELETE FROM morning_reviews WHERE demonstration_id=?", (did,))
        con.execute("DELETE FROM client_memory WHERE demonstration_id=?", (did,))
        con.execute("""INSERT INTO operation_tombstones
            SELECT operation_id,demonstration_id,operation_type,canonical_request_hash,committed_at
            FROM operation_receipts WHERE demonstration_id=?""", (did,))
        con.execute("DELETE FROM operation_receipts WHERE demonstration_id=?", (did,))
        # Retain only a content-free tombstone. Original variant/time metadata is purged.
        con.execute("""UPDATE demonstrations SET catalogue_version='',reference_at='',reference_clock_event_id=NULL,
                       selected_variant_id=NULL,applied_events_json='[]' WHERE id=?""", (did,))
        return save_receipt(con, did, "DELETE_DEMONSTRATION", did, request, "DELETED", demonstration_id=did)


def _case_view(con, did, cid, fixture, demo, *, include_reviews=True):
    row = case(con, did, cid)
    evidence = fixture.cases[row["catalogue_case_id"]].evidence
    facts = reconcile_payments(evidence)
    sources = [source_view(con, r) for r in con.execute(
        "SELECT * FROM evidence_versions WHERE demonstration_id=? AND case_id=? ORDER BY stable_source_id,version,id", (did, cid))]
    running = con.execute("SELECT id FROM investigations WHERE case_id=? AND status='RUNNING'", (cid,)).fetchone()
    latest = con.execute("""SELECT r.result_json,r.review_at,i.id,s.evidence_revision FROM investigation_results r
        JOIN investigations i ON i.id=r.investigation_id JOIN evidence_snapshots s ON s.id=i.snapshot_id
        WHERE i.id=? AND i.case_id=?""", (row["latest_completed_investigation_id"], cid)).fetchone()
    freshness = "INCOMPLETE"
    completed = current = None
    reasons = []
    if latest:
        completed = json.loads(latest["result_json"])
        freshness = "CURRENT"
        if latest["evidence_revision"] != row["evidence_revision"]:
            freshness = "EVIDENCE_CHANGED"
        elif latest["review_at"] and evaluation_at(demo) >= datetime.fromisoformat(latest["review_at"]):
            freshness = "TIME_EXPIRED"
        if freshness == "CURRENT":
            current = completed
        else:
            reasons.append(freshness)
    if running:
        reasons.append("INVESTIGATION_RUNNING")
    if row["lifecycle"] == "CLOSED" and not latest and row["evidence_revision"]:
        reasons.append("EVIDENCE_CHANGED")
    def money(value):
        return dict(currency="INR", minor_units=str(value)) if value is not None else None
    allowed = {name: dict(allowed=False, blocking_reasons=["GATE_NOT_IMPLEMENTED"]) for name in
               ("start_investigation", "edit_draft", "approve_draft", "reject_draft", "close", "reopen")}
    allowed["confirm_scenario_event"] = dict(allowed=True, blocking_reasons=[])
    start_blocks = (["CASE_CLOSED"] if row["lifecycle"] != "OPEN" else []) + (["INVESTIGATION_RUNNING"] if running else [])
    allowed["start_investigation"] = dict(allowed=not start_blocks, blocking_reasons=start_blocks)
    view = dict(schema_version="1", **{k: row[k] for k in (
        "id", "demonstration_id", "catalogue_case_id", "client", "invoice_id", "lifecycle", "case_revision",
        "evidence_revision", "review_epoch", "current_draft_version_id", "ledger_availability")},
        ledger_complete=bool(row["ledger_complete"]), clock_mode=demo["clock_mode"], evaluation_at=instant(evaluation_at(demo)),
        evidence=sources, financial_facts=dict(certainty="KNOWN" if facts.balance_minor is not None else "UNKNOWN",
            invoice=money(facts.invoice_minor), paid=money(facts.paid_minor), balance=money(facts.balance_minor),
            due_at=instant(facts.due_at) if facts.due_at else None,
            issues=[dict(code=i.code, sources=list(i.sources), detail=i.detail) for i in facts.issues]),
        latest_completed_result=completed, current_result=current, running_attempt=running["id"] if running else None,
        draft_state="NOT_IMPLEMENTED", review_state="NOT_IMPLEMENTED", draft_generation_state="NOT_IMPLEMENTED",
        freshness=freshness, review_required=bool(reasons), review_required_reasons=reasons, allowed_commands=allowed)
    if include_reviews:
        from promisekeeper.application.lifecycle import lifecycle_projection
        view = lifecycle_projection(con, row, view)
        from promisekeeper.application.reviews import review_projection
        return review_projection(con,row,view)
    return view


def get_case(db, did, cid):
    with db.connection() as con:
        # Keep all reads in one SQLite snapshot; the returned evidence packet is independent.
        con.execute("BEGIN")
        case(con, did, cid)
        return _case_view(con, did, cid, load_fixture(con, did), demonstration(con, did))


def list_cases(db, did):
    with db.connection() as con:
        con.execute("BEGIN")
        demo = demonstration(con, did)
        fixture = load_fixture(con, did)
        summaries = []
        for row in con.execute("SELECT * FROM cases WHERE demonstration_id=? ORDER BY catalogue_case_id", (did,)).fetchall():
            view = _case_view(con, did, row["id"], fixture, demo)
            invoices=fixture.cases[row['catalogue_case_id']].evidence.invoices
            superseded={i.source.supersedes_version_id for i in invoices if i.source.supersedes_version_id}
            due_texts={i.due_text for i in invoices if i.source.authoritative and i.source.availability=='AVAILABLE' and i.source.id not in superseded
                       and view['financial_facts']['due_at'] and deadline(i.due_text,original_at=i.source.event_at).expires_at==datetime.fromisoformat(view['financial_facts']['due_at'])}
            current = view['current_result'] if not view['running_attempt'] else None
            balance = view['financial_facts']['balance']
            balance_label = ('UNKNOWN_REMAINDER' if balance is None else
                             current['financial_label'] if current else 'RECORDED_REMAINDER')
            summaries.append({k: view[k] for k in ("id", "catalogue_case_id", "client", "invoice_id", "lifecycle", "case_revision", "review_required")}
                             | dict(currency="INR" if view["financial_facts"]["invoice"] else None,
                                    due_at=view["financial_facts"]["due_at"],
                                    due_text=next(iter(due_texts)) if len(due_texts)==1 else None,
                                    balance=balance, balance_label=balance_label,
                                    recommended_action=current['action'] if current else None,
                                    review_at=current['review_at'] if current else None,
                                    has_previous_investigation=bool(con.execute("SELECT 1 FROM investigations WHERE case_id=?", (row["id"],)).fetchone())))
        return dict(schema_version="1", demonstration_id=did, clock_mode=demo["clock_mode"], evaluation_at=instant(evaluation_at(demo)), cases=summaries)


def get_evidence(db, did, eid):
    with db.connection() as con:
        con.execute("BEGIN")
        demonstration(con, did)
        row = con.execute("SELECT * FROM evidence_versions WHERE demonstration_id=? AND id=?", (did, eid)).fetchone()
        if row is None:
            raise CommandError("NOT_FOUND", 404)
        return source_view(con, row)
