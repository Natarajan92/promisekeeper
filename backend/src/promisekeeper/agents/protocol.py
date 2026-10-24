"""No autonomous tools, side effects, or financial decisions in this protocol."""
from dataclasses import dataclass, field
from typing import Protocol

PROMPT_VERSION = 'candidate-extraction-7'
EXTRACTION_POLICY_VERSION = 'candidate-only-1'
SCHEMA_VERSION = '1'

class InvestigatorFailure(Exception):
    def __init__(self, code, *, transient=False):
        self.code, self.transient = code, transient
        super().__init__(code)

@dataclass(frozen=True)
class AgentResponse:
    output: dict | str
    returned_model: str | None = None
    response_id: str | None = None
    adapter_version: str = 'scripted-2'
    usage: dict = field(default_factory=dict)

class Investigator(Protocol):
    def extract(self, request: dict, *, timeout: float) -> AgentResponse: ...
