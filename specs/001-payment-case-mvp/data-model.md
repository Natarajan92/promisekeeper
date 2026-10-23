# Data Model and State Invariants

**Contract version**: 1 | **Authority**: [spec.md](spec.md), including all three accepted clarifications.

## Representation and identity

Use UUIDs for instances/operations and stable case-prefixed catalogue IDs for provenance. Source IDs are unique within each demonstration copy; foreign keys validate copy ownership. New copies seed exactly three cases and never reset existing history.

CommitmentAnchor is immutable catalogue metadata, not an extracted financial conclusion. Its unique identity is (demonstration_id, evidence_version_id, commitment_key); assign its instance ID once when materializing that catalogue source version. For example, PK-002-M1-C1 names the first approved commitment clause in PK-002-M1. Quote text, model candidate ID, extraction order and model-selected span offsets never enter this identity. A new source version gets a distinct anchor; an existing attribution cannot silently retarget it. Canonical clause ranges come from the versioned catalogue, not the model.

Demonstration selection is a browser preference (`selected_demonstration_id`), not a financial or case-state fact. The server's persisted nondeleted-copy list is authoritative. Restore a valid saved selection, otherwise select the sole copy, show a chooser for multiple copies, or require explicit creation for an empty list. Never seed or reset during listing, selection, reload or restart. Confirmed deletion clears that copy's local selection; pending operations remain scoped to their originating copy.

Preserve raw money text; normalize valid INR values to integer paise. Domain arithmetic uses Python integers; SQLite TEXT and JSON decimal strings preserve exact paise without floating-point coercion or overflow. Payments/invoices require nonnegative valid amounts with at most two decimals. Negative derived balances are overpayment anomalies; unknown/invalid/unavailable/conflicting differ from zero. Preserve invalid originals rather than discarding them.

Persist aware UTC RFC3339 instants plus original source timezone/date expressions. Date-only deadlines use Asia/Kolkata and exclusive next-day midnight. Event time, arrival time, evaluation time, and execution timeout are distinct. Unknown event times remain null. Registered reference-clock transitions cannot move backward within a retained copy; earlier-time replay requires a fresh copy.

## Entities

| Entity | Fields/relationships | Validation |
| --- | --- | --- |
| Demonstration | id, catalogue_version, created_at, clock_mode REFERENCE/REAL, reference_clock_event_id, selected_variant_id, deletion state | Only approved catalogue variants/events; no arbitrary evidence/time input. |
| PaymentCase | id, demonstration_id, catalogue_case_id, client identity, invoice_id, lifecycle OPEN/CLOSED, case_revision, evidence_revision, review_epoch, latest_completed_investigation_id, current_draft_version_id nullable, next_event_sequence | Monotonic revisions. Latest completed is not necessarily current; draft head changes atomically. |
| EvidenceVersion | id, case_id, stable_source_id, version, source type/provenance, original_content, event_at nullable, arrived_at, availability AVAILABLE/UNAVAILABLE/MISSING/UNREADABLE, supersedes_version_id nullable | Immutable. Corrections, reversals, explicit links and changed availability append versions and increment evidence_revision. |
| InvoiceProjection | evidence_version_id, invoice/client IDs, raw amount/currency/due date, normalized values or unresolved reasons, correction link | Designated authority only. Unsuperseded conflicts make required facts unknown. |
| PaymentProjection | evidence_version_id, transaction_ref, raw/normalized amount/currency, verification_status VERIFIED/UNVERIFIED/UNKNOWN, settled status, allocation_invoice_id nullable, authority designation, reversal/correction links | Eligibility requires verification_status=VERIFIED separately from authority designation, all verification fields, valid amount, same invoice/currency, settled/non-reversed state and availability. |
| CommitmentAnchor | id, demonstration_id, evidence_version_id, commitment_key, clause_start, clause_end | Immutable approved catalogue metadata. Unique copy/source-version/key; nonoverlapping commitment-clause ranges in each source. No amount, date, verification or fulfillment authority. |
| CommitmentAttribution | evidence_version_id, payment_version_id, commitment_stable_id, attributed_minor_units, source reference | Separate from invoice allocation. Approved catalogue uses a whole payment attributed to at most one commitment. Conflicting/excessive links require review. |
| Investigation | id, case_id, operation_id, retry_of nullable, started_at, evaluation_at, deadline_at, snapshot_id, status RUNNING/COMPLETE/LIMITED/INCOMPLETE, terminal_at, failure_code, agent_mode, requested/returned model, response_id, prompt/schema/adapter versions | Partial unique index: one RUNNING per case. Terminal attempts cannot accept late output. INCOMPLETE has no action. |
| EvidenceSnapshot | id, case_id, evidence_revision, ordered evidence_version_ids, commitment_anchor_ids, availability/authority/completeness observations, captured_at, hash | Immutable packet, including missing/unavailable states. A closed SQL transaction's snapshot alone is insufficient. |
| StepAttempt | investigation_id, step_name, invocation_number, invocation_kind INITIAL/AUTO_RETRY/MANUAL_RETRY, operation_id, started/ended_at, outcome, redacted failure_code | Unique investigation/step/invocation. At most one AUTO_RETRY per investigation/step across all executions; manual retry never resets that usage. Extraction has only INITIAL and optional AUTO_RETRY. |
| DraftGenerationAttempt | id, investigation_id, operation_id, retry_of nullable, expected_draft_head nullable, status RUNNING/READY/FAILED, started/deadline/terminal_at, failure_code | Independent of completed recommendation. Manual retry binds the failed step, original snapshot/result and expected head; it cannot overwrite an owner edit or superseding result. |
| InvestigationResult | investigation_id, commitments/claims, timeline refs, contradictions, unresolved facts, financial facts, action, reason_code, explanation/source refs, review_at nullable, rule_version | COMPLETE/LIMITED has one allowed action. Deterministic normalized facts; explicit limitations. |
| DraftVersion | id, case_id, investigation_id, parent_version_id nullable, recipient, invoice_id, exact_text, version, payload_hash, created_at, validation status/reasons | Immutable edits. Every changed text/recipient creates an unapproved version; no financial authority. |
| DraftReview | id, operation_id, draft_version_id, owner_actor, APPROVE/REJECT, decided_at, exact payload/recipient/invoice, investigation_id, evidence_revision, review_epoch | Append-only. Current approval derives from version/epoch/eligibility. No SENT state. |
| OwnerDisposition | id, operation_id, case_id, investigation_id, ACCEPT/REJECT, optional reason, decided_at | Separate from finance, draft approval and closure. |
| CaseEvent | case_id, sequence, event_type, operation_id, referenced IDs/payload hash, occurred_at | Append-only arrival/start/end/review/invalidation/decision/closure/reopening/failure history. |
| OperationReceipt | demonstration_id, operation_id, operation_type, canonical_request_hash, target_id, status/outcome, committed_at | Unique durable ID; same request replays, different request conflicts. Content-free deletion receipt survives deletion. |

Invoice/payment normalization is reproducible projection, not mutation of originals. Extracted commitments/claims belong to a saved result and are not independently editable authoritative records. A commitment's commitment_stable_id references its CommitmentAnchor.id, with copy/source-version ownership enforced; quote spans remain separate provenance. CommitmentAttribution references that same anchor through a foreign key, never a model-selected quote or a message-only link.

## Commitments and claims

A commitment retains commitment_stable_id, commitment_key, speaker, original span/source, stated amount/currency or null, raw/normalized deadline or unknown reason, explicit replacement references, attributed payments and derived fulfillment. Validate the candidate key against snapshot anchors and bind only when its quote intersects exactly one commitment clause and every nonnull amount/currency/date token is supported within both that clause and the quote. Speaker identity may use the original source's author metadata; explicit replacement references require supported source relationships. A null key or ambiguous clause binding leaves identity unresolved, never inferred from amount/date similarity. A provided unknown or foreign key fails validation. Explicit replacement links must resolve to exact anchored identities; ambiguous message-only replacement references stay unresolved. Recency alone never supersedes a promise. An unknown promised amount cannot be declared fulfilled.

Eligible explicit attributions reaching the stated same-currency amount derive fulfillment; reversals/corrections rederive it. A missing link can leave fulfillment unresolved while balance remains known. If it changes action, use VERIFY_PAYMENT. FV-16 linked: INR 30,000.00/FOLLOW_UP; unlinked: the same known remainder/VERIFY_PAYMENT. Do not demand the original promise amount after partial settlement.

A claim retains its source, stated amount/date/reference or null, explicit matching evidence and unresolved reasons. Receipts/screenshots/customer wording cannot verify payment. Matching uses eligible designated ledger evidence, explicit references/allocation and compatible facts; partial/conflicting matches remain unresolved for the uncovered amount. No guessed matching.

## Financial/time invariants

1. Balance equals invoice authority minus eligible allocations. Identical transaction duplicates count once; conflicting copies and suspected different-ID duplicates require review. A failed lookup is not an empty complete ledger.
2. Exact zero/no material conflict permits a CLOSE recommendation only. Negative remainder requires VERIFY_PAYMENT. A disputed positive remainder cannot become a demand.
3. Apply VERIFY_PAYMENT, CLOSE, WAIT, FOLLOW_UP in that order. Fulfilled partial promises do not justify WAIT. Unknown/conflicting material timing requires verification.
4. A 25 October date-only promise expires exactly at 26 October 00:00 IST. Relative dates require original aware timestamp and unambiguous deterministic interpretation.
5. Timeline: event time, then stable source ID for ties; separate undated group. Show arrival/audit chronology separately.
6. WAIT review_at is the minimum future invoice-due boundary or expiry of an active, unfulfilled promise justifying waiting, using the result's business clock. Exclude expired/fulfilled/superseded promises. At equality the prior result requires review; reinvestigation may still WAIT on the remaining condition. FV-18 requires 25 October 00:00 then 27 October 00:00 IST in both branches, then FOLLOW_UP at the latter boundary.

## Transitions and transactions

**Start**: Check for an existing receipt before capacity rejection. Reserve the single process-wide Investigator slot; if unavailable, recheck for a concurrently committed matching receipt before returning busy. In BEGIN IMMEDIATE, recheck receipt/revision and OPEN lifecycle, then capture sources/evaluation, insert RUNNING, increment review_epoch/case_revision and append start/invalidation/receipt; commit then execute. Release reservation on rollback, receipt replay, or terminal outcome. Never call the model in a transaction. Another case cannot persist RUNNING before acquiring the slot; the per-case unique index additionally guards duplicate starts.

**Complete**: RUNNING -> COMPLETE/LIMITED/INCOMPLETE. Fence writes by attempt ID/state/deadline. Old evidence scope can be saved as historical, never silently current. Draft status READY/FAILED/NOT_NEEDED is independent; draft failure cannot erase a saved recommendation.

**Evidence arrival**: A read-only case/event preview binds catalogue version, demonstration/case/event IDs, expected_case_revision, exact evidence changes and any clock change into its hash. The confirmation command rechecks that preview and revision in the same transaction as immutable evidence/anchor arrival, evidence_revision/case_revision increments, freshness/approval invalidation, events and receipt. Replay a known operation before revision/hash checks. A closed case stays CLOSED with review_required until explicitly reopened. Fixture authority is defined by the catalogue, not the confirmation click. The shared preview/confirmation path is available in Gate II; Gate IV integrates lifecycle UI/closed-case journeys without replacing it.

**Draft edit/review**: Editing requires the current parent/head and appends a version, advances current_draft_version_id, increments case_revision/review_epoch, and records invalidation/edit/receipt atomically. Approval requires that current head, exact payload/target, latest completed result, current evidence/time, current epoch, no running investigation, and deterministic validation in the same transaction as review/event/receipt. A newer edit permanently blocks approval of the older version. Historical rejection remains auditable; historical approval is prohibited. Saving wording never changes finance.

**Draft failure/retry**: A failed draft step leaves its completed result intact. An explicit draft-retry operation creates DraftGenerationAttempt bound to the failed attempt, original result/snapshot and expected current head (normally null). It gets a new execution deadline of at most 55 seconds but preserves the investigation/step's automatic-retry usage. Fence completion by attempt state/deadline, unchanged head, current evidence/result and review_epoch; do not overwrite edits or stale results. Restart marks a running draft attempt FAILED without changing the completed investigation. A new successful result clears the old current head until its own draft is saved, or leaves it null when no draft is needed.

**Failed rerun**: Start already invalidated approval through review_epoch. INCOMPLETE never reverses that change. Fresh explicit approval may use the old draft with the new epoch if its result is still latest completed/current and all checks pass. New evidence or a successful superseding result blocks it. FV-17 governs.

**Close/reopen**: Explicit eligible current CLOSE confirmation atomically writes CLOSED/event/receipt. Block stale, superseded, incomplete, nonzero, conflicting or currently running cases. Reopen is a separate explicit command; preserve closure history. Accepting advice alone changes neither lifecycle nor facts.

**Restart**: Acquire exclusive process ownership before commands/recovery. Mark prior-process RUNNING attempts INCOMPLETE; preserve committed results/reviews/epochs/step counts. No silent replay or reseeding, and no late old-process output.

**Delete**: Explicit confirmation of selected demonstration ID/hash purges its owned content, preserves other copies, and retains only a content-free tombstone/receipt.

## Concurrency, freshness and diagnostics

Use short per-operation connections, parameterized SQL, explicit transaction control, foreign keys on every connection, and optimistic case_revision checks. Receipts and mutations commit together. Unknown HTTP outcomes reconcile through operation ID before a new submission ID is generated.

Freshness derives at read/command time from evidence_revision, latest completed result, timing conditions and running attempts. Preserve original evaluation_at. A read may flag expired WAIT without starting investigation/contact. Current approval additionally requires matching review_epoch; failed reruns cannot restore it.

Backend deadline is 55 seconds; calls at most 20 seconds, SDK retries disabled. Browser polling/watchdog displays incomplete connectivity by 60 seconds if the server is unreachable; restart records the interruption. Persist redacted IDs, durations, attempts, reason codes and schema/model versions. Never persist credentials/authorization headers in diagnostics.
