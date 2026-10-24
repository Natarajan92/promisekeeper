"""Explicit, case-bound catalogue confirmation; no arbitrary source fields."""

from typing import Literal

from pydantic import Field

from promisekeeper.contracts.cases import EvidenceView
from promisekeeper.contracts.common import CaseCommand, Hash, Id, Instant, Revision
from promisekeeper.contracts.evidence import StrictInput


class ConfirmScenarioEvent(CaseCommand):
    event_id: str
    catalogue_version: str
    confirmed_preview_hash: Hash


class ClockChange(StrictInput):
    from_: Instant = Field(alias="from")
    to: Instant


class ScenarioEventPreview(StrictInput):
    schema_version: Literal["1"]
    catalogue_version: str
    demonstration_id: Id
    case_id: Id
    event_id: str
    expected_case_revision: Revision
    evidence_changes: list[EvidenceView]
    clock_change: ClockChange | None
    preview_hash: Hash


class CatalogueEvent(StrictInput):
    id: str
    kind: Literal["EVIDENCE", "CLOCK"]
    case_id: str
    evaluation_at: Instant


class CatalogueView(StrictInput):
    schema_version: Literal["1"]
    catalogue_version: str
    baseline_case_ids: list[str]
    variant_ids: list[str]
    events: list[CatalogueEvent]
