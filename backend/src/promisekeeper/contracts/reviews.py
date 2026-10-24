"""Strict exact-payload review and independent draft-generation contracts."""
from typing import Annotated, Literal
from pydantic import Field
from promisekeeper.contracts.common import CaseCommand, Id, Instant, Hash, Revision, Receipt
from promisekeeper.contracts.evidence import StrictInput


class SaveDraft(CaseCommand):
    investigation_id: Id
    parent_version_id: Id
    exact_text: Annotated[str, Field(min_length=1, max_length=8000)]
    recipient: Annotated[str, Field(min_length=1, max_length=200)]


class ReviewDraft(CaseCommand):
    draft_version_id: Id
    payload_hash: Hash
    expected_review_epoch: Revision
    decision: Literal['APPROVE', 'REJECT']


class RetryDraft(CaseCommand):
    investigation_id: Id
    failed_draft_attempt_id: Id
    expected_draft_head: Id | None


class DraftVersion(StrictInput):
    id: Id
    demonstration_id: Id
    case_id: Id
    investigation_id: Id
    parent_version_id: Id | None
    recipient: str
    invoice_id: str
    exact_text: str
    version: Annotated[int, Field(ge=1)]
    payload_hash: Hash
    created_at: Instant
    validation_status: Literal['VALID', 'INVALID']
    validation_reasons: list[str]
    evidence_revision: Revision


class DraftReview(StrictInput):
    id: Id
    demonstration_id: Id
    case_id: Id
    operation_id: Id
    draft_version_id: Id
    owner_actor: str
    decision: Literal['APPROVE', 'REJECT']
    decided_at: Instant
    exact_text: str
    recipient: str
    invoice_id: str
    payload_hash: Hash
    investigation_id: Id
    evidence_revision: Revision
    review_epoch: Revision


class DraftGenerationAttempt(StrictInput):
    id: Id
    demonstration_id: Id
    case_id: Id
    investigation_id: Id
    operation_id: Id
    retry_of: Id | None
    expected_draft_head: Id | None
    status: Literal['RUNNING', 'READY', 'FAILED']
    started_at: Instant
    deadline_at: Instant
    terminal_at: Instant | None
    failure_code: str | None
    draft_version_id: Id | None


class DraftAttemptView(DraftGenerationAttempt):
    schema_version: Literal['1']


class DraftSaved(StrictInput):
    schema_version: Literal['1']
    receipt: Receipt
    draft_version: DraftVersion


class DraftReviewed(StrictInput):
    schema_version: Literal['1']
    receipt: Receipt
    draft_review: DraftReview


class DraftRetryStarted(StrictInput):
    schema_version: Literal['1']
    receipt: Receipt
    draft_attempt_id: Id


class DeletedDraftOperation(StrictInput):
    schema_version: Literal['1']
    demonstration_id: Id
    receipt: Receipt
