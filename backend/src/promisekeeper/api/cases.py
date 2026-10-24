from typing import Annotated

from fastapi import APIRouter, Query, Request

from promisekeeper.application.cases import get_case, get_evidence
from promisekeeper.contracts.cases import CaseView, EvidenceView, HistoryView
from promisekeeper.contracts.common import Id
from promisekeeper.persistence.repositories import history

router = APIRouter()


@router.get("/cases/{case_id}", response_model=CaseView, response_model_exclude_unset=True)
def detail(case_id: Id, demonstration_id: Id, request: Request):
    return get_case(request.app.state.db, demonstration_id, case_id)


@router.get("/evidence-versions/{evidence_id}", response_model=EvidenceView, response_model_exclude_unset=True)
def evidence(evidence_id: Id, demonstration_id: Id, request: Request):
    return get_evidence(request.app.state.db, demonstration_id, evidence_id)


@router.get("/cases/{case_id}/history", response_model=HistoryView)
def events(case_id: Id, demonstration_id: Id, request: Request,
           cursor: Annotated[int, Query(ge=0)] = 0, limit: Annotated[int, Query(ge=1, le=100)] = 50):
    return history(request.app.state.db, demonstration_id, case_id, cursor, limit)
