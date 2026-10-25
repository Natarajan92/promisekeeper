"""Allocates each agent role to a provider. A role whose provider lacks a key is None,
and callers fall back explicitly; there is no silent provider or model substitution."""
from dataclasses import dataclass

from promisekeeper.agents.briefing import NebiusBriefing, ScriptedBriefing
from promisekeeper.agents.communicator import NebiusCommunicator, ScriptedCommunicator
from promisekeeper.agents.reviewer import LlmToneReviewer, ScriptedReviewer
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.agents.supervisor import NebiusSupervisor, ScriptedSupervisor


@dataclass(frozen=True)
class AgentSet:
    investigator: object
    communicator: object
    reviewer: object
    briefing: object
    memory: object = None
    supervisor: object = None


def build_agents(settings, *, usage_sink=None):
    if settings.agent_mode == 'STUB':
        return AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), ScriptedBriefing(),
                        supervisor=ScriptedSupervisor())
    if not settings.api_key:
        investigator = communicator = briefing = supervisor = None
    else:
        from promisekeeper.agents.nebius import NebiusInvestigator
        investigator = NebiusInvestigator(settings, usage_sink=usage_sink)
        communicator, briefing = NebiusCommunicator(settings), NebiusBriefing(settings)
        supervisor = NebiusSupervisor(settings)
    reviewer_key = settings.fireworks_api_key if settings.reviewer_provider == 'FIREWORKS' else settings.api_key
    reviewer = LlmToneReviewer(settings) if reviewer_key else None
    # mem0 is opt-in for LIVE; otherwise the case graph uses the local SQLite memory.
    memory = None
    if settings.mem0_api_key:
        from promisekeeper.agents.memory import Mem0Memory
        memory = Mem0Memory(settings.mem0_api_key)
    return AgentSet(investigator, communicator, reviewer, briefing, memory, supervisor)
