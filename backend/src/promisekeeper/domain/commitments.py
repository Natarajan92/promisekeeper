"""Promise credit and claims; implementation follows reconciliation tests."""

from dataclasses import dataclass, replace
from datetime import datetime
from uuid import UUID
import re

from promisekeeper.domain.dates import IST, deadline, source_day
from promisekeeper.domain.evidence import Availability, Issue, require_same_case
from promisekeeper.domain.money import parse_money
from promisekeeper.domain.quoted_money import uploaded_money,quoted_currency,quoted_currency_token,quoted_amount_token


def _whole_token(token, text):
    # A terminal sentence period is punctuation; dots inside references are not.
    return token is None or re.search(
        r"(?<![\w/:+.\-])" + re.escape(token) + r"(?![\w/:+\-]|\.\w)", text) is not None


def _has_stated_date(text):
    return re.search(r"\b(?:today|tomorrow|[0-9]{1,2} [A-Za-z]+ [0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})\b",
                     text, re.I) is not None


@dataclass(frozen=True, slots=True)
class CommitmentState:
    id: UUID | None
    source_id: str
    commitment_key: str | None
    amount_minor: int | None
    expires_at: datetime | None
    fulfilled: bool
    fulfillment_unresolved: bool
    credited_minor: int
    superseded: bool = False
    possible_credit_minor: int = 0


@dataclass(frozen=True, slots=True)
class ClaimState:
    source_id: str
    resolved: bool
    customer_clarification: bool


@dataclass(frozen=True, slots=True)
class CommitmentFacts:
    commitments: tuple[CommitmentState, ...]
    claims: tuple[ClaimState, ...]
    issues: tuple[Issue, ...]


def reconcile_commitments(case, extraction, financial):
    messages = {message.source.id: message for message in case.messages}
    issues = []
    covered = set()
    covered_anchors = set()

    def amount_supported(token, text):
        return token is None or re.search(r"(?<![0-9.,+\-])" + re.escape(token) + r"(?![0-9,]|\.[0-9])", text) is not None

    def issue(code, source_ids, detail):
        issues.append(Issue(code, tuple(source_ids), detail))

    def validate(candidate):
        require_same_case(case, candidate)
        original = messages.get(candidate.source.id)
        if original is None or original.source != candidate.source:
            raise ValueError("Candidate source is not the original snapshot record")
        if candidate.source.availability != Availability.AVAILABLE:
            raise ValueError("Candidate source is unavailable")
        if (type(candidate.start) is not int or type(candidate.end) is not int
                or not 0 <= candidate.start < candidate.end <= len(candidate.source.original_content)
                or candidate.source.original_content[candidate.start:candidate.end] != candidate.quote):
            raise ValueError("Candidate quote/span is unsupported")
        for token in (candidate.amount_text, candidate.currency_text):
            if token is not None and token not in candidate.quote:
                raise ValueError("Candidate token is unsupported by its quote")
        uploaded='-UPLOAD-CUSTOMER-' in candidate.source.source_id
        if not (amount_supported(candidate.amount_text, candidate.quote) or
                (uploaded and quoted_amount_token(candidate.currency_text,candidate.amount_text,candidate.quote))):
            raise ValueError("Candidate amount token is incomplete")
        uploaded='-UPLOAD-' in candidate.source.source_id
        if uploaded and '-UPLOAD-CUSTOMER-' not in candidate.source.source_id:
            raise ValueError('Uploaded sender role was not reviewed as customer')
        currency_ok=(_whole_token(candidate.currency_text,candidate.quote) or
            (uploaded and candidate.currency_text is not None and quoted_currency(candidate.currency_text)=='INR' and quoted_currency_token(candidate.currency_text,candidate.quote)))
        if not currency_ok:
            raise ValueError("Candidate currency token is incomplete")
        if candidate.speaker is not None and candidate.speaker not in {original.speaker, case.client}:
            raise ValueError("Candidate speaker is unsupported")
        covered.add(candidate.source.id)

    eligible = {payment.source.id: payment for payment in financial.eligible_payments}
    all_payments = {payment.source.id: payment for payment in case.payments}
    anchors = {anchor.id: anchor for anchor in case.anchors}
    aliases = dict(financial.payment_aliases)
    for anchor in case.anchors:
        require_same_case(case, anchor)
    credits = {}
    grouped_links = {}
    for link in case.attributions:
        require_same_case(case, link)
        if link.payment_version_id not in all_payments or link.commitment_stable_id not in anchors:
            raise ValueError("Attribution references foreign or missing evidence")
        canonical_id = aliases.get(link.payment_version_id, link.payment_version_id)
        grouped_links.setdefault(canonical_id, []).append(link)
    assigned = set()
    for payment_id, links in grouped_links.items():
        payment = eligible.get(payment_id)
        if payment is None:
            if payment_id in financial.reversed_payment_ids:
                continue
            issue("UNRESOLVED_ATTRIBUTION", (link.source.source_id for link in links), "The attributed payment is not eligible.")
            continue
        amount = parse_money(payment.amount_text, payment.currency_text).minor_units
        targets = {link.commitment_stable_id for link in links}
        valid = (len(targets) == 1 and all(link.source.authoritative and link.source.availability == Availability.AVAILABLE
                 and parse_money(link.attributed_amount_text, link.currency_text).minor_units == amount for link in links))
        if not valid:
            issue("CONFLICTING_ATTRIBUTION", (link.source.source_id for link in links), "Review conflicting or excessive promise credit.")
            continue
        target = next(iter(targets))
        credits[target] = credits.get(target, 0) + amount
        assigned.add(payment_id)
    unassigned = sum(parse_money(payment.amount_text, payment.currency_text).minor_units
                     for payment_id, payment in eligible.items() if payment_id not in assigned)

    commitments = []
    candidates = {}
    candidate_clauses = {}
    seen_anchors = set()
    for candidate in extraction.commitments:
        validate(candidate)
        matching = [anchor for anchor in case.anchors if anchor.evidence_version_id == candidate.source.id]
        for anchor in matching:
            require_same_case(case, anchor)
            if not 0 <= anchor.clause_start < anchor.clause_end <= len(candidate.source.original_content):
                raise ValueError("Catalogue anchor range is invalid")
        intersected = [anchor for anchor in matching if max(anchor.clause_start, candidate.start) < min(anchor.clause_end, candidate.end)]
        provided = next((anchor for anchor in matching if anchor.commitment_key == candidate.commitment_key), None)
        if candidate.commitment_key is not None and provided is None:
            raise ValueError("Unknown or foreign commitment key")
        anchor = provided if len(intersected) == 1 and provided == intersected[0] else None
        if provided is not None and provided not in intersected:
            raise ValueError("Commitment key is not supported by the cited clause")
        if len(intersected) != 1:
            issue("AMBIGUOUS_COMMITMENT", (candidate.source.source_id,), "Quote does not identify one commitment clause.")
        clause = candidate.source.original_content[intersected[0].clause_start:intersected[0].clause_end] if len(intersected) == 1 else candidate.quote
        candidate_clauses[id(candidate)] = clause
        if len(intersected) == 1:
            covered_anchors.add(intersected[0].id)
        for token in (candidate.amount_text, candidate.currency_text, candidate.date_text):
            if token is not None and (token not in candidate.quote or token not in clause):
                raise ValueError("Commitment token is unsupported by its anchored clause")
        if not (amount_supported(candidate.amount_text, clause) or
                ('-UPLOAD-CUSTOMER-' in candidate.source.source_id and quoted_amount_token(candidate.currency_text,candidate.amount_text,clause))):
            raise ValueError("Commitment amount token is incomplete")
        if not _whole_token(candidate.date_text, clause) or not _whole_token(candidate.date_text, candidate.quote):
            raise ValueError("Commitment date token is incomplete")
        if re.search(r"\bINR\s+[-+]?[0-9]", clause) and (candidate.amount_text is None or candidate.currency_text is None):
            issue("MISSING_EXTRACTION", (candidate.source.source_id,), "A stated promise amount/currency was not extracted.")
        if candidate.date_text is None and _has_stated_date(clause):
            issue("MISSING_EXTRACTION", (candidate.source.source_id,), "A stated promise date was not extracted.")
        if anchor and anchor.id in seen_anchors:
            raise ValueError("Duplicate commitment candidate for one anchor")
        if anchor:
            seen_anchors.add(anchor.id)
        money = uploaded_money(candidate)
        if candidate.amount_text is not None and money.error:
            issue("INVALID_PROMISE_AMOUNT", (candidate.source.source_id,), "Review the promised amount/currency.")
        expires = deadline(candidate.date_text, original_at=candidate.source.event_at,allow_weekday='-UPLOAD-CUSTOMER-' in candidate.source.source_id).expires_at
        identity = anchor.id if anchor else None
        credit = credits.get(identity, 0)
        fulfilled = money.minor_units is not None and credit >= money.minor_units
        unresolved = not fulfilled and (money.minor_units is None or unassigned > 0 or identity is None)
        commitments.append(CommitmentState(identity, candidate.source.source_id, candidate.commitment_key,
                                            money.minor_units, expires, fulfilled, unresolved, credit,
                                            possible_credit_minor=credit + unassigned))
        candidates.setdefault(candidate.source.source_id, []).append(candidate)

    # Explicit replacement is supported by this bounded English catalogue's original wording.
    superseded = set()
    replacements = {}
    for candidate in extraction.commitments:
        target_id = candidate.explicitly_replaces_source_id
        if target_id is None:
            continue
        targets = candidates.get(target_id, [])
        if not re.match(r"^We explicitly replace our [0-9]{1,2} [A-Za-z]+ promise:", candidate_clauses[id(candidate)], re.I):
            raise ValueError("Replacement is not explicitly supported by the source")
        if len(targets) != 1:
            issue("AMBIGUOUS_REPLACEMENT", (candidate.source.source_id, target_id), "Replacement target is not unique.")
            continue
        target = targets[0]
        words = (target.date_text or "").split()
        if len(words) < 2 or " ".join(words[:2]).lower() not in candidate.quote.lower():
            raise ValueError("Replacement target date is unsupported by the source")
        superseded.add(target_id)
        replacements[candidate.source.source_id] = target_id
    for start in replacements:
        visited = set()
        cursor = start
        while cursor in replacements:
            if cursor in visited:
                issue("CONFLICTING_REPLACEMENTS", sorted(visited), "Explicit replacement references form a cycle.")
                superseded.clear()
                break
            visited.add(cursor)
            cursor = replacements[cursor]
    commitments = [replace(item, superseded=True) if item.source_id in superseded else item for item in commitments]

    claims = []
    for candidate in extraction.claims:
        validate(candidate)
        for token in (candidate.payment_date_text, candidate.transaction_reference_text):
            if not _whole_token(token, candidate.quote):
                raise ValueError("Claim token is unsupported by its quote")
        omitted_date = candidate.payment_date_text is None and _has_stated_date(candidate.source.original_content)
        if omitted_date:
            issue("MISSING_EXTRACTION", (candidate.source.source_id,), "A stated payment date was not extracted.")
        amount = uploaded_money(candidate).minor_units
        stated_day = source_day(candidate.payment_date_text, original_at=candidate.source.event_at)
        matching = [payment for payment in financial.eligible_payments
                    if candidate.transaction_reference_text is not None
                    and (payment.original_transaction_ref or payment.transaction_ref) == candidate.transaction_reference_text]
        resolved = False
        if matching and amount is not None:
            # Imported receipt pieces keep unique allocation identities, while their
            # original bank reference connects the claim to the confirmed pieces.
            compatible = len(matching)==1 or all(p.original_transaction_ref==candidate.transaction_reference_text for p in matching)
            actual_days={p.source.event_at.astimezone(candidate.source.event_at.tzinfo if candidate.source.event_at else IST).date()
                         if p.source.event_at else None for p in matching}
            compatible_day = not omitted_date and len(actual_days)==1 and (candidate.payment_date_text is None or
                              (stated_day is not None and stated_day in actual_days))
            paid=sum(parse_money(p.amount_text,p.currency_text).minor_units for p in matching)
            resolved = compatible and len({p.currency_text for p in matching})==1 and paid==amount and compatible_day
        claims.append(ClaimState(candidate.source.source_id, resolved, candidate.transaction_reference_text is None))
    for message in case.messages:
        require_same_case(case, message)
        if message.source.id not in covered:
            issue("MISSING_EXTRACTION", (message.source.source_id,), "A customer message was not extracted; review it before deciding.")
    for anchor in case.anchors:
        if anchor.id not in covered_anchors:
            source = messages.get(anchor.evidence_version_id)
            if source is None:
                raise ValueError("Anchor source is missing from the snapshot")
            issue("MISSING_EXTRACTION", (source.source.source_id,), "An anchored commitment clause was not extracted.")
    return CommitmentFacts(tuple(commitments), tuple(claims), tuple(issues))
