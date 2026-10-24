"""Read-only preview and atomic exact-payload confirmation share one implementation."""

from datetime import datetime
import json

from promisekeeper.application.operations import CommandError, canonical, digest, instant, replay, save_receipt
from promisekeeper.fixtures.catalogue import _event_table, apply_event, variant_ids
from promisekeeper.persistence.repositories import append_event, append_evidence, case, demonstration, load_fixture, require_revision


def catalogue_view():
    events = {}
    for variant in (None, *variant_ids()):
        events.update(_event_table(variant))
    return dict(schema_version="1", catalogue_version="release-0.1", baseline_case_ids=["PK-001", "PK-002", "PK-003"],
                variant_ids=list(variant_ids()), events=[dict(id=e["id"], kind=e["kind"], case_id=e["case_id"],
                    evaluation_at=instant(datetime.fromisoformat(e["evaluation_at"]))) for _, e in sorted(events.items())])


def _preview(con, did, cid, event_id):
    row = case(con, did, cid)
    demo = demonstration(con, did)
    event = _event_table(demo["selected_variant_id"]).get(event_id)
    if event is None or event["case_id"] != row["catalogue_case_id"]:
        raise CommandError("UNAPPROVED_CATALOGUE_ENTRY", 422)
    if event_id in json.loads(demo["applied_events_json"]):
        raise CommandError("PREVIEW_CHANGED")
    if event["kind"] == "CLOCK" and demo["clock_mode"] == "REAL":
        raise CommandError("UNAPPROVED_CATALOGUE_ENTRY", 422)
    before = load_fixture(con, did)
    try:
        after = apply_event(before, event_id)
    except ValueError:
        raise CommandError("PREVIEW_CHANGED") from None
    evidence = after.cases[row["catalogue_case_id"]].evidence
    additions = {record["source_id"]: record for record in event["append"]}
    changes = []
    for record in (*evidence.invoices, *evidence.payments, *evidence.messages, *evidence.attributions):
        source = record.source
        if source.source_id not in additions:
            continue
        changes.append(dict(schema_version="1", id=str(source.id), demonstration_id=did, case_id=cid,
                            stable_source_id=source.source_id, version=source.version, kind=source.kind,
                            original_content=source.original_content, event_at=instant(source.event_at) if source.event_at else None,
                            arrived_at=instant(source.arrived_at), availability=source.availability, authoritative=source.authoritative,
                            supersedes_version_id=str(source.supersedes_version_id) if source.supersedes_version_id else None,
                            data={k: v for k, v in additions[source.source_id]["data"].items() if k != "candidate"},
                            commitment_anchors=[dict(id=str(a.id), evidence_version_id=str(a.evidence_version_id), commitment_key=a.commitment_key,
                                                     clause_start=a.clause_start, clause_end=a.clause_end)
                                                for a in evidence.anchors if a.evidence_version_id == source.id]))
    clock_change = None
    if demo["clock_mode"] == "REFERENCE" and before.evaluation_at != after.evaluation_at:
        clock_change = {"from": instant(before.evaluation_at), "to": instant(after.evaluation_at)}
    preview = dict(schema_version="1", catalogue_version=demo["catalogue_version"], demonstration_id=did, case_id=cid,
                   event_id=event_id, expected_case_revision=row["case_revision"], evidence_changes=changes, clock_change=clock_change)
    return preview | {"preview_hash": digest(preview)}, after


def preview_event(db, did, cid, event_id):
    with db.connection() as con:
        con.execute("BEGIN")
        return _preview(con, did, cid, event_id)[0]


def confirm_event(db, did, cid, request):
    with db.transaction() as con:
        previous = replay(con, did, "CONFIRM_SCENARIO_EVENT", cid, request)
        if previous:
            return previous
        row = case(con, did, cid)
        require_revision(row, request)
        preview, fixture = _preview(con, did, cid, request["event_id"])
        if request["catalogue_version"] != preview["catalogue_version"] or request["confirmed_preview_hash"] != preview["preview_hash"]:
            raise CommandError("PREVIEW_CHANGED")
        append_evidence(con, fixture)
        changes = bool(preview["evidence_changes"])
        clock = preview["clock_change"]
        con.execute("""UPDATE demonstrations SET applied_events_json=?,reference_at=?,
                       reference_clock_event_id=CASE WHEN ? THEN ? ELSE reference_clock_event_id END WHERE id=?""",
                    (canonical(fixture.applied_events), instant(fixture.evaluation_at), bool(clock), request["event_id"], did))
        affected = con.execute("SELECT * FROM cases WHERE demonstration_id=? AND (? OR id=?) ORDER BY catalogue_case_id",
                               (did, bool(clock), cid)).fetchall()
        for target in affected:
            evidence_changed = int(changes and target["id"] == cid)
            con.execute("UPDATE cases SET case_revision=case_revision+1,evidence_revision=evidence_revision+?,review_epoch=review_epoch+1 WHERE id=?",
                        (evidence_changed, target["id"]))
            append_event(con, dict(target), "APPROVAL_INVALIDATED", request["operation_id"], {"reason": "SCENARIO_EVENT_CONFIRMED"})
            append_event(con, dict(target), "EVIDENCE_ARRIVED" if evidence_changed else "CLOCK_CHANGED", request["operation_id"],
                         {"event_id": request["event_id"], "preview_hash": preview["preview_hash"], "confirmed_case_id": cid})
        append_event(con, row, "SCENARIO_EVENT_CONFIRMED", request["operation_id"],
                     {"event_id": request["event_id"], "preview_hash": preview["preview_hash"]})
        return save_receipt(con, did, "CONFIRM_SCENARIO_EVENT", cid, request, "APPLIED", revision=row["case_revision"] + 1)
