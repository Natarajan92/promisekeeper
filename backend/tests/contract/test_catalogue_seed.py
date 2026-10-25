from dataclasses import FrozenInstanceError

import pytest

from promisekeeper.fixtures.catalogue import apply_event, fresh_copy, variant_ids


def test_fresh_copies_seed_exactly_six_cases_without_sharing_instance_ids():
    left,right=fresh_copy(),fresh_copy()
    assert left is not None, "A new approved demonstration must be materialized"
    assert set(left.cases)=={"PK-001","PK-002","PK-003","PK-004","PK-005","PK-006"}
    assert left.id != right.id
    assert left.cases["PK-002"].evidence.case_id != right.cases["PK-002"].evidence.case_id
    assert left.evaluation_at.isoformat()=="2026-10-23T10:00:00+05:30"
    a=left.cases["PK-002"].evidence.anchors[0]
    b=right.cases["PK-002"].evidence.anchors[0]
    assert a.commitment_key==b.commitment_key=="PK-002-M1-C1"
    assert a.id != b.id


def test_staged_updates_preserve_old_sources_and_the_original_copy():
    old=fresh_copy()
    assert old is not None, "Fixture copy required"
    new=apply_event(old,"PK-003-U1")
    assert len(old.cases["PK-003"].evidence.payments)==1
    assert len(new.cases["PK-003"].evidence.payments)==2
    assert new.id==old.id
    assert new.cases["PK-003"].evidence.payments[1].source.source_id=="PK-003-L2"
    assert new.cases["PK-003"].evidence.payments[1].source.event_at.isoformat()=="2026-10-22T14:00:00+05:30"
    assert new.cases["PK-003"].evidence.payments[1].source.arrived_at.isoformat()=="2026-10-23T11:00:00+05:30"
    assert apply_event(new,"PK-003-U1")==new


@pytest.mark.parametrize("name",["arbitrary-upload","FV-99"])
def test_unregistered_variant_or_event_is_rejected(name):
    with pytest.raises(ValueError,match="registered"):
        fresh_copy(name)
    with pytest.raises(ValueError,match="registered"):
        apply_event(fresh_copy(),name)


def test_variant_registry_contains_every_financial_and_workflow_branch():
    ids=variant_ids()
    assert len(ids)==40
    assert "FV-16-LINKED" in ids
    assert "FV-16-UNLINKED" in ids
    assert "FV-18-A" in ids and "FV-18-B" in ids
    assert "FV-17-EVIDENCE" in ids
