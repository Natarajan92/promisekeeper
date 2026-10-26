"""Immutable evidence values. No framework, database, UI, or provider imports."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid5


class Availability(StrEnum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    MISSING = "MISSING"
    UNREADABLE = "UNREADABLE"


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    UNKNOWN = "UNKNOWN"


class SourceKind(StrEnum):
    INVOICE = "INVOICE"
    LEDGER = "LEDGER"
    MESSAGE = "MESSAGE"
    REVERSAL = "REVERSAL"
    ATTRIBUTION = "ATTRIBUTION"


def commitment_id(demonstration_id, evidence_version_id, commitment_key):
    if not isinstance(demonstration_id, UUID) or not isinstance(evidence_version_id, UUID) or not commitment_key:
        raise ValueError("Invalid commitment identity")
    return uuid5(demonstration_id, f"{evidence_version_id}:{commitment_key}")


def require_same_case(left, right):
    left, right = getattr(left, "source", left), getattr(right, "source", right)
    if (left.demonstration_id, left.case_id) != (right.demonstration_id, right.case_id):
        raise ValueError("Evidence ownership mismatch")


@dataclass(frozen=True, slots=True)
class Evidence:
    id: UUID
    demonstration_id: UUID
    case_id: UUID
    source_id: str
    kind: SourceKind
    original_content: str
    event_at: datetime | None
    arrived_at: datetime
    availability: Availability
    authoritative: bool
    version: int = 1
    supersedes_version_id: UUID | None = None


@dataclass(frozen=True, slots=True)
class Invoice:
    source: Evidence
    invoice_id: str
    client: str
    amount_text: str | None
    currency_text: str | None
    due_text: str | None


@dataclass(frozen=True, slots=True)
class Payment:
    source: Evidence
    transaction_ref: str | None
    amount_text: str | None
    currency_text: str | None
    invoice_id: str | None
    verification_status: VerificationStatus
    settled: bool
    reverses_payment_version_id: UUID | None = None
    suspected_duplicate_of: UUID | None = None
    original_transaction_ref: str | None = None


@dataclass(frozen=True, slots=True)
class Message:
    source: Evidence
    speaker: str | None


@dataclass(frozen=True, slots=True)
class CommitmentAnchor:
    id: UUID
    demonstration_id: UUID
    case_id: UUID
    evidence_version_id: UUID
    commitment_key: str
    clause_start: int
    clause_end: int


@dataclass(frozen=True, slots=True)
class Attribution:
    source: Evidence
    payment_version_id: UUID
    commitment_stable_id: UUID
    attributed_amount_text: str | None
    currency_text: str | None


@dataclass(frozen=True, slots=True)
class CommitmentCandidate:
    source: Evidence
    start: int
    end: int
    quote: str
    commitment_key: str | None
    speaker: str | None
    amount_text: str | None
    currency_text: str | None
    date_text: str | None
    explicitly_replaces_source_id: str | None = None


@dataclass(frozen=True, slots=True)
class ClaimCandidate:
    source: Evidence
    start: int
    end: int
    quote: str
    speaker: str | None
    amount_text: str | None
    currency_text: str | None
    payment_date_text: str | None
    transaction_reference_text: str | None


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    demonstration_id: UUID
    case_id: UUID
    catalogue_case_id: str
    client: str
    invoice_id: str
    invoices: tuple[Invoice, ...]
    payments: tuple[Payment, ...]
    messages: tuple[Message, ...]
    anchors: tuple[CommitmentAnchor, ...]
    attributions: tuple[Attribution, ...]
    ledger_availability: Availability = Availability.AVAILABLE
    ledger_complete: bool = True


@dataclass(frozen=True, slots=True)
class Extraction:
    commitments: tuple[CommitmentCandidate, ...] = ()
    claims: tuple[ClaimCandidate, ...] = ()


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    sources: tuple[str, ...]
    detail: str
