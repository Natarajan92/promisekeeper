# Gate III live qualification criteria

Criteria version: `gate-iii-live-4`. Evaluator version: `5`. Temporal policy: `deadline-by-1`. This version applies only to a fresh run after the source-valid deadline-connector correction. Earlier failed reports, including prompt7 under criteria3/evaluator4, remain unchanged and unqualified.

## Supported deadline wording

The original raw candidate text remains in every actual/expected report view. A commitment deadline may include one source-stated leading `by` before an otherwise already-supported, unambiguous deadline expression. It denotes the same deadline as that identical bare expression, preserving next-day IST date-only expiry, stated timestamp offsets and required original-message anchors for relative dates. No raw text is rewritten in the audit record.

Candidate comparison may accept only this narrow connector difference: the remainder must literally match the other expression and an independent evaluator guard must establish that the expression is supported and known. Every other candidate field remains strict. A different known day, omitted/added qualification, negation, approximation, invalid date, vague expression or unanchored relative cannot pass through this equivalence. Payment-day parsing/comparison stays strict: a `by` bound does not establish the actual payment day.

## Frozen run identity

Use the same explicit NEBIUS `zai-org/GLM-5.3-Flash` candidate with low reasoning effort, prompt `candidate-extraction-7`, schema `1`, extraction policy `candidate-only-1`, adapter `nebius-chat-json-schema-9` and findings profile `deterministic-1`. Add required `temporal_policy_version=deadline-by-1`, evaluator5 and criteria4 to report/qualification identity. Independent inventory `gate-iii-findings-1` remains byte-identical with SHA256 `78867b575bc69b0f1ee8ce4783ecd9264d1678deb8d6fb6a0c0469e97bad3632`; manifest SHA256 remains `17bcb26aa33ae4bab8fd37abf7e2260cda1089d47eaedc9bc67e7b89f38e1f81`.

## Unchanged acceptance obligations

All eight candidate/source/policy/product provenance/soundness/completeness/duplicate/outcome checks remain required. Retain literal candidate evidence and independently expected findings. Every actual returned result must be correct; every one of51 entries needs correct actual LIVE coverage within the planned three repetitions/153 unique identities. No best-of-three quality selection, repair loop, fallback or retrospective regrading. Safe bounded transient-provider failures remain distinct from successful extraction; known incorrect output or unsafe state blocks qualification. Keep20-second calls,55-second overall budget, one persisted automatic retry, terminal fencing and stop on first blocking failure or three consecutive no-response cases. Freeze reviewed code/policies/inventory before new calls.

`PASS`, `PASS_WITH_AVAILABILITY_GAPS`, `FAIL`, `BLOCKED` and `INTERRUPTED` retain the meanings below. Owner review and later-gate authorization remain required. This lexical correction changes neither financial authority/arithmetic nor ordered recommendation rules; it makes an explicitly supported source deadline usable without deleting its original wording.

## Preserved previous criteria

The exact version3 and historical version2 text below governs their earlier reports. It does not regrade them using the new temporal policy.

# Version 3 historical criteria

Criteria version: `gate-iii-live-3`. Evaluator version: `4`. This version applies only to a fresh qualification of the owner-approved deterministic-findings refinement. Earlier failed reports retain their original verdicts and versions. Offline verification and independent review must pass before the new LIVE run starts.

## Frozen configuration and independent inventory

- Provider `NEBIUS`, requested/returned model `zai-org/GLM-5.3-Flash`, explicit `reasoning_effort=low`; prompt `candidate-extraction-7`, structural extraction schema `1`, extraction policy `candidate-only-1`, adapter `nebius-chat-json-schema-9`, findings profile `deterministic-1`.
- Independent inventory `gate-iii-findings-1`, exact-file SHA-256 `78867b575bc69b0f1ee8ce4783ecd9264d1678deb8d6fb6a0c0469e97bad3632`. It declares all 51 expected finding inventories from approved evidence without using production derivation as an answer generator. Canonical manifest SHA-256 `17bcb26aa33ae4bab8fd37abf7e2260cda1089d47eaedc9bc67e7b89f38e1f81`.
- Freeze the inventory, manifest definitions, request parameters and all profiles/versions before LIVE. A mismatch fails closed. No in-run prompt/model/oracle changes, hidden repair, fallback or retrospective regrading.

## Required correctness and provenance

Each returned output must pass raw candidate-fact correctness, source validation and mandatory empty-model-findings policy. The final saved product must independently pass finding provenance, soundness, completeness and duplicate checks, plus deterministic action/balance/review correctness. These are separate report fields; empty model arrays do not prove complete product findings.

Finding identities cover contradictions, exact-source questions, all financial/commitment issues and snapshot observations. Missing a required finding fails completeness; an unsupported extra fails soundness; repeated identities fail duplicates. Correct stable IDs alone do not prove provenance: validate exact retained versions, original Unicode spans/quotes, issue version references and observation snapshot/hash and metadata. Unavailable or empty content cannot support a fabricated quote. Preserve issues even when the result is COMPLETE and its action is unaffected.

Retain raw candidate facts, extraction-policy evidence, derived actual findings and expected inventory separately. Wrong policy/candidates/findings block qualification. Checks for unavailable outputs remain unknown; a known incorrect output cannot be erased by a later timeout. Returned model and nonempty response identity must match the explicit LIVE configuration; a report label alone cannot establish LIVE coverage.

## Coverage, safety and availability

The approved basis remains SC-004, AC-24, NFR-002 and NFR-008, as described in the preserved version-2 criteria below. Evaluate the canonical 51 manifest entries, including exact variant/case/event mappings, three times, with 153 unique planned identities. A subset or different repeat count cannot qualify. Every entry needs at least one correct actual LIVE result, and every observed returned output must be correct; do not select only the best repetition.

Each attempt must retain persisted terminal timing, step/retry history and null result/action on INCOMPLETE. Keep the 20-second call limit, 55-second overall budget and at most one persisted automatic retry per failed step. Safe transient provider gaps remain distinct from successful extraction. Authentication/configuration errors, malformed/refused/unsupported outputs, unsafe terminal evidence or excess retries block qualification. Stop safely on a blocking quality error or three consecutive no-response cases and retain failed/unexecuted identities.

`PASS` means every run produced a correct result. `PASS_WITH_AVAILABILITY_GAPS` requires every returned output correct, every entry covered and each remaining attempt an evidenced safe transient-provider failure. Report correctness, coverage, availability and safety separately. `FAIL`, `BLOCKED` and `INTERRUPTED` are unqualified. Only `qualification_scope=RELEASE` can qualify; owner review remains required before Gate IV. Release performance, human usability and later workflows remain separate acceptance work.

## Preserved previous criteria

The following version-2 criteria governed earlier reports. They are retained for interpretation and do not score the new findings profile.

# Version 2 historical criteria

Criteria version: `gate-iii-live-2`. Defined on 24 October 2026 before the fresh qualification run using the clarified discrepancy categories. Prior failed reports remain unchanged.

## Approved basis

[SC-004](../specs/001-payment-case-mvp/spec.md) permits the specified action or an explicitly incomplete outcome, while requiring complete evidence traceability and no guessed amounts or matches. AC-24 and NFR-002 require bounded, truthful failure when a provider is unavailable. NFR-008 adds no upstream availability promise. Three repeats measure observed variability; they do not promise universal model reproducibility.

These criteria distinguish output correctness from provider availability. They remove an undocumented requirement that every provider request succeed; they do not waive evidence integrity, safe failure or actual live coverage. The owner still reviews the Gate III handoff. Release performance, human usability and later workflows remain separate requirements.

## Frozen qualification rules

- Run all 51 manifest entries three times using the same explicit provider, model, request parameters, prompt, schema, adapter and evaluator versions. Record actual outcomes and latency. No selection of the best returned output, hidden repair or runtime model fallback.
- Every observed returned output must pass candidate-fact, source, uncertainty and deterministic-outcome checks. A malformed output, refusal, unsupported interpretation or incorrect result blocks qualification even if another repetition passes.
- Every manifest entry must have at least one correct actual LIVE result across its three repetitions. This is an explicit conservative coverage safeguard introduced for this evaluation, rather than a quoted release target. Missing credentials, unsupported configuration or absent live coverage blocks qualification.
- A provider availability gap must be evidenced by transient extraction-step failure and a terminal INCOMPLETE attempt with null result/action, within the 55-second backend budget and at most one persisted automatic retry of that step. A 400/401/authentication/configuration failure, unsafe result, excess retry or unclassified failure is blocking. Unknown extraction/source/uncertainty checks remain null; known incorrect output cannot be erased by a later timeout.
- The permitted transient-provider category covers transport unavailability/timeouts, HTTP 408/429 and HTTP 5xx as classified by the backend. Failed attempts remain availability failures in the report. They are never described as successful extraction.
- Exact source disagreements require the category rules in [the interface contract](../specs/001-payment-case-mvp/contracts/api.md): explicit transaction relationships, supported normalized facts, no arithmetic-only conflict, no invented unknowns and no unresolved contradiction after a valid correction.

## Report interpretation

`PASS` means every run produced a correct result. `PASS_WITH_AVAILABILITY_GAPS` means every returned output was correct, all entries have actual live coverage, and the remaining attempts satisfy the evidenced safe-provider-failure rules. The latter must retain separate correctness, coverage, availability and safety counts; it must never be summarized as all runs passing. `FAIL`, `BLOCKED` and `INTERRUPTED` remain unqualified.

Only `qualification_scope=RELEASE` with the canonical 51-entry manifest, including its variant/case/event definitions, and three planned repetitions can qualify Gate III. Matching IDs alone is insufficient. A passing `SUBSET` report is a diagnostic result, with `qualified=false`.

The live report preserves validated contradiction/unresolved findings for inspection. Provider failures retain their failure codes, retry evidence and unknown checks. Diagnostic reproductions do not replace earlier outcomes. Backend deadline evidence does not establish the separate full UI responsiveness or human usability evaluations.
