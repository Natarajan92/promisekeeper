"""Shared PK draft-plan builders for draft and personal-note tests."""
from uuid import uuid4

from promisekeeper.application.derived_findings import derive_findings
from promisekeeper.application.findings import result_view
from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.domain.recommendations import recommend
from promisekeeper.fixtures.catalogue import fresh_copy


def case_view(demo=None, cid="PK-001"):
    demo = demo or fresh_copy()
    item = demo.cases[cid]
    evidence = item.evidence
    recommendation = recommend(evidence, item.extraction, demo.evaluation_at)
    records = [dict(id=str(r.source.id), stable_source_id=r.source.source_id,
                    availability=r.source.availability, original_content=r.source.original_content)
               for r in (*evidence.invoices, *evidence.payments, *evidence.messages, *evidence.attributions)]
    packet = dict(snapshot_id=str(uuid4()), snapshot_hash="a" * 64, evidence=records)
    derived = derive_findings(evidence, item.extraction, recommendation,
                             reconcile_commitments(evidence, item.extraction, recommendation.financial), packet)
    attempt = dict(id=str(uuid4()), snapshot_id=packet["snapshot_id"], evaluation_at=demo.evaluation_at.isoformat())
    result = result_view(attempt, packet, recommendation, derived)
    return dict(client=evidence.client, invoice_id=evidence.invoice_id, current_result=result,
                latest_completed_result=result, evidence=records)


def build(view):
    from promisekeeper.application.draft_templates import build_draft_plan
    return build_draft_plan(view)


def validate(plan, text=None, recipient=None):
    from promisekeeper.domain.draft_validation import validate_draft
    return validate_draft(plan, plan.exact_text if text is None else text,
                          plan.recipient if recipient is None else recipient)
