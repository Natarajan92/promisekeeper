"""The agent communication protocol: who may hand what to whom.

Every recorded agent step names its recipient and a typed message kind. Hand-offs outside this
protocol are rejected, which keeps the safety path explicit: a Communicator note always passes
the Safety Check before any reviewer or the owner sees it, and only the owner receives drafts.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict

AgentName = Literal['INTAKE', 'EXTRACTOR', 'RULES_ENGINE', 'MEMORY', 'COMMUNICATOR', 'SAFETY_CHECK', 'TONE_REVIEWER',
                    'OWNER', 'SUPERVISOR', 'BRIEFING']
MessageKind = Literal['EVIDENCE_PACKET', 'PAYMENT_CANDIDATES', 'DECISION', 'CLIENT_HISTORY', 'NOTE_DRAFT', 'REVISION_REQUEST',
                      'DRAFT_FOR_APPROVAL', 'CASE_SELECTION', 'CASE_OUTCOME', 'BRIEFING']


class AgentMessage(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    sender: AgentName
    recipient: AgentName
    kind: MessageKind


# Default hand-off for each (sender, outcome); steps whose recipient depends on the route pass it explicitly.
# A Communicator that fails hands nothing on: the owner then receives the code-written template, never its note.
DEFAULT_ROUTES = {
    ('INTAKE', 'SUCCEEDED'): ('EXTRACTOR', 'EVIDENCE_PACKET'),
    ('EXTRACTOR', 'SUCCEEDED'): ('RULES_ENGINE', 'PAYMENT_CANDIDATES'),
    ('MEMORY', 'SUCCEEDED'): ('COMMUNICATOR', 'CLIENT_HISTORY'),
    ('MEMORY', 'SKIPPED'): ('COMMUNICATOR', 'CLIENT_HISTORY'),
    ('COMMUNICATOR', 'SUCCEEDED'): ('SAFETY_CHECK', 'NOTE_DRAFT'),
    ('SAFETY_CHECK', 'SUCCEEDED'): ('TONE_REVIEWER', 'NOTE_DRAFT'),
    ('SAFETY_CHECK', 'REVISE'): ('COMMUNICATOR', 'REVISION_REQUEST'),
    ('SAFETY_CHECK', 'FALLBACK'): ('OWNER', 'DRAFT_FOR_APPROVAL'),
    ('SAFETY_CHECK', 'FAILED'): ('OWNER', 'DRAFT_FOR_APPROVAL'),
    ('TONE_REVIEWER', 'SUCCEEDED'): ('OWNER', 'DRAFT_FOR_APPROVAL'),
    ('TONE_REVIEWER', 'SKIPPED'): ('OWNER', 'DRAFT_FOR_APPROVAL'),
    ('TONE_REVIEWER', 'FAILED'): ('OWNER', 'DRAFT_FOR_APPROVAL'),
    ('TONE_REVIEWER', 'FALLBACK'): ('OWNER', 'DRAFT_FOR_APPROVAL'),
    ('TONE_REVIEWER', 'REVISE'): ('COMMUNICATOR', 'REVISION_REQUEST'),
    ('SUPERVISOR', 'SKIPPED'): ('BRIEFING', 'CASE_OUTCOME'),
    ('SUPERVISOR', 'FAILED'): ('BRIEFING', 'CASE_OUTCOME'),
    ('BRIEFING', 'SUCCEEDED'): ('OWNER', 'BRIEFING'),
    ('BRIEFING', 'FALLBACK'): ('OWNER', 'BRIEFING'),
    ('BRIEFING', 'FAILED'): ('OWNER', 'BRIEFING'),
    ('BRIEFING', 'SKIPPED'): ('OWNER', 'BRIEFING'),
}
EXPLICIT_ROUTES = {
    ('RULES_ENGINE', 'MEMORY', 'DECISION'), ('RULES_ENGINE', 'OWNER', 'DECISION'),
    ('MEMORY', 'COMMUNICATOR', 'CLIENT_HISTORY'),
    ('SUPERVISOR', 'INTAKE', 'CASE_SELECTION'), ('SUPERVISOR', 'BRIEFING', 'CASE_OUTCOME'),
}
PROTOCOL = {(sender, recipient, kind) for (sender, _), (recipient, kind) in DEFAULT_ROUTES.items()} | EXPLICIT_ROUTES


def route_for(sender, outcome, *, to=None, kind=None):
    """The typed message for a recorded step, or None for steps that hand nothing on (owner decisions)."""
    if to is None and kind is None:
        route = DEFAULT_ROUTES.get((sender, outcome))
        if route is None:
            return None
        to, kind = route
    if (sender, to, kind) not in PROTOCOL:
        raise ValueError(f'Hand-off {sender} -> {to} ({kind}) is not in the agent protocol')
    return AgentMessage(sender=sender, recipient=to, kind=kind)
