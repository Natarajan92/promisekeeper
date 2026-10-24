export type ClockMode = 'REFERENCE' | 'REAL';
export type Action = 'FOLLOW_UP' | 'WAIT' | 'VERIFY_PAYMENT' | 'CLOSE';
export type Status = 'RUNNING' | 'COMPLETE' | 'LIMITED' | 'INCOMPLETE';
export interface Demonstration {id:string; catalogue_version:string; created_at:string; clock_mode:ClockMode; selected_variant_id:string|null}
export interface Money {currency:'INR'; minor_units:string}
export interface SourceVersionRef {source_id:string;evidence_version_id:string}
export interface FinancialIssue {code:string;sources:string[];detail:string;source_versions?:SourceVersionRef[]}
export interface DeterministicIssue extends FinancialIssue {source_versions:SourceVersionRef[]}
export interface FinancialFacts {certainty:'KNOWN'|'UNKNOWN'; invoice:Money|null; paid:Money|null; balance:Money|null; due_at:string|null; issues:FinancialIssue[]; label?:string}
export type EvidenceAvailability = 'AVAILABLE'|'UNAVAILABLE'|'MISSING'|'UNREADABLE';
export interface Evidence {schema_version:'1'; id:string; demonstration_id:string; case_id:string;stable_source_id:string;version:number;kind:'INVOICE'|'LEDGER'|'MESSAGE'|'REVERSAL'|'ATTRIBUTION';original_content:string;event_at:string|null;arrived_at:string;availability:'AVAILABLE'|'UNAVAILABLE'|'MISSING'|'UNREADABLE';authoritative:boolean;supersedes_version_id:string|null;data:Record<string,string|boolean|null>;commitment_anchors:{id:string;evidence_version_id:string;commitment_key:string;clause_start:number;clause_end:number}[]}
export interface CaseSummary {id:string;catalogue_case_id:string;client:string;invoice_id:string;currency:string|null;due_text?:string|null;due_at:string|null;lifecycle:'OPEN'|'CLOSED';case_revision:number;has_previous_investigation:boolean;review_required:boolean;balance:Money|null;balance_label:'VERIFIED_REMAINDER'|'RECORDED_REMAINDER'|'UNKNOWN_REMAINDER';recommended_action:Action|null;review_at:string|null}
export interface CaseListResponse {schema_version:'1';demonstration_id:string;clock_mode:ClockMode;evaluation_at:string;cases:CaseSummary[]}
export interface SourceRef extends SourceVersionRef {quote:string;start:number;end:number}
export interface Commitment {commitment_stable_id:string|null;commitment_key:string|null;source_id:string;evidence_version_id:string;amount:Money|null;expires_at:string|null;fulfilled:boolean;fulfillment_unresolved:boolean;credited:Money;superseded:boolean}
export interface Claim {source_id:string;evidence_version_id:string;resolved:boolean;customer_clarification:boolean}
export interface TimelineEntry {source_id:string;evidence_version_id:string;event_at:string|null;arrived_at:string;kind:string;undated:boolean}
export interface LegacyResult {investigation_id:string;snapshot_id:string;snapshot_hash:string;evaluation_at:string;status:'COMPLETE'|'LIMITED';financial_facts:FinancialFacts;financial_label:'VERIFIED_REMAINDER'|'RECORDED_REMAINDER'|'UNKNOWN_REMAINDER';commitments:Commitment[];claims:Claim[];timeline:TimelineEntry[];contradictions:{kind:string;sources:SourceRef[]}[];unresolved_questions:{field:string;sources:SourceRef[]}[];limitations:string[];action:Action;reason_code:string;explanation:{text:string;sources:string[]};next_step:string;review_at:string|null;result_hash:string;findings_version?:never;commitment_issues?:never;evidence_observations?:never}
export type EvidenceObservation = {snapshot_id:string;snapshot_hash:string} & (
  {subject:'LEDGER';source:null} & ({field:'availability';value:EvidenceAvailability}|{field:'complete';value:boolean}) |
  {subject:'SOURCE';source:SourceVersionRef} & ({field:'availability';value:Exclude<EvidenceAvailability,'AVAILABLE'>}|{field:'content_present';value:false})
);
export interface DeterministicResult extends Omit<LegacyResult,'findings_version'|'commitment_issues'|'evidence_observations'|'financial_facts'> {
  findings_version:'deterministic-1';
  financial_facts:Omit<FinancialFacts,'issues'> & {issues:DeterministicIssue[]};
  commitment_issues:DeterministicIssue[];
  evidence_observations:EvidenceObservation[];
}
export type Result = LegacyResult | DeterministicResult;
export interface CaseView {schema_version:'1';id:string;demonstration_id:string;catalogue_case_id:string;client:string;invoice_id:string;lifecycle:'OPEN'|'CLOSED';case_revision:number;evidence_revision:number;review_epoch:number;current_draft_version_id:string|null;clock_mode:ClockMode;evaluation_at:string;ledger_availability:string;ledger_complete:boolean;evidence:Evidence[];financial_facts:FinancialFacts;latest_completed_result:Result|null;current_result:Result|null;running_attempt:string|null;freshness:string;review_required:boolean;review_required_reasons:string[];allowed_commands:Record<string,{allowed:boolean;blocking_reasons:string[]}>}
export interface ReceiptResponse {schema_version:'1';receipt:{operation_id:string;operation_type:string;target_id:string;committed_at:string;outcome:string;case_revision:number|null};demonstration_id?:string|null;investigation_id?:string|null;snapshot_id?:string|null;evaluation_at?:string|null;deadline_at?:string|null}
export interface Attempt {schema_version:'1';id:string;investigation_id:string;demonstration_id:string;case_id:string;status:Status;snapshot_id:string;snapshot_hash:string;evaluation_at:string;deadline_at:string;limitations:string[];failure_code:string|null;result:Result|null;action:Action|null;draft_status:string;progress:Record<string,unknown>[]}
export interface HistoryEvent {id:string;demonstration_id:string;case_id:string;sequence:number;event_type:string;operation_id:string|null;payload:Record<string,unknown>;occurred_at:string}
export interface CatalogueEvent {id:string;kind:'EVIDENCE'|'CLOCK';case_id:string;evaluation_at:string;eligible_variant_ids:(string|null)[]}
export interface ScenarioPreview {schema_version:'1';catalogue_version:string;demonstration_id:string;case_id:string;event_id:string;expected_case_revision:number;evidence_changes:Evidence[];clock_change:{from:string;to:string}|null;preview_hash:string}
export interface Catalogue {schema_version:'1';catalogue_version:string;variant_ids:string[];baseline_case_ids:string[];events?:CatalogueEvent[]}
export interface Health {schema_version:'1';ready:boolean;agent_mode:'STUB'|'LIVE';catalogue_version:string;configuration?:{model:string;capability_available:boolean}}
export interface DraftVersion {id:string;demonstration_id:string;case_id:string;investigation_id:string;parent_version_id:string|null;recipient:string;invoice_id:string;exact_text:string;version:number;payload_hash:string;created_at:string;validation_status:'VALID'|'INVALID';validation_reasons:string[];evidence_revision?:number}
export interface DraftReviewRecord {id:string;draft_version_id:string;decision:'APPROVE'|'REJECT';decided_at:string;recipient:string;invoice_id:string;exact_text:string;payload_hash:string;review_epoch:number;investigation_id:string}
export interface DraftGenerationAttempt {id:string;demonstration_id:string;case_id:string;investigation_id:string;status:'RUNNING'|'READY'|'FAILED';draft_version_id?:string|null;failure_code:string|null;deadline_at:string;expected_draft_head:string|null}
export interface CaseView {draft?:DraftVersion|null;draft_reviews?:DraftReviewRecord[];draft_generation_attempt?:DraftGenerationAttempt|null;no_draft_reason?:string|null;draft_state?:string;review_state?:string;draft_generation_state?:string}
export interface OwnerDisposition {id:string;demonstration_id:string;case_id:string;operation_id:string;investigation_id:string;decision:'ACCEPT'|'REJECT';reason:string|null;decided_at:string}
export interface CaseView {owner_dispositions?:OwnerDisposition[]}
