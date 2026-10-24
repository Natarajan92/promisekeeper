from dataclasses import replace

import pytest

from promisekeeper.domain.evidence import Availability, Extraction, VerificationStatus
from promisekeeper.domain.payments import reconcile_payments
from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.fixtures.catalogue import apply_event, fresh_copy


def settled():
    return apply_event(fresh_copy(),"PK-003-U1").cases["PK-003"]


@pytest.mark.parametrize("change",[
    {"verification_status":VerificationStatus.UNVERIFIED},
    {"verification_status":VerificationStatus.UNKNOWN},
    {"settled":False}, {"invoice_id":None}, {"transaction_ref":None},
])
def test_only_eligible_explicitly_verified_settled_allocations_count(change):
    case=settled().evidence
    modified=replace(case.payments[1],**change)
    facts=reconcile_payments(replace(case,payments=(case.payments[0],modified)))
    assert modified not in facts.eligible_payments
    assert facts.paid_minor != 9000000
    assert facts.issues


def test_designation_alone_is_not_verification_and_untrusted_authority_cannot_settle():
    case=settled().evidence
    untrusted=replace(case.payments[1],source=replace(case.payments[1].source,authoritative=False))
    facts=reconcile_payments(replace(case,payments=(case.payments[0],untrusted)))
    assert untrusted not in facts.eligible_payments
    assert facts.paid_minor != 9000000
    assert facts.issues


def test_unavailable_ledger_never_means_zero_payments():
    case=settled().evidence
    facts=reconcile_payments(replace(case,ledger_availability=Availability.UNAVAILABLE))
    assert facts.paid_minor is None
    assert facts.balance_minor is None
    assert any(issue.code=="LEDGER_UNAVAILABLE" for issue in facts.issues)


def test_duplicate_transaction_counts_once_and_reversal_excludes_only_its_linked_payment():
    duplicate=fresh_copy("FV-06-DUPLICATE").cases["PK-003"].evidence
    reversed_case=fresh_copy("FV-06-REVERSAL").cases["PK-003"].evidence
    assert reconcile_payments(duplicate).paid_minor==9000000
    assert reconcile_payments(reversed_case).paid_minor==3000000


def test_foreign_copy_payment_is_rejected_before_reconciliation():
    left,right=fresh_copy(),fresh_copy()
    case=left.cases["PK-001"].evidence
    foreign=right.cases["PK-001"].evidence.payments[0]
    with pytest.raises(ValueError,match="ownership"):
        reconcile_payments(replace(case,payments=(foreign,)))


def test_fv16_quote_boundaries_do_not_change_identity_credit_or_fulfillment():
    fixture=fresh_copy("FV-16-LINKED").cases["PK-002"]
    original=fixture.extraction.commitments[0]
    shorter=replace(original,start=3,quote=original.source.original_content[3:])
    facts=reconcile_payments(fixture.evidence)
    full=reconcile_commitments(fixture.evidence,fixture.extraction,facts)
    short=reconcile_commitments(fixture.evidence,Extraction((shorter,),()),facts)
    assert len(full.commitments)==len(short.commitments)==1
    assert full.commitments[0].id==short.commitments[0].id==fixture.evidence.anchors[0].id
    assert full.commitments[0].fulfilled and short.commitments[0].fulfilled
    assert full.commitments[0].credited_minor==short.commitments[0].credited_minor==2000000


def test_missing_commitment_link_leaves_credit_unresolved_without_changing_balance():
    fixture=fresh_copy("FV-16-UNLINKED").cases["PK-002"]
    facts=reconcile_payments(fixture.evidence)
    commitments=reconcile_commitments(fixture.evidence,fixture.extraction,facts)
    assert facts.balance_minor==3000000
    assert commitments.commitments[0].credited_minor==0
    assert not commitments.commitments[0].fulfilled
    assert commitments.commitments[0].fulfillment_unresolved


def test_foreign_commitment_key_and_forged_quote_cannot_bind_to_a_payment_link():
    fixture=fresh_copy("FV-16-LINKED").cases["PK-002"]
    candidate=fixture.extraction.commitments[0]
    facts=reconcile_payments(fixture.evidence)
    for changed in [replace(candidate,commitment_key="PK-999-M1-C1"),replace(candidate,quote="invented")]:
        with pytest.raises(ValueError):
            reconcile_commitments(fixture.evidence,Extraction((changed,),()),facts)
