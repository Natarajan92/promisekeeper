"""Strict local file commands. CSV/text travels in the existing protected JSON envelope."""
from typing import Literal
from pydantic import Field, field_validator
from promisekeeper.contracts.common import Command, Hash, Id, Revision, Instant

Kind = Literal['customers','invoices','payments','allocations','remittance_email','customer_email','whatsapp']


class IntakePreview(Command):
    kind: Kind
    filename: str = Field(min_length=1,max_length=160)
    content: str = Field(min_length=1,max_length=262144)
    demonstration_id: Id | None = None
    case_id: Id | None = None
    event_at: str | None = None
    context_only: bool = False
    sender_role: Literal['CUSTOMER','OWNER','THIRD_PARTY','UNVERIFIED'] = 'UNVERIFIED'


class IntakeCommit(IntakePreview):
    confirmed_preview_hash: Hash
    confirm: Literal[True]
    fictional_data: Literal[True]
    settled_confirmed: bool = False

    @field_validator('confirm','fictional_data',mode='before')
    @classmethod
    def explicit_confirmation(cls,value):
        if value is not True:raise ValueError('Explicit confirmation required')
        return value


class AllocationCommand(Command):
    payment_id: Id
    case_id: Id
    amount_text: str = Field(min_length=1,max_length=40)
    expected_case_revision: Revision
    confirm: Literal[True]
    settled_confirmed: Literal[True]

    @field_validator('confirm','settled_confirmed',mode='before')
    @classmethod
    def explicit_confirmation(cls,value):
        if value is not True:raise ValueError('Explicit confirmation required')
        return value


class LedgerReviewCommand(Command):
    case_id: Id
    expected_case_revision: Revision
    reviewed_through: Instant
    complete: Literal[True]
    confirm: Literal[True]

    @field_validator('confirm','complete',mode='before')
    @classmethod
    def explicit_confirmation(cls,value):
        if value is not True:raise ValueError('Explicit confirmation required')
        return value
