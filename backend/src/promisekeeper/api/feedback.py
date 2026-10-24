"""Owner ratings that help improve the agents; saved locally even without LangSmith."""
from fastapi import APIRouter, Request
from promisekeeper.application.feedback import record_feedback
from promisekeeper.contracts.common import Id
from promisekeeper.contracts.feedback import FeedbackRecorded, RecordFeedback

router = APIRouter()


@router.post('/cases/{case_id}/feedback', status_code=201, response_model=FeedbackRecorded)
def feedback(case_id: Id, demonstration_id: Id, body: RecordFeedback, request: Request):
    return record_feedback(request.app.state.db, demonstration_id, case_id, body.model_dump())
