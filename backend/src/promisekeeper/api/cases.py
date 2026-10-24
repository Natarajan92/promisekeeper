from fastapi import APIRouter, Request

from promisekeeper.application.cases import get_case, get_evidence
from promisekeeper.contracts.cases import CaseView, EvidenceView
from promisekeeper.contracts.common import Id

router = APIRouter()


@router.get("/cases/{case_id}", response_model=CaseView, response_model_exclude_unset=True)
def detail(case_id: Id, demonstration_id: Id, request: Request):
    return get_case(request.app.state.db, demonstration_id, case_id)


@router.get("/evidence-versions/{evidence_id}", response_model=EvidenceView, response_model_exclude_unset=True)
def evidence(evidence_id: Id, demonstration_id: Id, request: Request):
    return get_evidence(request.app.state.db, demonstration_id, evidence_id)
