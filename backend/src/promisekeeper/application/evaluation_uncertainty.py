"""Independent typed evidence checks for reported extraction uncertainties.

These checks score what was reported; an extractor need not repeat deterministic
financial findings. Unknown values never establish a factual contradiction.
"""
from itertools import combinations

from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.domain.dates import IST, deadline, source_day
from promisekeeper.domain.money import parse_money
from promisekeeper.domain.recommendations import recommend


def _amount(raw):
    # Numeric validity is independent of whether the application supports a currency.
    return parse_money(raw, 'INR').minor_units


def _currency(raw):
    return raw.strip().upper() if isinstance(raw, str) and raw.strip() else None


def _active(records, *, payment=False):
    """Conservatively discard superseded, invalid and ambiguous corrections."""
    by_id={r.source.id:r for r in records};superseded=set();invalid=set();successors={}
    for record in records:
        target=record.source.supersedes_version_id
        if target is None:continue
        valid=(target in by_id and record.source.authoritative and record.source.availability=='AVAILABLE'
               and record.invoice_id==by_id[target].invoice_id
               and parse_money(record.amount_text,record.currency_text).error is None)
        if payment:valid=valid and record.verification_status=='VERIFIED' and record.settled
        visited={record.source.id};cursor=target
        while cursor in by_id:
            if cursor in visited:valid=False;break
            visited.add(cursor);cursor=by_id[cursor].source.supersedes_version_id
        if not valid:invalid.add(record.source.id);continue
        superseded.add(target);successors.setdefault(target,[]).append(record.source.id)
    ambiguous={sid for ids in successors.values() if len(ids)>1 for sid in ids}
    while True:
        descendants={r.source.id for r in records if r.source.supersedes_version_id in ambiguous|invalid}
        if descendants <= ambiguous|invalid:break
        ambiguous.update(descendants)
    ambiguous_refs={r.transaction_ref for r in records if payment and r.source.id in ambiguous}
    return [r for r in records if r.source.id not in superseded|ambiguous|invalid
            and r.source.authoritative and r.source.availability=='AVAILABLE'
            and not (payment and r.transaction_ref in ambiguous_refs)]


def _differences(left,right):
    """Both dictionaries contain normalized, known values or None."""
    return {field for field,value in left.items() if value is not None
            and right.get(field) is not None and value!=right[field]}


def uncertainty_correct(output,oracle,evaluation_at):
    extraction=oracle.extraction
    nullable={key:set() for key in ('SPEAKER','AMOUNT','CURRENCY','PROMISE_DATE','PAYMENT_DATE','PAYMENT_REFERENCE','SUPERSESSION','ATTRIBUTION')}
    for c in (*extraction.commitments,*extraction.claims):
        sid=c.source.source_id
        if c.speaker is None:nullable['SPEAKER'].add(sid)
        if _amount(c.amount_text) is None:nullable['AMOUNT'].add(sid)
        if _currency(c.currency_text)!='INR':nullable['CURRENCY'].add(sid)
    for c in extraction.commitments:
        if deadline(c.date_text,original_at=c.source.event_at).expires_at is None:nullable['PROMISE_DATE'].add(c.source.source_id)
    for c in extraction.claims:
        if source_day(c.payment_date_text,original_at=c.source.event_at) is None:nullable['PAYMENT_DATE'].add(c.source.source_id)
        if not c.transaction_reference_text:nullable['PAYMENT_REFERENCE'].add(c.source.source_id)
    state=recommend(oracle.evidence,extraction,evaluation_at)
    nullable['ATTRIBUTION']={c.source_id for c in state.commitments if c.fulfillment_unresolved and not c.fulfilled}
    findings=reconcile_commitments(oracle.evidence,extraction,state.financial)
    for issue in findings.issues:
        if issue.code in {'AMBIGUOUS_REPLACEMENT','CONFLICTING_REPLACEMENTS'}:nullable['SUPERSESSION'].update(issue.sources)

    case=oracle.evidence
    invoices=[i for i in _active(case.invoices) if i.invoice_id==case.invoice_id and i.client==case.client]
    payments=[p for p in _active(case.payments,payment=True) if p.invoice_id==case.invoice_id]
    reversed_ids=set(state.financial.reversed_payment_ids)
    payments=[p for p in payments if p.source.id not in reversed_ids and p.reverses_payment_version_id is None]
    for record in (*invoices,*payments):
        sid=record.source.source_id
        if _amount(record.amount_text) is None:nullable['AMOUNT'].add(sid)
        if _currency(record.currency_text)!='INR':nullable['CURRENCY'].add(sid)
    for payment in payments:
        if payment.source.event_at is None:nullable['PAYMENT_DATE'].add(payment.source.source_id)
        if not payment.transaction_ref:nullable['PAYMENT_REFERENCE'].add(payment.source.source_id)

    supported={kind:[] for kind in ('PAYMENT_CLAIM','INVOICE_FACT','OTHER_CANDIDATE','PROMISE_TIMING','PROMISED_AMOUNT')}
    def register(kind,left,right,differences):
        if not differences:return
        refs=frozenset((left.source.source_id,right.source.source_id))
        supported[kind].append(refs)
        for field in differences:
            if field in nullable:nullable[field].update(refs)
    def money(record):return dict(AMOUNT=_amount(record.amount_text),CURRENCY=_currency(record.currency_text))
    for claim in extraction.claims:
        for payment in payments:
            if not claim.transaction_reference_text or claim.transaction_reference_text!=payment.transaction_ref:continue
            zone=claim.source.event_at.tzinfo if claim.source.event_at else IST
            left=dict(**money(claim),PAYMENT_DATE=source_day(claim.payment_date_text,original_at=claim.source.event_at))
            right=dict(**money(payment),PAYMENT_DATE=payment.source.event_at.astimezone(zone).date() if payment.source.event_at else None)
            register('PAYMENT_CLAIM',claim,payment,_differences(left,right))
    for left,right in combinations(payments,2):
        if not left.transaction_ref or left.transaction_ref!=right.transaction_ref:continue
        fields=_differences(dict(**money(left),PAYMENT_DATE=left.source.event_at),dict(**money(right),PAYMENT_DATE=right.source.event_at))
        register('OTHER_CANDIDATE',left,right,fields)
    for left,right in combinations(invoices,2):
        fields=_differences(dict(**money(left),DUE=deadline(left.due_text,original_at=left.source.event_at).expires_at),
                            dict(**money(right),DUE=deadline(right.due_text,original_at=right.source.event_at).expires_at))
        register('INVOICE_FACT',left,right,fields)
    active={c.source_id for c in state.commitments if not c.superseded and not c.fulfilled}
    commitments=[c for c in extraction.commitments if c.source.source_id in active]
    for left,right in combinations(commitments,2):
        register('PROMISED_AMOUNT',left,right,_differences(money(left),money(right)) & {'AMOUNT'})
        dates=_differences({'PROMISE_DATE':deadline(left.date_text,original_at=left.source.event_at).expires_at},
                           {'PROMISE_DATE':deadline(right.date_text,original_at=right.source.event_at).expires_at})
        register('PROMISE_TIMING',left,right,dates)
    for question in output.unresolved:
        if not {s.source_id for s in question.sources} <= nullable[question.field]:return False
    for contradiction in output.contradictions:
        refs={s.source_id for s in contradiction.sources}
        # Every cited source must participate in a proven direct disagreement.
        pairs=[pair for pair in supported[contradiction.kind] if pair<=refs]
        if len(refs)<2 or not pairs or set().union(*pairs)!=refs:return False
    return True
