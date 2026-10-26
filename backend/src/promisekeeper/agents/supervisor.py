"""Planning supervisor: chooses, one step at a time, which case the morning review works on next.

After every investigation it re-plans from the updated outcomes. It sees only structured case
facts (never customer message text), and may only choose INVESTIGATE for a pending case or FINISH.
Code validates every choice (see orchestration.morning_review); an invalid, failed or slow choice
falls back to rule order. It never sends, approves, closes or changes money.
"""
from decimal import Decimal
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from promisekeeper.agents.llm_client import NEBIUS_BASE_URL, AgentCall, chat_structured, make_client, scripted_call

PROMPT_VERSION = 'supervisor-2'
SYSTEM_PROMPT = (
    'You supervise a small agency owner\'s morning review of overdue-invoice cases. Each turn, choose exactly one next step. '
    'INVESTIGATE runs a read-only investigation of one pending case; FINISH ends the review and writes the briefing. '
    'Every case with must_investigate=true must be investigated before you FINISH. You may also investigate a case whose '
    'saved recommendation is still current when the facts suggest it is worth re-checking now (for example a review date '
    'that is very close). Put the most urgent work first: unverified payment claims and review-required cases, then larger '
    'and older overdue balances. A balance of INR 0.00 means the ledger shows nothing owed: check that case last, never as '
    'urgent. A null balance or action only means the case has not been investigated yet, not that details are missing. '
    'Use the outcomes so far to re-plan. Never invent facts. Give one short owner-facing reason of at most 25 words that '
    'names the client, never a case code such as PK-001, and uses only the supplied facts. '
    'Reply with JSON {"action": "INVESTIGATE"|"FINISH", "case": "PK-00n"|null, "reason": "..."} only.')


class SupervisorStep(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['INVESTIGATE', 'FINISH']
    case: str | None = Field(default=None, max_length=12)
    reason: str = Field(min_length=1, max_length=240)


class SupervisorAgent(Protocol):
    def next_step(self, context: dict, *, timeout: float) -> AgentCall: ...


def _balance(item):
    text = item.get('balance_text') or ''
    try:
        return Decimal(text.split(' ')[-1].replace(',', '')) if text else Decimal(0)
    except ArithmeticError:
        return Decimal(0)


def _urgency(item):
    return (not item['review_required'], item.get('recommended_action') != 'VERIFY_PAYMENT', -_balance(item), -item.get('days_overdue', 0))


def scripted_choice(context):
    """Risk-first policy used in STUB mode: a deterministic stand-in for the LLM, never a fallback."""
    due = [item for item in context['pending'] if item['must_investigate']]
    if not due:
        return {'action': 'FINISH', 'case': None,
                'reason': 'Every case that needed work is done; the other saved recommendations are still current.'}
    item = min(due, key=_urgency)
    if item['review_required']:
        why = 'evidence changed since the last recommendation'
    elif item.get('recommended_action') == 'VERIFY_PAYMENT':
        why = 'a payment claim still needs checking against the ledger'
    elif _balance(item) > 0:
        days = item.get('days_overdue', 0)
        # 0 means not yet overdue or no due date; say nothing rather than "overdue 0 days".
        overdue = f", overdue {days} day{'' if days == 1 else 's'}" if days > 0 else ''
        why = f"largest open balance still waiting ({item['balance_text']}){overdue}"
    else:
        why = 'nothing appears outstanding; confirming whether it can close'
    return {'action': 'INVESTIGATE', 'case': item['case'], 'reason': f'{why[0].upper()}{why[1:]}.'}


class NebiusSupervisor:
    def __init__(self, settings, *, client=None):
        self.model = settings.supervisor_model or settings.model
        self.client = client or make_client(NEBIUS_BASE_URL, settings.api_key)

    def next_step(self, context, *, timeout):
        return chat_structured(self.client, model=self.model, system=SYSTEM_PROMPT, user=context,
                               schema_model=SupervisorStep, timeout=timeout)


class ScriptedSupervisor:
    """Preset choices first (tests), then the risk-first policy."""
    def __init__(self, choices=()):
        self.choices = list(choices)

    def next_step(self, context, *, timeout):
        if self.choices:
            choice = self.choices.pop(0)
            if isinstance(choice, Exception):
                raise choice
            return scripted_call(choice)
        return scripted_call(scripted_choice(context))
