"""Deterministic findings over validated candidates and immutable captured evidence.

This module does not select actions or alter reconciliation. Known comparisons use
the shared lifecycle projection; unknown fields belong to their exact sources.
"""
from itertools import combinations

from promisekeeper.domain.dates import IST, deadline, source_day
from promisekeeper.domain.evidence import Availability
from promisekeeper.domain.money import parse_money
from promisekeeper.domain.record_lifecycle import project_records

FINDINGS_VERSION = 'deterministic-1'


def derive_findings(case, extraction, recommendation, commitment_facts, packet):
    records = {r['id']: r for r in packet['evidence']}
    questions, contradictions = {}, {}

    def reference(source):
        record = records[str(source.id)]
        if record['stable_source_id'] != source.source_id:
            raise ValueError('Finding source differs from captured source')
        return dict(source_id=source.source_id, evidence_version_id=str(source.id))

    def span(record, candidate=False):
        source = record.source
        retained = records[str(source.id)]
        reference(source)
        if source.availability != Availability.AVAILABLE or not source.original_content:
            return None
        start, end = (record.start, record.end) if candidate else (0, len(source.original_content))
        quote = record.quote if candidate else source.original_content
        if not 0 <= start < end <= len(retained['original_content']) or retained['original_content'][start:end] != quote:
            raise ValueError('Finding quote differs from captured source')
        return dict(**reference(source), start=start, end=end, quote=quote)

    def question(field, source_span):
        if source_span:
            questions.setdefault((field, source_span['source_id']), dict(field=field, sources=[source_span]))

    def contradiction(kind, left, right):
        if left and right and left['source_id'] != right['source_id']:
            pair = tuple(sorted((left['source_id'], right['source_id'])))
            contradictions.setdefault((kind, pair), dict(kind=kind, sources=sorted([left, right], key=lambda s:s['source_id'])))

    def amount_fields(record, citation):
        amount = parse_money(record.amount_text, 'INR').minor_units
        if amount is None:
            question('AMOUNT', citation)
        if record.currency_text != 'INR':
            question('CURRENCY', citation)
        return amount, record.currency_text

    def active(records, *, payment=False):
        lifecycle = project_records(records, payment=payment)
        excluded = lifecycle.invalid_ids | lifecycle.ambiguous_ids | lifecycle.reversed_ids | lifecycle.reversal_ids
        # A rejected correction can still have an intrinsic field gap. Preserve
        # that gap on its own source while excluding it from known comparisons.
        for record in records:
            if (record.source.id in lifecycle.invalid_ids | lifecycle.ambiguous_ids
                    and record.source.id not in lifecycle.superseded_ids | lifecycle.reversed_ids | lifecycle.reversal_ids
                    and record.source.availability == Availability.AVAILABLE):
                citation = span(record)
                amount_fields(record, citation)
                if payment:
                    if not record.transaction_ref:
                        question('PAYMENT_REFERENCE', citation)
                    if record.source.event_at is None:
                        question('PAYMENT_DATE', citation)
        return [r for r in lifecycle.active_records if r.source.id not in excluded
                and r.source.authoritative and r.source.availability == Availability.AVAILABLE]

    def compare(kind, left, right, *, date_field=None):
        # Amounts are known only for supported nonnegative INR values. A stated
        # currency can disagree independently of whether this app supports it.
        a, b = left['amount'], right['amount']
        different = False
        if left['currency'] == right['currency'] == 'INR' and a is not None and b is not None and a != b:
            different = True
            question('AMOUNT', left['span']); question('AMOUNT', right['span'])
        if left['currency'] is not None and right['currency'] is not None and left['currency'] != right['currency']:
            different = True
            question('CURRENCY', left['span']); question('CURRENCY', right['span'])
        if left.get('date') is not None and right.get('date') is not None and left['date'] != right['date']:
            different = True
            if date_field:
                question(date_field, left['span']); question(date_field, right['span'])
        if different:
            contradiction(kind, left['span'], right['span'])

    invoices = []
    for record in active(case.invoices):
        citation = span(record)
        amount, currency = amount_fields(record, citation)
        invoices.append(dict(record=record, span=citation, amount=amount, currency=currency,
                             date=deadline(record.due_text, original_at=record.source.event_at).expires_at))
    for left, right in combinations(invoices, 2):
        if left['record'].invoice_id == right['record'].invoice_id:
            compare('INVOICE_FACT', left, right)

    payments = []
    for record in active(case.payments, payment=True):
        citation = span(record)
        amount, currency = amount_fields(record, citation)
        if not record.transaction_ref:
            question('PAYMENT_REFERENCE', citation)
        if record.source.event_at is None:
            question('PAYMENT_DATE', citation)
        payments.append(dict(record=record, span=citation, amount=amount, currency=currency,
                             date=record.source.event_at.astimezone(IST).date() if record.source.event_at else None))
    for left, right in combinations(payments, 2):
        if left['record'].transaction_ref and left['record'].transaction_ref == right['record'].transaction_ref:
            compare('OTHER_CANDIDATE', left, right, date_field='PAYMENT_DATE')

    for candidate in extraction.claims:
        citation = span(candidate, True)
        amount, currency = amount_fields(candidate, citation)
        date = source_day(candidate.payment_date_text, original_at=candidate.source.event_at)
        if candidate.speaker is None:
            question('SPEAKER', citation)
        if date is None:
            question('PAYMENT_DATE', citation)
        if not candidate.transaction_reference_text:
            question('PAYMENT_REFERENCE', citation)
        for payment in payments:
            if candidate.transaction_reference_text and candidate.transaction_reference_text == payment['record'].transaction_ref:
                # Preserve the claim's original timezone for date interpretation,
                # matching the domain's source-clock comparison.
                event = payment['record'].source.event_at
                actual = event.astimezone(candidate.source.event_at.tzinfo if candidate.source.event_at else IST).date() if event else None
                compare('PAYMENT_CLAIM', dict(span=citation, amount=amount, currency=currency, date=date),
                        payment | dict(date=actual), date_field='PAYMENT_DATE')

    promises = []
    for candidate, state in zip(extraction.commitments, commitment_facts.commitments, strict=True):
        if state.superseded or state.fulfilled:
            continue
        citation = span(candidate, True)
        amount, currency = amount_fields(candidate, citation)
        if candidate.speaker is None:
            question('SPEAKER', citation)
        if state.expires_at is None:
            question('PROMISE_DATE', citation)
        # An unknown amount or an unbound extraction is not itself a payment link.
        linked = state.id is not None and any(link.commitment_stable_id == state.id for link in case.attributions)
        unassigned_credit = state.possible_credit_minor > state.credited_minor
        if state.id is not None and state.fulfillment_unresolved and (linked or unassigned_credit):
            question('ATTRIBUTION', citation)
        if any(i.code in {'AMBIGUOUS_REPLACEMENT', 'CONFLICTING_REPLACEMENTS'}
               and candidate.source.source_id in i.sources for i in commitment_facts.issues):
            question('SUPERSESSION', citation)
        promises.append(dict(span=citation, amount=amount, currency=currency, date=state.expires_at))
    for left, right in combinations(promises, 2):
        if left['amount'] is not None and right['amount'] is not None and left['currency'] == right['currency'] == 'INR' and left['amount'] != right['amount']:
            contradiction('PROMISED_AMOUNT', left['span'], right['span'])
            question('AMOUNT', left['span']); question('AMOUNT', right['span'])
        if left['date'] is not None and right['date'] is not None and left['date'] != right['date']:
            contradiction('PROMISE_TIMING', left['span'], right['span'])
            question('PROMISE_DATE', left['span']); question('PROMISE_DATE', right['span'])

    def issues(values):
        unique = {}
        for issue in values:
            source_ids = sorted(set(issue.sources))
            refs = [dict(source_id=r['stable_source_id'], evidence_version_id=r['id'])
                    for r in packet['evidence'] if r['stable_source_id'] in source_ids]
            if set(source_ids) != {r['source_id'] for r in refs}:
                raise ValueError('Issue references evidence absent from snapshot')
            unique.setdefault((issue.code, tuple(source_ids)), dict(code=issue.code, detail=issue.detail,
                              sources=source_ids, source_versions=sorted(refs,key=lambda r:(r['source_id'],r['evidence_version_id']))))
        return [unique[key] for key in sorted(unique)]

    snapshot = dict(snapshot_id=packet['snapshot_id'], snapshot_hash=packet['snapshot_hash'])
    observations = [dict(**snapshot, subject='LEDGER', field='availability', value=str(case.ledger_availability), source=None),
                    dict(**snapshot, subject='LEDGER', field='complete', value=case.ledger_complete, source=None)]
    for record in packet['evidence']:
        ref = dict(source_id=record['stable_source_id'], evidence_version_id=record['id'])
        if record['availability'] != 'AVAILABLE':
            observations.append(dict(**snapshot, subject='SOURCE', field='availability', value=record['availability'], source=ref))
        if not record['original_content']:
            observations.append(dict(**snapshot, subject='SOURCE', field='content_present', value=False, source=ref))
    return dict(findings_version=FINDINGS_VERSION,
                contradictions=[contradictions[key] for key in sorted(contradictions)],
                unresolved_questions=[questions[key] for key in sorted(questions)],
                financial_issues=issues(recommendation.financial.issues),
                commitment_issues=issues(commitment_facts.issues), evidence_observations=observations)
