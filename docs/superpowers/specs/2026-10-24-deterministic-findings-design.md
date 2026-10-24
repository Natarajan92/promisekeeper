# Deterministic investigation findings

Status: approved by the owner on 24 October 2026 for the remaining Gate III work. This does not authorize Gate IV or qualify the current LIVE adapter.

An independent builder check found no important unanswered planning questions. The approved refinement is implemented and independently reviewed, with offline verification passed. Fresh LIVE qualification remains blocked by provider availability; see the Gate III report.

## Intent and evidence

Keep the single Investigator responsible for extracting what a customer actually said. Make code responsible for deciding which facts disagree, which fields remain unresolved and what evidence needs review.

The current architecture already assigns money, dates, payment authority and action selection to deterministic code. However, saved contradiction and unresolved-question arrays currently come directly from the model after source/span validation. Correct citations alone do not prove that a financial interpretation is supported.

The complete prompt-4 evaluation failed six quality checks. Later prompt refinements preserved raw vague-date wording and clarified precision, attribution and reversal semantics. The prompt-6 batch still produced a claim/ledger contradiction using a negative ledger amount despite an explicit nonnegative-amount rule. It was stopped at 95 of 153 planned attempts: 92 passed, two ended with bounded provider failures and one failed quality checks. Candidate facts, source validation and the deterministic action were correct in that failed result. All prior reports remain unchanged.

The responsibility change was recommended by Codex and approved by the owner. Implementation and fresh qualification remain required.

## Required behavior

Nebius extracts AVAILABLE MESSAGE commitments and payment claims, preserving raw speaker, amount, currency, temporal wording, transaction reference, replacement relationship, anchor identity and exact source span. A vague temporal phrase remains text even when its date cannot be resolved. Null never substitutes for a stated phrase, amount or reference.

The provider request constrains `contradictions` and `unresolved` to empty arrays. The existing extraction schema remains structurally compatible; a versioned extraction policy identifies this stricter request profile. Response validation rejects a policy violation rather than silently dropping model findings. STUB follows the same production policy. This is not an instruction to hide uncertainty in the product.

After validation and reconciliation, a production findings service derives the visible findings from the captured evidence, actual extracted candidates and deterministic domain results. It has no fixture, expected-answer or evaluator dependency. It runs before hashing and saving the immutable result.

## Findings and provenance

Retain the existing result `contradictions` and `unresolved_questions` arrays, but populate them deterministically:

- Direct disagreements require supported known facts and relevant source pairs: active invoice/invoice facts; exact-reference claim/ledger or ledger/ledger facts; and conflicting active, unfulfilled promises. Normalize supported number/date representations before comparison.
- Missing, invalid or disputed candidate/source values identify the exact affected field. Known source values do not become unknown because another record or the overall balance is uncertain.
- Invalid precision, negative numbers, unavailable records and unsupported values cannot establish a known monetary disagreement. Equivalent formatting, unrelated references, arithmetic-only differences and validly corrected facts do not establish contradictions.
- Reversal events and reversed originals are excluded from active factual comparisons. Settlement effects remain in the financial findings. Invoice allocation and payment-to-commitment attribution remain separate.
- Commitment attribution questions identify an actually unresolved payment link to an anchored commitment. Preserve supported supersession/binding issues and ambiguous replacement relationships.

Message findings use validated candidate spans. Available typed invoice/payment findings use exact, nonempty original-record spans. Every citation names the immutable evidence-version UUID and stable source ID with Unicode code-point offsets. Never manufacture a quotation for missing or unreadable content.

The current question enum cannot represent all domain issues. Add these bounded, typed result projections:

- Financial issues retain their code, detail and stable source IDs, with additional exact `source_versions` references for every cited retained record.
- `commitment_issues` retains code, detail and exact source-version references for every reconciliation issue, including COMPLETE results. Limitation codes or the selected reason alone are insufficient.
- `evidence_observations` records captured ledger availability/completeness and unavailable-source status. Each observation identifies its snapshot, field and captured value, plus the exact record version when one exists. A case-wide lookup observation is distinct from a missing amount on a source.

The UI displays these issues and observations, with direct exact-version source access. It retains issues that do not change an independently known balance. Findings explain the specific review needed, while preserving the existing action, financial certainty, timeline and previous-result behavior.

## Domain and compatibility constraints

Use one shared pure lifecycle projection for production correction/fork/cycle/reversal selection, extracted from the existing payment reconciliation logic if needed. This must preserve financial decisions. The independent evaluator must not use this production findings implementation.

Amounts, verified totals, balance, fulfillment, action, review time, mutation eligibility and retry policy do not change. Keep the owner-selected Nebius provider and explicit GLM candidate, the single execution slot, 20-second call deadline, 55-second overall budget, one persisted automatic retry per failed step, immutable snapshots and terminal fencing. There is no model fallback, repair loop or additional model.

New saved results carry an explicit findings-profile version, covered by their result hash. Existing saved JSON, hashes and history remain immutable and readable. The UI identifies an older profile as legacy and requests explicit reinvestigation; it must not present it as a result validated under the new profile. Do not silently rewrite or regenerate retained results. Additive read compatibility must preserve the exact stored representation rather than inserting new fields into an old hashed payload.

The builder may choose the precise internal helper boundaries, DTO names and storage mechanism for profile metadata. The behavior and provenance requirements above are fixed. Reuse the existing source viewer and layout; this is not a UI redesign or a new workflow.

## Independent acceptance evidence

Before further provider calls, define an evaluation-only expected finding inventory for every canonical manifest entry, using stable source IDs, finding kinds/fields, issue codes and observation values. These expectations are authored from the approved catalogue and reviewed independently; they are not generated by the production findings service and never enter the provider request.

Check soundness, completeness and duplicate findings separately. Independently validate all actual version IDs, source spans and observation snapshot references. Keep actual raw candidate facts, policy validation, derived findings, expected inventory and correctness checks separately labeled. Empty model arrays alone cannot count as evidence that product uncertainty is correct.

Required offline evidence includes all 51 manifest projections and synthetic positive/negative cases for invalid or missing fields, unrelated references, equivalent formats, partial payments, overpayment, duplicate/reversed payments, valid/invalid corrections, competing correction branches, unknown dates, conflicting promises, ambiguous binding/supersession, linked/unlinked fulfillment, unavailable/empty evidence and incomplete lookups. Assert unchanged financial/action outputs and immutable legacy-result compatibility. Add real API/SQLite and browser checks for the new visible issue/source paths.

Freeze the new extraction, findings, evaluator and criteria versions before a fresh canonical 51-entry, three-repetition LIVE evaluation. Retain every observed outcome. Every returned candidate and every material product finding must be correct, source-valid and complete; missing findings or fabricated facts block qualification. Preserve the existing actual-live-coverage, bounded-provider-failure, deadline and retry requirements. Preserve all earlier failed reports without regrading them.

Gate III remains unqualified until that evidence passes and the owner reviews the handoff. Drafts, approvals, closure, customer transmission, release performance trials and human usability acceptance remain outside this refinement.
