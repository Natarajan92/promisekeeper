from fastapi import APIRouter, Request

from promisekeeper.application.cases import create_demonstration, delete_demonstration, list_cases, list_demonstrations
from promisekeeper.application.scenario_updates import catalogue_view
from promisekeeper.contracts.cases import CaseList, CreateDemonstration, DeleteDemonstration, DemonstrationList
from promisekeeper.contracts.common import CommandResponse, Id
from promisekeeper.contracts.scenarios import CatalogueView

router = APIRouter()


@router.get("/catalogue", response_model=CatalogueView)
def catalogue():
    return catalogue_view()


@router.get("/demonstrations", response_model=DemonstrationList)
def demonstrations(request: Request):
    return list_demonstrations(request.app.state.db)


@router.post("/demonstrations", status_code=201, response_model=CommandResponse, response_model_exclude_unset=True)
def create(command: CreateDemonstration, request: Request):
    return create_demonstration(request.app.state.db, command.model_dump())


@router.get("/demonstrations/{demonstration_id}/cases", response_model=CaseList, response_model_exclude_unset=True)
def cases(demonstration_id: Id, request: Request):
    return list_cases(request.app.state.db, demonstration_id)


@router.post("/demonstrations/{demonstration_id}/deletion", response_model=CommandResponse, response_model_exclude_unset=True)
def delete(demonstration_id: Id, command: DeleteDemonstration, request: Request):
    return delete_demonstration(request.app.state.db, demonstration_id, command.model_dump())
