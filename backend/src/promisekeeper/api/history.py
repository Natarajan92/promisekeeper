from typing import Annotated
from fastapi import APIRouter, Query, Request
from promisekeeper.application.history import get_history, get_historical_draft
from promisekeeper.contracts.cases import HistoryView
from promisekeeper.contracts.common import Id
from promisekeeper.contracts.decisions import HistoricalDraft

router = APIRouter()


@router.get('/cases/{case_id}/history', response_model=HistoryView)
def events(case_id: Id, demonstration_id: Id, request: Request,
           cursor: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 50):
    return get_history(request.app.state.db, demonstration_id, case_id, cursor, limit)


@router.get('/draft-versions/{draft_version_id}', response_model=HistoricalDraft)
def draft(draft_version_id: Id, demonstration_id: Id, request: Request):
    return get_historical_draft(request.app.state.db, demonstration_id, draft_version_id)
