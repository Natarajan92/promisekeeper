"""Deterministic supported explanations and source-time chronology."""
from promisekeeper.application.operations import digest, instant

def money(value):
    return dict(currency='INR',minor_units=str(value)) if value is not None else None

def result_view(attempt, packet, recommendation, derived, *, limitations=()):
    r=recommendation; f=r.financial
    sources={s['stable_source_id']:s for s in packet['evidence']}
    def ref(source): return sources[source]['id']
    financial=dict(certainty='KNOWN' if f.balance_minor is not None else 'UNKNOWN',invoice=money(f.invoice_minor),paid=money(f.paid_minor),balance=money(f.balance_minor),
        due_at=instant(f.due_at) if f.due_at else None,issues=derived['financial_issues'])
    explanation={
        'FOLLOW_UP':'Verified evidence supports following up on the overdue remainder.',
        'WAIT':'The invoice or an active unfulfilled promise supports waiting until the next review boundary.',
        'VERIFY_PAYMENT':'Review the cited evidence and unresolved payment facts before deciding. Any recorded remainder is contested.',
        'CLOSE':'Verified settlement supports an explicit owner review of closure.'}[r.action]
    result=dict(investigation_id=attempt['id'],snapshot_id=attempt['snapshot_id'],snapshot_hash=packet['snapshot_hash'],evaluation_at=attempt['evaluation_at'],
        status=r.status,financial_facts=financial,financial_label='UNKNOWN_REMAINDER' if f.balance_minor is None else 'RECORDED_REMAINDER' if r.action=='VERIFY_PAYMENT' else 'VERIFIED_REMAINDER',
        commitments=[dict(commitment_stable_id=str(c.id) if c.id else None,commitment_key=c.commitment_key,source_id=c.source_id,evidence_version_id=ref(c.source_id),
            amount=money(c.amount_minor),expires_at=instant(c.expires_at) if c.expires_at else None,fulfilled=c.fulfilled,fulfillment_unresolved=c.fulfillment_unresolved,credited=money(c.credited_minor),superseded=c.superseded) for c in r.commitments],
        claims=[dict(source_id=c.source_id,evidence_version_id=ref(c.source_id),resolved=c.resolved,customer_clarification=c.customer_clarification) for c in r.claims],
        timeline=[dict(source_id=s.source_id,evidence_version_id=str(s.id),event_at=instant(s.event_at) if s.event_at else None,arrived_at=instant(s.arrived_at),kind=s.kind,undated=s.event_at is None) for s in (*r.dated_sources,*r.undated_sources)],
        contradictions=derived['contradictions'],unresolved_questions=derived['unresolved_questions'],limitations=list(limitations),
        findings_version=derived['findings_version'],commitment_issues=derived['commitment_issues'],evidence_observations=derived['evidence_observations'],
        action=r.action,reason_code=r.reason_code,explanation=dict(text=explanation,sources=list(r.source_refs)),next_step=r.next_step,
        review_at=instant(r.review_at) if r.review_at else None)
    result['result_hash']=digest(result)
    return result
