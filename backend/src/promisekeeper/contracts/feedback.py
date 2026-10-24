"""Owner feedback on a recommendation or a draft."""
from typing import Literal
from pydantic import Field
from promisekeeper.contracts.common import Id, Instant
from promisekeeper.contracts.evidence import StrictInput


class RecordFeedback(StrictInput):
    schema_version: Literal['1']
    operation_id: Id
    investigation_id: Id
    target: Literal['RECOMMENDATION', 'DRAFT']
    rating: Literal['UP', 'DOWN']
    comment: str | None = Field(default=None, max_length=500)


class FeedbackView(StrictInput):
    id: Id
    case_id: Id
    investigation_id: Id
    target: Literal['RECOMMENDATION', 'DRAFT']
    rating: Literal['UP', 'DOWN']
    comment: str | None
    created_at: Instant


class FeedbackRecorded(StrictInput):
    schema_version: Literal['1']
    feedback: FeedbackView
    sent_to_langsmith: bool
