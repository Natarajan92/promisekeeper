"""Deterministic invoice settlement; implementation follows reconciliation tests."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from promisekeeper.domain.dates import deadline
from promisekeeper.domain.evidence import Availability, Issue, Payment, VerificationStatus, require_same_case
from promisekeeper.domain.money import parse_money


@dataclass(frozen=True, slots=True)
class FinancialFacts:
    invoice_minor: int | None
    paid_minor: int | None
    balance_minor: int | None
    due_at: datetime | None
    eligible_payments: tuple[Payment, ...]
    issues: tuple[Issue, ...]
    source_refs: tuple[str, ...]
    payment_aliases: tuple[tuple[UUID, UUID], ...] = ()
    reversed_payment_ids: tuple[UUID, ...] = ()


def reconcile_payments(case):
    issues = []
    complete = True

    def issue(code, records, detail, *, unknown=False):
        nonlocal complete
        issues.append(Issue(code, tuple(record.source.source_id for record in records), detail))
        if unknown:
            complete = False

    for record in (*case.invoices, *case.payments):
        require_same_case(case, record)
    ids = [record.source.id for record in (*case.invoices, *case.payments)]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate evidence version")

    def active(records, payment=False):
        by_id = {record.source.id: record for record in records}
        superseded = set()
        successors = {}
        for record in records:
            target = record.source.supersedes_version_id
            if target is None:
                continue
            valid = (target in by_id and record.source.authoritative
                     and record.source.availability == Availability.AVAILABLE
                     and record.invoice_id == by_id[target].invoice_id
                     and parse_money(record.amount_text, record.currency_text).error is None)
            if payment:
                valid = valid and record.verification_status == VerificationStatus.VERIFIED and record.settled
            if not valid:
                issue("INVALID_CORRECTION", (record,), "Review the explicit authoritative correction.", unknown=True)
                continue
            visited = {record.source.id}
            cursor = target
            while cursor in by_id and cursor is not None:
                if cursor in visited:
                    issue("CYCLIC_CORRECTION", (record,), "Correction references form a cycle.", unknown=True)
                    break
                visited.add(cursor)
                cursor = by_id[cursor].source.supersedes_version_id
            else:
                superseded.add(target)
                successors.setdefault(target, []).append(record)
        ambiguous = set()
        for target, corrections in successors.items():
            if len(corrections) > 1:
                issue("CONFLICTING_CORRECTIONS", (by_id[target], *corrections),
                      "Competing successors do not establish independent settlements.", unknown=True)
                ambiguous.update(record.source.id for record in corrections)
        # A descendant cannot silently select one side of an unresolved fork.
        while True:
            descendants = {record.source.id for record in records
                           if record.source.supersedes_version_id in ambiguous}
            if descendants <= ambiguous:
                break
            ambiguous.update(descendants)
        ambiguous_refs = {record.transaction_ref for record in records
                          if payment and record.source.id in ambiguous}
        return tuple(record for record in records if record.source.id not in superseded | ambiguous
                     and not (payment and record.transaction_ref in ambiguous_refs))

    invoices = active(case.invoices)
    invoice_values = []
    for record in invoices:
        if not record.source.authoritative:
            issue("NON_AUTHORITATIVE_INVOICE", (record,), "Invoice authority requires review.")
            continue
        if record.source.availability != Availability.AVAILABLE:
            issue("INVOICE_UNAVAILABLE", (record,), "The invoice source is unavailable.", unknown=True)
            continue
        if record.invoice_id != case.invoice_id or record.client != case.client:
            issue("INVOICE_IDENTITY_CONFLICT", (record,), "Invoice identity conflicts with the case.", unknown=True)
            continue
        amount = parse_money(record.amount_text, record.currency_text)
        due = deadline(record.due_text, original_at=record.source.event_at)
        if amount.error:
            issue(amount.error, (record,), "Review the invoice amount/currency.", unknown=True)
        if due.error:
            issue("INVOICE_DATE_UNRESOLVED", (record,), "Review the invoice due date.")
        invoice_values.append((amount.minor_units, record.currency_text, due.expires_at))
    invoice_minor = due_at = None
    if not invoice_values:
        issue("MISSING_INVOICE_AUTHORITY", invoices, "An authoritative invoice is required.", unknown=True)
    elif len(set(invoice_values)) != 1:
        issue("CONFLICTING_INVOICES", invoices, "Preserve and review both invoice authorities.", unknown=True)
    else:
        invoice_minor, _, due_at = invoice_values[0]

    if case.ledger_availability != Availability.AVAILABLE:
        issue("LEDGER_UNAVAILABLE", case.payments, "Ledger retrieval is unavailable, not empty.", unknown=True)
    elif not case.ledger_complete:
        issue("LEDGER_INCOMPLETE", case.payments, "Ledger completeness is not established.", unknown=True)

    payments = active(case.payments, payment=True)
    groups = {}
    for payment in payments:
        if not payment.source.authoritative:
            issue("NON_AUTHORITATIVE_PAYMENT", (payment,), "This source cannot verify settlement.")
            continue
        if payment.source.availability != Availability.AVAILABLE:
            issue("PAYMENT_UNAVAILABLE", (payment,), "A required payment record is unavailable.", unknown=True)
            continue
        if not payment.transaction_ref:
            issue("MISSING_TRANSACTION_REFERENCE", (payment,), "A unique ledger reference is required.", unknown=True)
            continue
        if payment.suspected_duplicate_of is not None:
            issue("SUSPECTED_DUPLICATE", (payment,), "Different transaction IDs may describe one payment.", unknown=True)
        groups.setdefault(payment.transaction_ref, []).append(payment)

    unique = []
    aliases = {}
    for records in groups.values():
        fingerprints = {(parse_money(record.amount_text, record.currency_text).minor_units, record.currency_text,
                         record.invoice_id, record.verification_status, record.settled,
                         record.source.event_at, record.reverses_payment_version_id) for record in records}
        if len(fingerprints) != 1:
            issue("CONFLICTING_PAYMENTS", records, "The same transaction has conflicting financial facts.", unknown=True)
        else:
            unique.append(records[0])
            aliases.update({record.source.id: records[0].source.id for record in records})

    eligible = []
    reversals = []
    for payment in unique:
        if payment.verification_status != VerificationStatus.VERIFIED:
            issue("UNVERIFIED_PAYMENT", (payment,), "Designation alone does not establish verification.")
            continue
        if not payment.settled:
            issue("UNSETTLED_PAYMENT", (payment,), "The ledger record is not settled.")
            continue
        amount = parse_money(payment.amount_text, payment.currency_text)
        if amount.error:
            issue(amount.error, (payment,), "Review the payment amount/currency.", unknown=True)
            continue
        if payment.invoice_id != case.invoice_id:
            issue("UNALLOCATED_PAYMENT", (payment,), "An explicit allocation to this invoice is required.")
            continue
        if payment.reverses_payment_version_id is not None:
            reversals.append(payment)
        else:
            eligible.append(payment)
    by_id = {payment.source.id: payment for payment in eligible}
    reversed_ids = set()
    for reversal in reversals:
        target = by_id.get(aliases.get(reversal.reverses_payment_version_id, reversal.reverses_payment_version_id))
        if target is None or parse_money(target.amount_text, target.currency_text).minor_units != parse_money(reversal.amount_text, reversal.currency_text).minor_units:
            issue("UNMATCHED_REVERSAL", (reversal,), "The reversal requires its exact compatible original payment.", unknown=True)
        else:
            reversed_ids.add(target.source.id)
    eligible = tuple(payment for payment in eligible if payment.source.id not in reversed_ids)
    if case.ledger_availability != Availability.AVAILABLE or not case.ledger_complete:
        eligible = ()
    paid = sum(parse_money(payment.amount_text, payment.currency_text).minor_units for payment in eligible) if complete else None
    balance = invoice_minor - paid if invoice_minor is not None and paid is not None else None
    if balance is not None and balance < 0:
        issue("OVERPAYMENT", eligible, "A negative remainder requires review, not automatic closure.")
    references = tuple(sorted({record.source.source_id for record in (*case.invoices, *case.payments)}))
    return FinancialFacts(invoice_minor, paid, balance, due_at, eligible, tuple(issues), references,
                          tuple(sorted(aliases.items())), tuple(sorted(reversed_ids)))
