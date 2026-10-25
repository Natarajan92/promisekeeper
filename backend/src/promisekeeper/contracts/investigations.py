"""Strict candidate extraction and durable investigation views."""
from typing import Annotated, Literal
from pydantic import Field, model_validator
from promisekeeper.contracts.evidence import StrictInput
from promisekeeper.contracts.common import CaseCommand, Id, Instant, Hash
from promisekeeper.contracts.cases import FinancialView, FinancialIssue, MoneyView, SourceVersionRef

Action = Literal['FOLLOW_UP', 'WAIT', 'VERIFY_PAYMENT', 'CLOSE']
RAW_AMOUNT_DESCRIPTION='Preserve the stated raw amount token verbatim, including invalid or incomplete numeric text. A known usable INR amount has at most two fractional digits; invalid precision is unknown financial value, not a known amount disagreement. Null only if unstated.'
RAW_DATE_DESCRIPTION='Preserve the explicit raw temporal expression verbatim, even when vague or unresolvable (for example next week or later). An unresolved date may coexist with this raw text; deterministic deadline resolution remains unknown. Null only if no temporal expression is stated.'

class StartInvestigation(CaseCommand):
    retry_of: Id | None

class Span(StrictInput):
    evidence_version_id: str
    source_id: str
    start: Annotated[int, Field(ge=0)]
    end: Annotated[int, Field(ge=1)]
    quote: Annotated[str, Field(min_length=1, max_length=8000)]

class Commitment(StrictInput):
    candidate_id: str
    commitment_key: str | None
    source: Span
    speaker: str | None
    amount_text: str | None = Field(description=RAW_AMOUNT_DESCRIPTION)
    currency_text: str | None
    date_text: str | None = Field(description=RAW_DATE_DESCRIPTION)
    explicitly_replaces_source_id: str | None

class Claim(StrictInput):
    candidate_id: str
    source: Span
    speaker: str | None
    amount_text: str | None = Field(description=RAW_AMOUNT_DESCRIPTION)
    currency_text: str | None
    payment_date_text: str | None = Field(description=RAW_DATE_DESCRIPTION)
    transaction_reference_text: str | None

class Contradiction(StrictInput):
    kind: Literal['PROMISE_TIMING','PROMISED_AMOUNT','PAYMENT_CLAIM','INVOICE_FACT','OTHER_CANDIDATE'] = Field(description='Direct known disagreement: INVOICE_FACT compares active authoritative invoice records; PAYMENT_CLAIM compares a customer claim and active authoritative ledger with the exact same non-null transaction reference; OTHER_CANDIDATE compares active authoritative same-reference ledger records. A reversal is a later settlement lifecycle event, not itself a contradiction of an earlier payment claim; exclude reversal records and their reversed originals from active factual comparisons. No arithmetic-only, different-reference, formatting-equivalent or validly corrected conflicts; unknown values are not known disagreements.')
    sources: Annotated[list[Span], Field(min_length=2,max_length=8)]

class Unresolved(StrictInput):
    field: Literal['SPEAKER','AMOUNT','CURRENCY','PROMISE_DATE','PAYMENT_DATE','PAYMENT_REFERENCE','SUPERSESSION','ATTRIBUTION'] = Field(description='The exact cited candidate or typed financial source field must be missing, invalid or disputed; a case-wide financial limitation does not make a known source field unknown. ATTRIBUTION means a verified payment-to-anchored-commitment link, cited on that commitment message clause, never missing invoice allocation. Invalid monetary precision is an AMOUNT uncertainty, not known monetary disagreement. Preserve stated raw temporal text even for unresolved dates. Do not invent unknown values. Empty unresolved arrays are allowed when deterministic findings preserve the gaps.')
    sources: Annotated[list[Span], Field(min_length=1,max_length=8)]

class InvestigatorOutput(StrictInput):
    schema_version: Literal['1']
    snapshot_id: str
    commitments: Annotated[list[Commitment], Field(max_length=32)]
    payment_claims: Annotated[list[Claim], Field(max_length=32)]
    contradictions: Annotated[list[Contradiction], Field(max_length=32)]
    unresolved: Annotated[list[Unresolved], Field(max_length=32)]


class CandidateOnlyOutput(InvestigatorOutput):
    """Production candidate-only-1 profile; the structural v1 DTO stays readable."""
    contradictions: Annotated[list[Contradiction], Field(max_length=0, description='candidate-only-1 policy: always an empty array; findings are derived by deterministic code.')]
    unresolved: Annotated[list[Unresolved], Field(max_length=0, description='candidate-only-1 policy: always an empty array; questions are derived by deterministic code.')]

class CommitmentView(StrictInput):
    commitment_stable_id: Id | None
    commitment_key: str | None
    source_id: str
    evidence_version_id: Id
    amount: MoneyView | None
    expires_at: Instant | None
    fulfilled: bool
    fulfillment_unresolved: bool
    credited: MoneyView
    superseded: bool

class ClaimView(StrictInput):
    source_id: str
    evidence_version_id: Id
    resolved: bool
    customer_clarification: bool

class TimelineEntry(StrictInput):
    source_id: str
    evidence_version_id: Id
    event_at: Instant | None
    arrived_at: Instant
    kind: str
    undated: bool

class Explanation(StrictInput):
    text: str
    sources: list[str]

class LegacyResult(StrictInput):
    investigation_id: Id
    snapshot_id: Id
    snapshot_hash: Hash
    evaluation_at: Instant
    status: Literal['COMPLETE','LIMITED']
    financial_facts: FinancialView
    financial_label: Literal['VERIFIED_REMAINDER','RECORDED_REMAINDER','UNKNOWN_REMAINDER']
    commitments: list[CommitmentView]
    claims: list[ClaimView]
    timeline: list[TimelineEntry]
    contradictions: list[Contradiction]
    unresolved_questions: list[Unresolved]
    limitations: list[str]
    action: Action
    reason_code: str
    explanation: Explanation
    next_step: str
    review_at: Instant | None
    result_hash: Hash

    @model_validator(mode='after')
    def wait_boundary(self):
        if (self.action == 'WAIT') != (self.review_at is not None):
            raise ValueError('WAIT requires its review boundary')
        return self


class CommitmentIssue(FinancialIssue):
    source_versions: list[SourceVersionRef]


class DeterministicFinancialIssue(FinancialIssue):
    source_versions: list[SourceVersionRef]


class DeterministicFinancialView(FinancialView):
    issues: Annotated[list[DeterministicFinancialIssue], Field(max_length=512)]


class EvidenceObservation(StrictInput):
    subject: Literal['LEDGER', 'SOURCE']
    field: Literal['availability', 'complete', 'content_present']
    value: Literal['AVAILABLE', 'UNAVAILABLE', 'MISSING', 'UNREADABLE'] | bool
    snapshot_id: Id
    snapshot_hash: Hash
    source: SourceVersionRef | None

    @model_validator(mode='after')
    def consistent_observation(self):
        if (self.subject == 'LEDGER') != (self.source is None):
            raise ValueError('Ledger observations are source-less; source observations require a version')
        if self.field == 'availability':
            if type(self.value) is not str:
                raise ValueError('Availability requires an availability value')
            if self.subject == 'SOURCE' and self.value == 'AVAILABLE':
                raise ValueError('Available source metadata is not a review observation')
        elif type(self.value) is not bool:
            raise ValueError('Completeness and content presence require booleans')
        if self.field == 'complete' and self.subject != 'LEDGER':
            raise ValueError('Completeness belongs to the captured ledger lookup')
        if self.field == 'content_present' and (self.subject != 'SOURCE' or self.value is not False):
            raise ValueError('Content observations identify empty source records')
        return self


class Result(LegacyResult):
    findings_version: Literal['deterministic-1']
    financial_facts: DeterministicFinancialView
    contradictions: Annotated[list[Contradiction], Field(max_length=4096)]
    unresolved_questions: Annotated[list[Unresolved], Field(max_length=512)]
    commitment_issues: Annotated[list[CommitmentIssue], Field(max_length=512)]
    evidence_observations: Annotated[list[EvidenceObservation], Field(min_length=2, max_length=128)]

    @model_validator(mode='after')
    def findings_profile(self):
        if len(self.financial_facts.issues) > 512:
            raise ValueError('Too many financial issues')
        if any('source_versions' not in issue.model_fields_set for issue in self.financial_facts.issues):
            raise ValueError('Deterministic financial issues require exact source versions')
        known_versions = {(item.source_id, item.evidence_version_id) for item in self.timeline}
        def exact_reference(ref):
            if (ref.source_id, ref.evidence_version_id) not in known_versions:
                raise ValueError('Finding reference is absent from the retained timeline')
        for issue in [*self.financial_facts.issues, *self.commitment_issues]:
            if set(issue.sources) != {ref.source_id for ref in issue.source_versions}:
                raise ValueError('Every issue source requires its exact version')
            for ref in issue.source_versions:
                exact_reference(ref)
            if len({(ref.source_id,ref.evidence_version_id) for ref in issue.source_versions}) != len(issue.source_versions):
                raise ValueError('Duplicate issue source version')
        for items, kind in ((self.contradictions, 'kind'), (self.unresolved_questions, 'field'),
                            (self.financial_facts.issues, 'code'), (self.commitment_issues, 'code')):
            identities = set()
            for item in items:
                source_ids = item.sources if kind == 'code' else [s.source_id for s in item.sources]
                identity = (getattr(item, kind), tuple(sorted(source_ids)))
                if identity in identities:
                    raise ValueError('Duplicate deterministic finding')
                identities.add(identity)
                if kind != 'code':
                    if len(source_ids) != (2 if kind == 'kind' else 1) or len(set(source_ids)) != len(source_ids):
                        raise ValueError('Deterministic findings require a source pair or one question source')
                    for ref in item.sources:
                        exact_reference(ref)
        ledger_fields = []
        identities = set()
        for observation in self.evidence_observations:
            if (observation.snapshot_id, observation.snapshot_hash) != (self.snapshot_id, self.snapshot_hash):
                raise ValueError('Observation snapshot differs from result')
            identity = (observation.subject, observation.field,
                        observation.source.evidence_version_id if observation.source else None)
            if identity in identities:
                raise ValueError('Duplicate observation')
            identities.add(identity)
            if observation.source:
                exact_reference(observation.source)
            if observation.subject == 'LEDGER':
                ledger_fields.append(observation.field)
        if sorted(ledger_fields) != ['availability', 'complete']:
            raise ValueError('Both captured ledger observations are required')
        return self

class AgentActivityView(StrictInput):
    agent: Literal['INTAKE','EXTRACTOR','RULES_ENGINE','MEMORY','COMMUNICATOR','SAFETY_CHECK','TONE_REVIEWER','OWNER','SUPERVISOR','BRIEFING']
    event: str
    outcome: Literal['STARTED','SUCCEEDED','REVISE','FALLBACK','FAILED','WAITING','SKIPPED']
    note: str | None
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int | None
    at: Instant
    case_id: Id | None
    investigation_id: Id | None
    morning_review_id: str | None
    recipient: Literal['INTAKE','EXTRACTOR','RULES_ENGINE','MEMORY','COMMUNICATOR','SAFETY_CHECK','TONE_REVIEWER','OWNER','SUPERVISOR','BRIEFING'] | None = None
    message_kind: Literal['EVIDENCE_PACKET','PAYMENT_CANDIDATES','DECISION','CLIENT_HISTORY','NOTE_DRAFT','REVISION_REQUEST','DRAFT_FOR_APPROVAL','CASE_SELECTION','CASE_OUTCOME','BRIEFING'] | None = None

class AgentTotals(StrictInput):
    input_tokens: int
    output_tokens: int
    latency_ms: int
    cost_usd: float | None

class InvestigationView(StrictInput):
    schema_version: Literal['1']
    id: Id
    investigation_id: Id
    demonstration_id: Id
    case_id: Id
    status: Literal['RUNNING','COMPLETE','LIMITED','INCOMPLETE']
    snapshot_id: Id
    snapshot_hash: Hash
    evaluation_at: Instant
    deadline_at: Instant
    limitations: list[str]
    failure_code: str | None
    result: Result | LegacyResult | None
    action: Action | None
    draft_status: Literal['NONE','RUNNING','READY','FAILED']
    progress: list[dict]
    agent_activity: list[AgentActivityView] = []
    agent_totals: AgentTotals | None = None

    @model_validator(mode='after')
    def terminal_result(self):
        complete=self.status in {'COMPLETE','LIMITED'}
        if complete != (self.result is not None) or (not complete and self.action is not None):
            raise ValueError('Only completed attempts have an action and result')
        if complete and (self.action!=self.result.action or self.status!=self.result.status):
            raise ValueError('Attempt and result disagree')
        return self
