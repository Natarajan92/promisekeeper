"""Strict version-one wire values. UUIDs and instants retain their JSON spelling."""

from datetime import datetime, timedelta
from typing import Annotated, Literal

from pydantic import AfterValidator, Field, StringConstraints

from promisekeeper.contracts.evidence import StrictInput


Id = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")]
Revision = Annotated[int, Field(ge=0)]
Hash = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


def utc_instant(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("UTC instant required")
    return value


Instant = Annotated[str, AfterValidator(utc_instant), Field(json_schema_extra={"format": "date-time"})]


class Command(StrictInput):
    schema_version: Literal["1"]
    operation_id: Id


class CaseCommand(Command):
    expected_case_revision: Revision


class Receipt(StrictInput):
    operation_id: Id
    operation_type: str
    target_id: Id
    committed_at: Instant
    outcome: str
    case_revision: Revision | None


class CommandResponse(StrictInput):
    schema_version: Literal["1"]
    receipt: Receipt
    demonstration_id: Id | None = None
    investigation_id: Id | None = None
    snapshot_id: Id | None = None
    evaluation_at: Instant | None = None
    deadline_at: Instant | None = None


class ErrorDetail(StrictInput):
    code: str
    message: str
    operation_id: Id | None
    retryable: bool
    blocking_reasons: list[str]


class ErrorResponse(StrictInput):
    schema_version: Literal["1"] = "1"
    error: ErrorDetail


class AgentRole(StrictInput):
    role: Literal["Extractor", "Communicator", "Tone Reviewer", "Briefing", "Memory"]
    provider: Literal["SCRIPTED", "NEBIUS", "FIREWORKS", "MEM0", "LOCAL"]
    model: str | None
    available: bool
    can_change: list[str]


class SafeConfiguration(StrictInput):
    agent_mode: Literal["STUB", "LIVE"]
    model: str
    capability_available: bool
    agents: list[AgentRole]
    autonomous_review_minutes: int = 0


class Health(StrictInput):
    schema_version: Literal["1"] = "1"
    ready: bool
    catalogue_version: str
    agent_mode: Literal["STUB", "LIVE"]
    configuration: SafeConfiguration
