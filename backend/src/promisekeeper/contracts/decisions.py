"""Immutable owner decisions, explicit lifecycle commands and typed receipts."""
from typing import Annotated, Literal
from pydantic import Field, field_validator
from promisekeeper.contracts.common import CaseCommand, Hash, Id, Instant, Receipt
from promisekeeper.contracts.evidence import StrictInput
from promisekeeper.contracts.reviews import DraftVersion

Reason = Annotated[str, Field(max_length=1000)]


class DispositionCommand(CaseCommand):
    investigation_id: Id
    decision: Literal['ACCEPT', 'REJECT']
    reason: Reason | None = None


class Confirmation(CaseCommand):
    confirm: Literal[True]

    @field_validator('confirm', mode='before')
    @classmethod
    def explicit_true(cls, value):
        if value is not True:
            raise ValueError('Explicit boolean confirmation required')
        return value


class CloseCase(Confirmation):
    investigation_id: Id
    confirmed_result_hash: Hash


class ReopenCase(Confirmation):
    reason: Reason | None = None


class OwnerDisposition(StrictInput):
    id: Id
    demonstration_id: Id
    case_id: Id
    operation_id: Id
    investigation_id: Id
    decision: Literal['ACCEPT', 'REJECT']
    reason: Reason | None
    decided_at: Instant


class DispositionRecorded(StrictInput):
    schema_version: Literal['1']
    receipt: Receipt
    disposition: OwnerDisposition


class LifecycleChanged(StrictInput):
    schema_version: Literal['1']
    receipt: Receipt
    case_id: Id
    lifecycle: Literal['OPEN', 'CLOSED']


class HistoricalDraft(StrictInput):
    schema_version: Literal['1']
    draft_version: DraftVersion
