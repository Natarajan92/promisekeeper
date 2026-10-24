"""Pure correction selection, preserving the payment reconciler's historical decisions.

``active_records`` is the legacy financial selection, including invalid corrections.
Consumers establishing known facts must also exclude invalid/ambiguous identities.
Reversal metadata describes factual comparisons; settlement eligibility stays in payments.
"""
from dataclasses import dataclass
from uuid import UUID

from promisekeeper.domain.evidence import Availability, Issue, SourceKind, VerificationStatus
from promisekeeper.domain.money import parse_money


@dataclass(frozen=True, slots=True)
class LifecycleProjection:
    active_records: tuple
    issues: tuple[Issue, ...]
    invalid_ids: frozenset[UUID]
    ambiguous_ids: frozenset[UUID]
    superseded_ids: frozenset[UUID]
    reversal_ids: frozenset[UUID]
    reversed_ids: frozenset[UUID]


def project_records(records, *, payment=False):
    records = tuple(records)
    issues = []
    invalid = set()

    def issue(code, records, detail, *, unknown=False):
        issues.append(Issue(code, tuple(record.source.source_id for record in records), detail))
        if code in {"INVALID_CORRECTION", "CYCLIC_CORRECTION"}:
            invalid.update(record.source.id for record in records)

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
    active = tuple(record for record in records if record.source.id not in superseded | ambiguous
                 and not (payment and record.transaction_ref in ambiguous_refs))

    # Findings cannot promote a descendant of an invalid correction into a fact.
    while True:
        descendants = {record.source.id for record in records
                       if record.source.supersedes_version_id in invalid}
        if descendants <= invalid:
            break
        invalid.update(descendants)
    reversal_ids = {record.source.id for record in records
                    if payment and (record.reverses_payment_version_id is not None or record.source.kind == SourceKind.REVERSAL)}
    reversed_ids = _effective_reversed_ids(active, invalid | ambiguous, reversal_ids) if payment else set()
    return LifecycleProjection(active, tuple(issues), frozenset(invalid), frozenset(ambiguous),
                               frozenset(superseded), frozenset(reversal_ids), frozenset(reversed_ids))


def _effective_reversed_ids(active, excluded, reversal_ids):
    """A reversal pointer alone cannot erase a supported original fact.

    Match the financial reconciler's transaction equivalence and settlement
    prerequisites, additionally excluding invalid correction branches. This is
    factual comparison metadata only: the legacy financial selection and its
    issue/settlement processing remain unchanged.
    """
    groups = {}
    for record in active:
        if (record.source.id not in excluded and record.source.authoritative
                and record.source.availability == Availability.AVAILABLE and record.transaction_ref):
            groups.setdefault(record.transaction_ref, []).append(record)

    eligible = []
    aliases = {}
    for records in groups.values():
        # A same-reference conflict is not a duplicate alias and cannot establish
        # either a known reversal or a compatible original settlement.
        fingerprints = {(parse_money(record.amount_text, record.currency_text).minor_units, record.currency_text,
                         record.invoice_id, record.verification_status, record.settled,
                         record.source.event_at, record.reverses_payment_version_id) for record in records}
        if len(fingerprints) != 1:
            continue
        record = records[0]
        if (record.verification_status != VerificationStatus.VERIFIED or not record.settled
                or not record.invoice_id or parse_money(record.amount_text, record.currency_text).error):
            continue
        eligible.append(record)
        for alias in records:
            aliases[alias.source.id] = (record, records)

    reversed_ids = set()
    for reversal in eligible:
        target_group = aliases.get(reversal.reverses_payment_version_id)
        if target_group is None:
            continue
        target, aliases_of_target = target_group
        if (target.source.id not in reversal_ids and reversal.invoice_id == target.invoice_id
                and reversal.currency_text == target.currency_text
                and parse_money(reversal.amount_text, reversal.currency_text).minor_units
                == parse_money(target.amount_text, target.currency_text).minor_units):
            reversed_ids.update(alias.source.id for alias in aliases_of_target)
    return reversed_ids
