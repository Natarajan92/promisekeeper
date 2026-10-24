"""Morning Review views: supervisor outcomes per case and the owner briefing."""
from typing import Literal
from promisekeeper.contracts.common import Id, Instant
from promisekeeper.contracts.evidence import StrictInput
from promisekeeper.contracts.investigations import Action, AgentActivityView


class StartMorningReview(StrictInput):
    schema_version: Literal['1']
    operation_id: Id


class CaseOutcome(StrictInput):
    case_id: Id
    client: str
    invoice_id: str
    outcome: Literal['INVESTIGATED', 'SKIPPED', 'FAILED']
    action: Action | None
    reason: str | None
    balance_text: str | None
    review_at_text: str | None
    draft_ready: bool


class MorningReviewView(StrictInput):
    schema_version: Literal['1']
    id: Id
    demonstration_id: Id
    status: Literal['RUNNING', 'COMPLETE', 'FAILED']
    started_at: Instant
    terminal_at: Instant | None
    briefing: str | None
    briefing_source: Literal['AGENT', 'DETERMINISTIC'] | None
    failure_code: str | None
    outcomes: list[CaseOutcome]
    agent_activity: list[AgentActivityView]
    started_by: Literal['OWNER', 'AUTONOMOUS'] = 'OWNER'


class LatestMorningReview(StrictInput):
    schema_version: Literal['1']
    morning_review: MorningReviewView | None
