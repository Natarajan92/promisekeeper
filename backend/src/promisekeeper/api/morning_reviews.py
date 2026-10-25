"""Morning Review: the supervisor agent works through cases that need attention."""
from fastapi import APIRouter, BackgroundTasks, Request
from promisekeeper.contracts.common import Id
from promisekeeper.contracts.morning_reviews import LatestMorningReview, MorningReviewView, StartMorningReview
from promisekeeper.orchestration.morning_review import get_morning_review, latest_morning_review, run_morning_review, start_morning_review

router = APIRouter()


@router.post('/demonstrations/{demonstration_id}/morning-reviews', status_code=202, response_model=MorningReviewView)
def start(demonstration_id: Id, body: StartMorningReview, request: Request, background_tasks: BackgroundTasks):
    view = start_morning_review(request.app.state.db, demonstration_id, body.model_dump())
    if view['status'] == 'RUNNING':
        background_tasks.add_task(run_morning_review, request.app.state.db, request.app.state.agents, view['id'])
    return view


@router.get('/demonstrations/{demonstration_id}/morning-reviews/latest', response_model=LatestMorningReview)
def latest(demonstration_id: Id, request: Request):
    return latest_morning_review(request.app.state.db, demonstration_id)


@router.get('/morning-reviews/{morning_review_id}', response_model=MorningReviewView)
def detail(morning_review_id: Id, demonstration_id: Id, request: Request):
    return get_morning_review(request.app.state.db, demonstration_id, morning_review_id)
