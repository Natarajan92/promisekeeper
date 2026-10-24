"""Saved-copy and case inspection contracts; no browser-derived financial facts."""

from typing import Annotated, Literal

from pydantic import Field, field_validator

from promisekeeper.contracts.common import Command, Id, Instant, Revision
from promisekeeper.contracts.evidence import StrictInput


class CreateDemonstration(Command):
    catalogue_version: str
    variant_id: str | None
    clock_mode: Literal["REFERENCE", "REAL"]


class DeleteDemonstration(Command):
    confirmed_demonstration_id: Id
    confirm: Literal[True]

    @field_validator("confirm", mode="before")
    @classmethod
    def explicit_true(cls, value):
        if value is not True:
            raise ValueError("Explicit boolean confirmation required")
        return value


class DemonstrationSummary(StrictInput):
    id: Id
    catalogue_version: str
    created_at: Instant
    clock_mode: Literal["REFERENCE", "REAL"]
    selected_variant_id: str | None


class DemonstrationList(StrictInput):
    schema_version: Literal["1"]
    demonstrations: list[DemonstrationSummary]


class AnchorView(StrictInput):
    id: Id
    evidence_version_id: Id
    commitment_key: str
    clause_start: Revision
    clause_end: Revision


class InvoiceData(StrictInput):
    invoice_id: str
    client: str
    amount_text: str | None
    currency_text: str | None
    due_text: str | None


class PaymentData(StrictInput):
    transaction_ref: str | None
    amount_text: str | None
    currency_text: str | None
    invoice_id: str | None
    verification_status: Literal["VERIFIED", "UNVERIFIED", "UNKNOWN"]
    settled: bool
    reverses_source_id: str | None = None
    suspected_duplicate_source_id: str | None = None


class MessageData(StrictInput):
    speaker: str | None


class AttributionData(StrictInput):
    payment_source_id: str
    commitment_source_id: str
    commitment_key: str
    attributed_amount_text: str | None
    currency_text: str | None


class EvidenceView(StrictInput):
    schema_version: Literal["1"]
    id: Id
    demonstration_id: Id
    case_id: Id
    stable_source_id: str
    version: Annotated[int, Field(ge=1)]
    kind: Literal["INVOICE", "LEDGER", "MESSAGE", "REVERSAL", "ATTRIBUTION"]
    original_content: Annotated[str, Field(max_length=8000)]
    event_at: Instant | None
    arrived_at: Instant
    availability: Literal["AVAILABLE", "UNAVAILABLE", "MISSING", "UNREADABLE"]
    authoritative: bool
    supersedes_version_id: Id | None
    data: InvoiceData | PaymentData | MessageData | AttributionData
    commitment_anchors: list[AnchorView]


class MoneyView(StrictInput):
    currency: Literal["INR"] = "INR"
    minor_units: Annotated[str, Field(pattern=r"^-?(0|[1-9][0-9]*)$")]


class FinancialIssue(StrictInput):
    code: str
    sources: list[str]
    detail: str


class FinancialView(StrictInput):
    certainty: Literal["KNOWN", "UNKNOWN"]
    invoice: MoneyView | None
    paid: MoneyView | None
    balance: MoneyView | None
    due_at: Instant | None
    issues: list[FinancialIssue]


class CommandEligibility(StrictInput):
    allowed: bool
    blocking_reasons: list[str]


class CaseSummary(StrictInput):
    id: Id
    catalogue_case_id: Literal["PK-001", "PK-002", "PK-003"]
    client: str
    invoice_id: str
    currency: str | None
    due_at: Instant | None
    lifecycle: Literal["OPEN", "CLOSED"]
    case_revision: Revision
    has_previous_investigation: bool
    review_required: bool


class CaseList(StrictInput):
    schema_version: Literal["1"]
    demonstration_id: Id
    clock_mode: Literal["REFERENCE", "REAL"]
    evaluation_at: Instant
    cases: list[CaseSummary]


class CaseView(StrictInput):
    schema_version: Literal["1"]
    id: Id
    demonstration_id: Id
    catalogue_case_id: str
    client: str
    invoice_id: str
    lifecycle: Literal["OPEN", "CLOSED"]
    case_revision: Revision
    evidence_revision: Revision
    review_epoch: Revision
    current_draft_version_id: Id | None
    clock_mode: Literal["REFERENCE", "REAL"]
    evaluation_at: Instant
    ledger_availability: Literal["AVAILABLE", "UNAVAILABLE", "MISSING", "UNREADABLE"]
    ledger_complete: bool
    evidence: list[EvidenceView]
    financial_facts: FinancialView
    latest_completed_result: dict | None
    current_result: dict | None
    running_attempt: Id | None
    draft_state: Literal["NOT_IMPLEMENTED"]
    review_state: Literal["NOT_IMPLEMENTED"]
    draft_generation_state: Literal["NOT_IMPLEMENTED"]
    freshness: Literal["CURRENT", "EVIDENCE_CHANGED", "TIME_EXPIRED", "SUPERSEDED", "INCOMPLETE"]
    review_required: bool
    review_required_reasons: list[str]
    allowed_commands: dict[str, CommandEligibility]


class HistoryEvent(StrictInput):
    id: Id
    demonstration_id: Id
    case_id: Id
    sequence: Annotated[int, Field(ge=1)]
    event_type: str
    operation_id: Id | None
    payload: dict
    occurred_at: Instant


class HistoryView(StrictInput):
    schema_version: Literal["1"]
    events: list[HistoryEvent]
    next_cursor: Revision | None
