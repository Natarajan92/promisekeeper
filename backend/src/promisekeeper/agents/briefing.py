"""Briefing agent: a short owner-facing summary of the case portfolio.

It may only restate supplied facts. Any number it writes must already appear in those facts;
otherwise the deterministic briefing is used instead.
"""
import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from promisekeeper.agents.llm_client import NEBIUS_BASE_URL, AgentCall, chat_structured, make_client, scripted_call

PROMPT_VERSION = 'briefing-1'
SYSTEM_PROMPT = (
    'You brief a small agency owner on their overdue-invoice cases in 3 to 5 plain sentences, most urgent first. '
    'Use only the supplied facts; never invent or recompute amounts or dates. State that nothing is sent to customers '
    'without the owner. Reply with JSON {"briefing": "..."} only.')
NUMBER = re.compile(r'\d[\d,]*(?:\.\d+)?')
ACTION_TEXT = {
    'FOLLOW_UP': 'a follow-up draft is ready for your review',
    'WAIT': 'wait; the customer promise has not expired yet',
    'VERIFY_PAYMENT': 'verify the payment record before contacting the customer',
    'CLOSE': 'the records show it settled; confirm closure when ready',
}


class BriefingOut(BaseModel):
    model_config = ConfigDict(extra='forbid')
    briefing: str = Field(max_length=1200)


class BriefingAgent(Protocol):
    def summarize(self, facts: list[dict], *, timeout: float) -> AgentCall: ...


def _normalise(token):
    value = token.replace(',', '')
    return value.split('.')[0] if re.fullmatch(r'\d+\.0+', value) else value


def briefing_numbers_supported(text, facts):
    supported = {_normalise(token) for fact in facts for value in fact.values() if isinstance(value, str)
                 for token in NUMBER.findall(value)}
    return all(_normalise(token) in supported for token in NUMBER.findall(text))


def deterministic_briefing(facts):
    lines = []
    for fact in facts:
        head = f"{fact['client']} ({fact['invoice_id']})"
        if fact.get('outcome') == 'SKIPPED':
            lines.append(f'{head}: no new investigation was needed.')
            continue
        action = ACTION_TEXT.get(fact.get('action'), 'review the latest result')
        detail = f"; verified balance {fact['balance_text']}" if fact.get('balance_text') and fact.get('action') == 'FOLLOW_UP' else ''
        when = f"; next review {fact['review_at_text']}" if fact.get('review_at_text') else ''
        lines.append(f'{head}: {action}{detail}{when}.')
    return 'Here is your case review. ' + ' '.join(lines) + ' Nothing is sent to customers without your approval.'


class NebiusBriefing:
    def __init__(self, settings, *, client=None):
        self.model = settings.model
        self.client = client or make_client(NEBIUS_BASE_URL, settings.api_key)

    def summarize(self, facts, *, timeout):
        return chat_structured(self.client, model=self.model, system=SYSTEM_PROMPT, user={'cases': facts},
                               schema_model=BriefingOut, timeout=timeout)


class ScriptedBriefing:
    def summarize(self, facts, *, timeout):
        return scripted_call({'briefing': deterministic_briefing(facts)})
