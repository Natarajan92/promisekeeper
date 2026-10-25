from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from promisekeeper.fixtures.catalogue import apply_event, fresh_copy, variant_definition, variant_ids


@pytest.mark.parametrize("variant",variant_ids())
def test_catalogue_variants_keep_exact_six_cases_and_owned_immutable_source_links(variant):
    demo=fresh_copy(variant)
    assert set(demo.cases)=={"PK-001","PK-002","PK-003","PK-004","PK-005","PK-006"}
    for case in demo.cases.values():
        evidence=case.evidence
        sources=[item.source for item in (*evidence.invoices,*evidence.payments,*evidence.messages,*evidence.attributions)]
        assert len({s.id for s in sources})==len(sources)
        for source in sources:
            assert source.demonstration_id==demo.id and source.case_id==evidence.case_id
            assert source.arrived_at<=demo.evaluation_at
        anchors={a.id:a for a in evidence.anchors}
        for link in evidence.attributions:
            assert link.commitment_stable_id in anchors
            assert link.payment_version_id in {p.source.id for p in evidence.payments}
        with pytest.raises(FrozenInstanceError):
            evidence.client="Changed"


def test_every_named_group_has_registered_branch_definitions():
    groups={variant_definition(vid)["group"] for vid in variant_ids()}
    assert groups=={f"FV-{i:02}" for i in range(1,19)}


def test_workflow_presets_declare_outcomes_without_faking_implemented_history():
    for vid in variant_ids():
        entry=variant_definition(vid)
        if "workflow" in entry:
            assert entry["workflow"]
            assert fresh_copy(vid).applied_events==()
    unchanged=variant_definition("FV-17-UNCHANGED")["workflow"]
    assert unchanged["fresh_approval_permitted"] is True
    assert unchanged["restore_old_approval"] is False
    assert variant_definition("FV-17-EVIDENCE")["workflow"]["fresh_approval_permitted"] is False


def test_registered_clock_event_cannot_renew_an_expired_wait_by_moving_backward():
    demo=apply_event(fresh_copy("FV-18-A"),"FV-18-A-CLOCK-2")
    with pytest.raises(ValueError,match="backward"):
        apply_event(demo,"FV-18-A-CLOCK-1")
