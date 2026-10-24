from fastapi import APIRouter, Request

from promisekeeper.application.operations import lookup_receipt
from promisekeeper.contracts.common import CommandResponse, Id

router = APIRouter()


@router.get("/operations/{operation_id}", response_model=CommandResponse, response_model_exclude_unset=True)
def operation(operation_id: Id, demonstration_id: Id, request: Request):
    return lookup_receipt(request.app.state.db, demonstration_id, operation_id)
