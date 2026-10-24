"""Deterministic supported customer wording from a current saved result.

Only typed reconciled facts enter the wording. Source message text never becomes
an instruction or an automatically trusted customer-message clause.
"""
from datetime import datetime
import re

from promisekeeper.domain.dates import IST
from promisekeeper.domain.review import (
    CLARIFICATION_REQUESTS, CLOSINGS, FOLLOW_UP_REQUESTS, GREETINGS, DraftPlan,
)


def _amount(balance):
    if not isinstance(balance, dict) or balance.get('currency') != 'INR':
        return None
    raw = balance.get('minor_units')
    if not isinstance(raw, str) or not re.fullmatch(r'[1-9][0-9]*', raw):
        return None
    # String arithmetic preserves all digits without int conversion limits.
    digits = raw.zfill(3)
    whole, fraction = digits[:-2], digits[-2:]
    groups = [whole[max(0, end - 3):end] for end in range(len(whole), 0, -3)]
    return 'INR ' + ','.join(reversed(groups)) + '.' + fraction


def build_draft_plan(case_view: dict) -> DraftPlan:
    recipient, invoice = case_view['client'], case_view['invoice_id']
    result = case_view.get('current_result')
    refs = set()
    if result:
        for key in ('timeline', 'commitments', 'claims'):
            refs.update(r['evidence_version_id'] for r in result.get(key, ()) if r.get('evidence_version_id'))
        cited = set(result.get('explanation', {}).get('sources', ()))
        refs.update(r['id'] for r in case_view.get('evidence', ()) if r.get('stable_source_id') in cited)
    sources = tuple(sorted(refs))

    def no_draft(reason):
        return DraftPlan(recipient, invoice, None, reason, (recipient,), (), sources)

    if not result or result.get('status') not in {'COMPLETE', 'LIMITED'}:
        return no_draft('NO_CURRENT_RESULT')
    action = result.get('action')
    if action in {'WAIT', 'CLOSE'}:
        return no_draft(action + '_NO_CUSTOMER_DRAFT')
    if action == 'VERIFY_PAYMENT':
        if not any(c.get('customer_clarification') is True and c.get('resolved') is False
                   for c in result.get('claims', ())):
            return no_draft('INTERNAL_VERIFICATION_NO_CUSTOMER_DRAFT')
        facts = (f'We are reviewing your payment information for invoice {invoice}.',)
        requests = CLARIFICATION_REQUESTS
    elif action == 'FOLLOW_UP':
        financial = result.get('financial_facts', {})
        amount = _amount(financial.get('balance'))
        if financial.get('certainty') != 'KNOWN' or amount is None:
            return no_draft('UNSUPPORTED_FINANCIAL_FACTS')
        facts = (f'The verified overdue balance for invoice {invoice} is {amount}.',)
        for commitment in result.get('commitments', ()):
            if commitment.get('superseded') or commitment.get('fulfilled'):
                continue
            expiry = commitment.get('expires_at')
            if expiry:
                # Render the actual expiry instant; never guess whether it came
                # from a date-only deadline or an explicit source timestamp.
                instant = datetime.fromisoformat(expiry)
                if instant.tzinfo is None or instant.utcoffset() is None:
                    return no_draft('UNSUPPORTED_FINANCIAL_FACTS')
                local = instant.astimezone(IST)
                day = f'{local.day} {local.strftime("%B %Y, %H:%M")} IST'
                facts += (f'Your earlier payment promise reached its deadline at {day}.',)
        requests = FOLLOW_UP_REQUESTS
    else:
        return no_draft('NO_CURRENT_RESULT')

    greetings = tuple(t.format(recipient=recipient) for t in GREETINGS)
    clauses = greetings + facts + requests + CLOSINGS
    text = '\n\n'.join((greetings[0], *facts, requests[0], CLOSINGS[0]))
    return DraftPlan(recipient, invoice, text, None, (recipient,), clauses, sources)
