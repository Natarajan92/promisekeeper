from copy import deepcopy
from datetime import datetime, timezone
import json
from types import SimpleNamespace
from uuid import UUID

from pydantic import ValidationError
import pytest

from promisekeeper.contracts.evidence import EvidenceInput, InvoiceInput
from promisekeeper.domain.evidence import commitment_id, require_same_case


COPY = "00000000-0000-4000-8000-000000000001"
CASE = "00000000-0000-4000-8000-000000000002"
SOURCE = "00000000-0000-4000-8000-000000000003"


def payload():
    return dict(schema_version="1", id=SOURCE, demonstration_id=COPY, case_id=CASE,
                source_id="PK-001-I1", kind="INVOICE", original_content="INR -60,000.001",
                event_at=None, arrived_at="2026-10-23T04:30:00Z", availability="AVAILABLE",
                authoritative=True, version=1, supersedes_version_id=None)


@pytest.mark.parametrize("field,value", [
    ("extra_permission", True), ("authoritative", "true"), ("version", "1"),
    ("version", 0), ("schema_version", "2"), ("availability", "verified"),
    ("arrived_at", "2026-10-23T04:30:00"), ("event_at", "2026-10-22T16:00:00"),
])
def test_evidence_contract_rejects_unsafe_or_coerced_metadata(field, value):
    data = payload(); data[field] = value
    with pytest.raises(ValidationError):
        EvidenceInput.model_validate_json(json.dumps(data))


def test_invalid_original_financial_values_are_preserved_for_review():
    data = dict(source=payload(), invoice_id="NS-104", client="Fictional client",
                amount_text="-60,000.001", currency_text="USD", due_text="soon")
    invoice = InvoiceInput.model_validate_json(json.dumps(data))
    assert invoice.amount_text == "-60,000.001"
    assert invoice.currency_text == "USD"
    assert invoice.source.event_at is None
    assert invoice.source.original_content == "INR -60,000.001"


def test_commitment_identity_is_repeatable_and_scoped_to_copy_and_source_version():
    first = commitment_id(UUID(COPY), UUID(SOURCE), "PK-002-M1-C1")
    assert first == commitment_id(UUID(COPY), UUID(SOURCE), "PK-002-M1-C1")
    assert first != commitment_id(UUID(CASE), UUID(SOURCE), "PK-002-M1-C1")
    assert first != commitment_id(UUID(COPY), UUID(CASE), "PK-002-M1-C1")


@pytest.mark.parametrize("copy,case", [(CASE,CASE), (COPY,SOURCE)])
def test_foreign_copy_or_case_evidence_cannot_be_linked(copy, case):
    left = SimpleNamespace(demonstration_id=UUID(COPY), case_id=UUID(CASE))
    right = SimpleNamespace(demonstration_id=UUID(copy), case_id=UUID(case))
    with pytest.raises(ValueError, match="ownership"):
        require_same_case(left, right)
