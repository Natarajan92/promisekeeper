"""Save and review only. There is no customer transmission capability."""
from fastapi import APIRouter,BackgroundTasks,Request
from promisekeeper.contracts.common import Id
from promisekeeper.contracts.reviews import SaveDraft,ReviewDraft,RetryDraft,DraftSaved,DraftReviewed,DraftRetryStarted,DraftAttemptView,DeletedDraftOperation
from promisekeeper.application.reviews import save_draft,review_draft
from promisekeeper.application.draft_retry import retry_draft,get_attempt
from promisekeeper.orchestration.drafts import generate_draft

router=APIRouter()

@router.post('/cases/{case_id}/draft-versions',status_code=201,response_model=DraftSaved|DeletedDraftOperation)
def save(case_id:Id,demonstration_id:Id,body:SaveDraft,request:Request):
    return save_draft(request.app.state.db,demonstration_id,case_id,body.model_dump())

@router.post('/cases/{case_id}/draft-reviews',response_model=DraftReviewed|DeletedDraftOperation)
def review(case_id:Id,demonstration_id:Id,body:ReviewDraft,request:Request):
    return review_draft(request.app.state.db,demonstration_id,case_id,body.model_dump())

@router.post('/cases/{case_id}/draft-retries',status_code=202,response_model=DraftRetryStarted|DeletedDraftOperation)
def retry(case_id:Id,demonstration_id:Id,body:RetryDraft,request:Request,background_tasks:BackgroundTasks):
    response=retry_draft(request.app.state.db,demonstration_id,case_id,body.model_dump())
    if response['receipt']['outcome']!='DELETED':
        background_tasks.add_task(generate_draft,request.app.state.db,response['draft_attempt_id'],getattr(request.app.state,'draft_generator',None))
    return response

@router.get('/draft-attempts/{draft_attempt_id}',response_model=DraftAttemptView)
def detail(draft_attempt_id:Id,demonstration_id:Id,request:Request):
    return get_attempt(request.app.state.db,demonstration_id,draft_attempt_id)
