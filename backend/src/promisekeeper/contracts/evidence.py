"""Evidence boundary; strictness is specified by contract tests."""

from datetime import datetime
from uuid import UUID
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from promisekeeper.domain.evidence import Availability, Evidence, SourceKind, VerificationStatus


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class EvidenceInput(StrictInput):
    schema_version: Literal["1"] = "1"
    id: UUID
    demonstration_id: UUID
    case_id: UUID
    source_id: str = Field(min_length=1, max_length=160)
    kind: SourceKind
    original_content: str = Field(max_length=8000)
    event_at: datetime | None
    arrived_at: datetime
    availability: Availability
    authoritative: bool
    version: int = Field(default=1, ge=1)
    supersedes_version_id: UUID | None = None

    @field_validator("event_at", "arrived_at")
    @classmethod
    def aware_instant(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Source instants require an explicit timezone")
        return value

    def to_domain(self) -> Evidence:
        return Evidence(**self.model_dump(exclude={"schema_version"}))


class InvoiceInput(StrictInput):
    source: EvidenceInput
    invoice_id: str
    client: str
    amount_text: str | None
    currency_text: str | None
    due_text: str | None


class PaymentInput(StrictInput):
    source: EvidenceInput
    transaction_ref: str | None
    amount_text: str | None
    currency_text: str | None
    invoice_id: str | None
    verification_status: VerificationStatus
    settled: bool
    reverses_payment_version_id: UUID | None = None
    suspected_duplicate_of: UUID | None = None
