"""Bounded English clause validation; never general natural-language verification."""
from promisekeeper.domain.personal_note import (
    FEE_OR_THREAT, FOREIGN_CURRENCY, PAYMENT_ASSERTION, PAYMENT_INSTRUCTION, PLACEHOLDER, STATED_AMOUNT, note_reasons,
)
from promisekeeper.domain.review import (
    CLARIFICATION_REQUESTS, CLOSINGS, FOLLOW_UP_REQUESTS, GREETINGS, DraftPlan,
)


def validate_draft(plan: DraftPlan, exact_text: str, recipient: str) -> tuple[str, ...]:
    reasons = []
    if recipient not in plan.allowed_recipients:
        reasons.append('UNSUPPORTED_RECIPIENT')
    if plan.exact_text is None:
        return tuple(reasons + ['NO_CUSTOMER_DRAFT'])
    if not isinstance(exact_text, str) or not 1 <= len(exact_text) <= 8000:
        return tuple(reasons + ['DRAFT_TEXT_LENGTH'])
    paragraphs = tuple(exact_text.split('\n\n'))
    greetings = tuple(t.format(recipient=recipient) for t in GREETINGS)
    neutral = set(greetings + FOLLOW_UP_REQUESTS + CLARIFICATION_REQUESTS + CLOSINGS)
    required = tuple(c for c in plan.exact_text.split('\n\n') if c not in neutral)
    if (len(paragraphs) == len(required) + 4 and paragraphs[0] in greetings
            and paragraphs[1] not in neutral and paragraphs[1] not in plan.allowed_clauses):
        # One optional personal note directly after the greeting; it never carries facts.
        flags = note_reasons(paragraphs[1])
        if flags:
            reasons.extend((*flags, 'UNSUPPORTED_CLAUSE'))
        paragraphs = paragraphs[:1] + paragraphs[2:]
    if any(c not in paragraphs for c in required):
        reasons.append('MISSING_REQUIRED_CLAUSE')
    requests = tuple(c for c in FOLLOW_UP_REQUESTS + CLARIFICATION_REQUESTS if c in plan.allowed_clauses)
    if (len(paragraphs) != len(required) + 3 or paragraphs[0] not in greetings
            or paragraphs[-1] not in CLOSINGS or paragraphs[-2] not in requests
            or paragraphs[1:-2] != required):
        reasons.append('UNSUPPORTED_CLAUSE')
    for clause in paragraphs:
        if clause in plan.allowed_clauses:
            continue
        # These checks explain corrections. Exact clause membership and the
        # finite grammar above, never these lexical hints, decide eligibility.
        if PLACEHOLDER.search(clause):
            reasons.append('UNRESOLVED_PLACEHOLDER')
        if FEE_OR_THREAT.search(clause):
            reasons.append('UNSUPPORTED_FEE_OR_THREAT')
        if PAYMENT_INSTRUCTION.search(clause):
            reasons.append('UNSUPPORTED_PAYMENT_INSTRUCTION')
        if PAYMENT_ASSERTION.search(clause):
            reasons.append('UNSUPPORTED_PAYMENT_ASSERTION')
        if FOREIGN_CURRENCY.search(clause):
            reasons.append('UNSUPPORTED_CURRENCY')
        if STATED_AMOUNT.search(clause):
            reasons.append('UNSUPPORTED_AMOUNT')
        if 'UNSUPPORTED_CLAUSE' not in reasons:
            reasons.append('UNSUPPORTED_CLAUSE')
    return tuple(dict.fromkeys(reasons))
