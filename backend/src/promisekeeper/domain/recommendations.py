"""Ordered responsible actions; implementation follows decision tests."""

from dataclasses import dataclass
from datetime import datetime

from promisekeeper.domain.commitments import CommitmentState, ClaimState, reconcile_commitments
from promisekeeper.domain.dates import ordered_timeline, review_boundary
from promisekeeper.domain.evidence import Evidence
from promisekeeper.domain.payments import FinancialFacts, reconcile_payments


@dataclass(frozen=True, slots=True)
class Recommendation:
    action: str | None
    status: str
    financial: FinancialFacts
    commitments: tuple[CommitmentState, ...]
    claims: tuple[ClaimState, ...]
    review_at: datetime | None
    reason_code: str
    source_refs: tuple[str, ...]
    next_step: str
    dated_sources: tuple[Evidence, ...] = ()
    undated_sources: tuple[Evidence, ...] = ()


def recommend(case, extraction, evaluation_at, *, attempt_complete=True):
    if evaluation_at.tzinfo is None or evaluation_at.utcoffset() is None:
        raise ValueError("Evaluation time requires a timezone")
    if not attempt_complete:
        return Recommendation(None, "INCOMPLETE", FinancialFacts(None, None, None, None, (), (), ()),
                              (), (), None, "INCOMPLETE_ATTEMPT", (), "Retry the incomplete investigation explicitly.")
    financial = reconcile_payments(case)
    findings = reconcile_commitments(case, extraction, financial)
    sources = {item.source.id: item.source for item in (*case.invoices, *case.payments, *case.messages, *case.attributions)}
    dated, undated = ordered_timeline(sources.values())
    refs = tuple(sorted({source.source_id for source in sources.values()}))
    active = [item for item in findings.commitments if not item.fulfilled and not item.superseded]
    balance = financial.balance_minor
    positive = balance is not None and balance > 0
    finance_issues = [issue for issue in financial.issues if not (issue.code == "INVOICE_DATE_UNRESOLVED" and balance == 0)]
    commitment_issues = [issue for issue in findings.issues if balance != 0 or issue.code == "MISSING_EXTRACTION"]
    missing = any(issue.code in {"MISSING_EXTRACTION", "AMBIGUOUS_COMMITMENT"} for issue in findings.issues)
    unknown_timing = positive and any(item.expires_at is None for item in active)
    conflicting = positive and len({(item.amount_minor, item.expires_at) for item in active}) > 1
    unresolved_claim = any(not claim.resolved for claim in findings.claims)
    invoice_due = financial.due_at is not None and evaluation_at >= financial.due_at
    attribution_changes_action = positive and invoice_due and any(
        item.expires_at is not None and evaluation_at < item.expires_at and item.amount_minor is not None
        and item.fulfillment_unresolved and (item.id is None or item.possible_credit_minor >= item.amount_minor)
        for item in active)
    status = "LIMITED" if balance is None or missing else "COMPLETE"
    review = None
    if finance_issues or commitment_issues or balance is None or unresolved_claim or unknown_timing or conflicting or attribution_changes_action:
        action = "VERIFY_PAYMENT"
        if finance_issues:
            reason = finance_issues[0].code
        elif commitment_issues:
            reason = commitment_issues[0].code
        elif unresolved_claim:
            reason = "PAYMENT_CLAIM_UNVERIFIED"
        elif unknown_timing:
            reason = "PROMISE_DATE_UNRESOLVED"
        elif conflicting:
            reason = "CONFLICTING_PROMISES"
        elif attribution_changes_action:
            reason = "COMMITMENT_ATTRIBUTION_UNRESOLVED"
        else:
            reason = "BALANCE_UNRESOLVED"
        if any(claim.customer_clarification and not claim.resolved for claim in findings.claims):
            step = "Ask the customer for the missing payment reference or receipt."
        elif unresolved_claim:
            references = ", ".join(candidate.transaction_reference_text for candidate in extraction.claims if candidate.transaction_reference_text)
            step = f"Review the internal ledger for payment reference {references}."
        else:
            step = f"Review {reason} in the preserved source evidence before deciding."
    elif balance == 0:
        action, reason = "CLOSE", "VERIFIED_SETTLEMENT"
        step = "Review the settlement sources and explicitly confirm closure."
    else:
        future_promises = [item.expires_at for item in active if item.expires_at is not None and item.expires_at > evaluation_at]
        if future_promises or (financial.due_at is not None and evaluation_at < financial.due_at):
            action, reason = "WAIT", "ACTIVE_PROMISE_OR_NOT_DUE"
            review = review_boundary(evaluation_at, invoice_due=financial.due_at, promise_expiries=future_promises)
            step = f"Review the case at {review.isoformat()}."
        else:
            action, reason = "FOLLOW_UP", "VERIFIED_OVERDUE_BALANCE"
            step = "Review a follow-up draft for the verified overdue remainder."
    return Recommendation(action, status, financial, findings.commitments, findings.claims, review, reason, refs, step, dated, undated)
