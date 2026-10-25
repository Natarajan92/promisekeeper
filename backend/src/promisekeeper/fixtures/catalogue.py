"""Approved fixture materialization. No arbitrary paths, records, dates or writes."""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from importlib.resources import files
import json
from types import MappingProxyType
from typing import Mapping
from uuid import UUID, uuid4, uuid5

from promisekeeper.contracts.evidence import EvidenceInput, InvoiceInput, PaymentInput
from promisekeeper.domain.dates import advance_reference
from promisekeeper.domain.evidence import (
    Attribution, Availability, CaseEvidence, ClaimCandidate, CommitmentAnchor,
    CommitmentCandidate, Extraction, Invoice, Message, Payment, commitment_id,
)

CASE_IDS = ("PK-001", "PK-002", "PK-003", "PK-004", "PK-005", "PK-006")


@dataclass(frozen=True, slots=True)
class FixtureCase:
    evidence: CaseEvidence
    extraction: Extraction
    expected: Mapping


@dataclass(frozen=True, slots=True)
class DemonstrationFixture:
    id: UUID
    variant_id: str | None
    catalogue_version: str
    evaluation_at: datetime
    cases: Mapping[str, FixtureCase]
    applied_events: tuple[str, ...]
    _records_json: str = field(repr=False)


def _read(name):
    data = json.loads(files(__package__).joinpath(name).read_text(encoding="utf-8"))
    if data.get("schema_version") != "1":
        raise ValueError("Unsupported catalogue schema")
    return data


def _definitions():
    items = _read("financial_variants.json")["variants"] + _read("workflow_variants.json")["variants"]
    result = {item["id"]: item for item in items}
    if len(result) != len(items):
        raise ValueError("Duplicate catalogue variant")
    return result


def variant_ids():
    return tuple(sorted(_definitions()))


def variant_definition(variant_id):
    try:
        return deepcopy(_definitions()[variant_id])
    except (KeyError, TypeError):
        raise ValueError("Variant is not registered") from None


def _event_table(variant_id):
    events = _read("baseline.json")["events"]
    if variant_id is not None:
        events += variant_definition(variant_id)["events"]
    return {event["id"]: event for event in events}


def _materialize(copy_id, case):
    cid = case["id"]
    case_id = uuid5(copy_id, cid)
    records = case["sources"]
    if len({record["source_id"] for record in records}) != len(records):
        raise ValueError("Duplicate source identifier")
    versions = {record["source_id"]: uuid5(copy_id, f"{cid}:{record['source_id']}:v{record['version']}")
                for record in records}
    sources = {}
    inputs = {}
    for record in records:
        sid = record["source_id"]
        if not sid.startswith(cid + "-"):
            raise ValueError("Source ownership mismatch")
        payload = {key: record[key] for key in (
            "source_id", "kind", "original_content", "event_at", "arrived_at", "availability", "authoritative", "version")}
        payload.update(schema_version="1", id=str(versions[sid]), demonstration_id=str(copy_id), case_id=str(case_id),
                       supersedes_version_id=str(versions[record["supersedes_source_id"]]) if record.get("supersedes_source_id") else None)
        model = EvidenceInput.model_validate_json(json.dumps(payload))
        inputs[sid] = payload
        sources[sid] = model.to_domain()
    invoices, payments, messages, anchors, attributions, commitments, claims = [], [], [], [], [], [], []
    for record in records:
        sid = record["source_id"]
        source = sources[sid]
        data = deepcopy(record["data"])
        if record["kind"] == "INVOICE":
            validated = InvoiceInput.model_validate_json(json.dumps(dict(source=inputs[sid], **data)))
            invoices.append(Invoice(source=source, **validated.model_dump(exclude={"source"})))
        elif record["kind"] in {"LEDGER", "REVERSAL"}:
            for key, target in [("reverses_source_id", "reverses_payment_version_id"),
                                ("suspected_duplicate_source_id", "suspected_duplicate_of")]:
                if key in data:
                    data[target] = str(versions[data.pop(key)])
            validated = PaymentInput.model_validate_json(json.dumps(dict(source=inputs[sid], **data)))
            payments.append(Payment(source=source, **validated.model_dump(exclude={"source"})))
        elif record["kind"] == "MESSAGE":
            if set(data) != {"speaker", "candidate"}:
                raise ValueError("Unsupported message fields")
            messages.append(Message(source, data["speaker"]))
            candidate = data["candidate"]
            clause = candidate["clause"]
            if not isinstance(clause, str) or not clause or source.original_content.count(clause) != 1:
                raise ValueError("Candidate requires one exact source clause")
            start = source.original_content.index(clause)
            common = dict(source=source, start=start, end=start+len(clause), quote=clause, speaker=data["speaker"],
                          amount_text=candidate["amount_text"], currency_text=candidate["currency_text"])
            if candidate["kind"] == "COMMITMENT":
                key = candidate["commitment_key"]
                anchors.append(CommitmentAnchor(commitment_id(copy_id, source.id, key), copy_id, case_id,
                                                source.id, key, start, start+len(clause)))
                commitments.append(CommitmentCandidate(**common, commitment_key=key, date_text=candidate["date_text"],
                                                       explicitly_replaces_source_id=candidate.get("explicitly_replaces_source_id")))
            elif candidate["kind"] == "CLAIM":
                claims.append(ClaimCandidate(**common, payment_date_text=candidate["payment_date_text"],
                                              transaction_reference_text=candidate["transaction_reference_text"]))
            else:
                raise ValueError("Unsupported candidate kind")
    for record in records:
        if record["kind"] != "ATTRIBUTION":
            continue
        data = record["data"]
        target_version = versions[data["commitment_source_id"]]
        target = next((a for a in anchors if a.evidence_version_id == target_version and a.commitment_key == data["commitment_key"]), None)
        if target is None:
            raise ValueError("Attribution target is not an approved source-version anchor")
        attributions.append(Attribution(sources[record["source_id"]], versions[data["payment_source_id"]], target.id,
                                        data["attributed_amount_text"], data["currency_text"]))
    evidence = CaseEvidence(copy_id, case_id, cid, case["client"], case["invoice_id"], tuple(invoices), tuple(payments),
                            tuple(messages), tuple(anchors), tuple(attributions),
                            Availability(case["ledger_availability"]), case["ledger_complete"])
    return FixtureCase(evidence, Extraction(tuple(commitments), tuple(claims)), MappingProxyType(case["expected"]))


def _build(copy_id, variant_id, version, evaluation_at, raw_cases, events):
    for case in raw_cases.values():
        for source in case["sources"]:
            if datetime.fromisoformat(source["arrived_at"]) > evaluation_at:
                raise ValueError("A fixture source has not arrived at evaluation time")
    cases = MappingProxyType({cid: _materialize(copy_id, case) for cid, case in raw_cases.items()})
    return DemonstrationFixture(copy_id, variant_id, version, evaluation_at, cases, tuple(events), json.dumps(raw_cases))


def fresh_copy(variant_id=None):
    baseline = _read("baseline.json")
    definitions = variant_definition(variant_id) if variant_id is not None else None
    raw_cases = {case["id"]: case for case in baseline["cases"]}
    if set(raw_cases) != set(CASE_IDS):
        raise ValueError("Catalogue must seed exactly the registered cases")
    evaluation_at = datetime.fromisoformat(baseline["reference_at"])
    applied = []
    if definitions:
        events = {event["id"]: event for event in baseline["events"]}
        for event_id in definitions["base_events"]:
            event = events[event_id]
            raw_cases[event["case_id"]]["sources"].extend(deepcopy(event["append"]))
            evaluation_at = max(evaluation_at, datetime.fromisoformat(event["evaluation_at"]))
            raw_cases[event["case_id"]]["expected"] = event["expected"]
            applied.append(event_id)
        case = raw_cases[definitions["case_id"]]
        for change in definitions["changes"]:
            if change["op"] == "APPEND":
                case["sources"].append(deepcopy(change["source"]))
            elif change["op"] == "CASE":
                if not set(change["fields"]) <= {"ledger_availability", "ledger_complete"}:
                    raise ValueError("Unsupported case change")
                case.update(change["fields"])
            elif change["op"] in {"REPLACE", "PATCH"}:
                sid = change["source"]["source_id"] if change["op"] == "REPLACE" else change["source_id"]
                index = next(i for i, source in enumerate(case["sources"]) if source["source_id"] == sid)
                if change["op"] == "REPLACE":
                    case["sources"][index] = deepcopy(change["source"])
                else:
                    case["sources"][index].update(change["fields"])
            else:
                raise ValueError("Unsupported catalogue change")
        case["expected"] = definitions["expected"]
    return _build(uuid4(), variant_id, baseline["catalogue_version"], evaluation_at, raw_cases, applied)


def apply_event(demo, event_id):
    table = _event_table(demo.variant_id)
    if event_id not in table:
        raise ValueError("Event is not registered for this variant")
    if event_id in demo.applied_events:
        return demo
    event = table[event_id]
    target_at = datetime.fromisoformat(event["evaluation_at"])
    now = advance_reference(demo.evaluation_at, target_at) if event["kind"] == "CLOCK" else max(demo.evaluation_at, target_at)
    raw = json.loads(demo._records_json)
    case = raw[event["case_id"]]
    case["sources"].extend(deepcopy(event["append"]))
    # Expectations are declared only for registered journeys, never domain inputs.
    if demo.variant_id is None or event_id in {e["id"] for e in variant_definition(demo.variant_id)["events"]}:
        case["expected"] = event["expected"]
    else:
        case["expected"] = {}
    return _build(demo.id, demo.variant_id, demo.catalogue_version, now, raw, (*demo.applied_events, event_id))
