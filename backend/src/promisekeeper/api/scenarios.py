from fastapi import APIRouter, Request

from promisekeeper.application.scenario_updates import confirm_event, preview_event
from promisekeeper.contracts.common import CommandResponse, Id
from promisekeeper.contracts.scenarios import ConfirmScenarioEvent, ScenarioEventPreview

router = APIRouter()


@router.get("/cases/{case_id}/scenario-events/{event_id}/preview", response_model=ScenarioEventPreview,
            response_model_exclude_unset=True)
def preview(case_id: Id, event_id: str, demonstration_id: Id, request: Request):
    return preview_event(request.app.state.db, demonstration_id, case_id, event_id)


@router.post("/cases/{case_id}/scenario-events", response_model=CommandResponse, response_model_exclude_unset=True)
def confirm(case_id: Id, demonstration_id: Id, command: ConfirmScenarioEvent, request: Request):
    return confirm_event(request.app.state.db, demonstration_id, case_id, command.model_dump())
