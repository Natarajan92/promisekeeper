from fastapi import APIRouter, BackgroundTasks, Request
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.operations import CommandError
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.contracts.common import Id, CommandResponse
from promisekeeper.contracts.investigations import StartInvestigation, InvestigationView
from promisekeeper.orchestration.investigate import investigate, get_investigation

router=APIRouter()

@router.post('/cases/{case_id}/investigations',status_code=202,response_model=CommandResponse,response_model_exclude_unset=True)
def start(case_id:Id,demonstration_id:Id,body:StartInvestigation,request:Request,background_tasks:BackgroundTasks):
    app=request.app;settings=app.state.settings
    worker=getattr(app.state,'investigator',None)
    agents=getattr(app.state,'agents',None)
    if worker is None and agents is not None:worker=agents.investigator
    # Known receipts remain replayable even if provider configuration later changes.
    from promisekeeper.application.operations import replay
    with app.state.db.connection() as con:
        saved=replay(con,demonstration_id,'START_INVESTIGATION',case_id,body.model_dump())
    if saved: return saved
    if not settings.capability_available and worker is None: raise CommandError('CAPABILITY_UNAVAILABLE',503)
    if worker is None:
        if settings.agent_mode=='STUB': worker=ScriptedInvestigator()
        else:
            from promisekeeper.agents.nebius import NebiusInvestigator
            from promisekeeper.application.provider_usage import usage_recorder
            from pathlib import Path
            worker=NebiusInvestigator(settings,usage_sink=usage_recorder(Path(__file__).resolve().parents[4]/'.runtime'/'application-provider-usage.jsonl'))
    response=start_investigation(app.state.db,demonstration_id,case_id,body.model_dump(),agent_mode=settings.agent_mode,requested_model=settings.model if settings.agent_mode=='LIVE' else None)
    background_tasks.add_task(investigate,app.state.db,response['investigation_id'],worker,draft_generator=getattr(app.state,'draft_generator',None),agents=agents)
    return response

@router.get('/investigations/{investigation_id}',response_model=InvestigationView,response_model_exclude_unset=True)
def detail(investigation_id:Id,demonstration_id:Id,request:Request):
    return get_investigation(request.app.state.db,demonstration_id,investigation_id,token_rates=request.app.state.settings.token_rates)
