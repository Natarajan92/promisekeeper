"""Scoped advice and lifecycle commands; all responses are durable receipts."""
from fastapi import APIRouter, Request
from promisekeeper.application.decisions import record_disposition
from promisekeeper.application.lifecycle import close_case, reopen_case
from promisekeeper.contracts.common import Id
from promisekeeper.contracts.decisions import DispositionCommand, CloseCase, ReopenCase, DispositionRecorded, LifecycleChanged
from promisekeeper.contracts.reviews import DeletedDraftOperation

router = APIRouter()


@router.post('/cases/{case_id}/dispositions', response_model=DispositionRecorded|DeletedDraftOperation)
def disposition(case_id: Id, demonstration_id: Id, body: DispositionCommand, request: Request):
    return record_disposition(request.app.state.db, demonstration_id, case_id, body.model_dump())


@router.post('/cases/{case_id}/closure', response_model=LifecycleChanged|DeletedDraftOperation)
def close(case_id: Id, demonstration_id: Id, body: CloseCase, request: Request):
    return close_case(request.app.state.db, demonstration_id, case_id, body.model_dump())


@router.post('/cases/{case_id}/reopening', response_model=LifecycleChanged|DeletedDraftOperation)
def reopen(case_id: Id, demonstration_id: Id, body: ReopenCase, request: Request):
    return reopen_case(request.app.state.db, demonstration_id, case_id, body.model_dump())
