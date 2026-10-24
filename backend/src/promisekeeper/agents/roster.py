"""Allocates each agent role to a provider. A role whose provider lacks a key is None,
and callers fall back explicitly; there is no silent provider or model substitution."""
from dataclasses import dataclass

from promisekeeper.agents.briefing import NebiusBriefing, ScriptedBriefing
from promisekeeper.agents.communicator import NebiusCommunicator, ScriptedCommunicator
from promisekeeper.agents.reviewer import LlmToneReviewer, ScriptedReviewer
from promisekeeper.agents.scripted import ScriptedInvestigator


@dataclass(frozen=True)
class AgentSet:
    investigator: object
    communicator: object
    reviewer: object
    briefing: object
    memory: object = None


def build_agents(settings, *, usage_sink=None):
    if settings.agent_mode == 'STUB':
        return AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), ScriptedBriefing())
    if not settings.api_key:
        investigator = communicator = briefing = None
    else:
        from promisekeeper.agents.nebius import NebiusInvestigator
        investigator = NebiusInvestigator(settings, usage_sink=usage_sink)
        communicator, briefing = NebiusCommunicator(settings), NebiusBriefing(settings)
    reviewer_key = settings.fireworks_api_key if settings.reviewer_provider == 'FIREWORKS' else settings.api_key
    reviewer = LlmToneReviewer(settings) if reviewer_key else None
    return AgentSet(investigator, communicator, reviewer, briefing)
