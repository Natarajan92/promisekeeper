# Deterministic Findings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the approved Gate III refinement with deterministic, source-linked findings and independently verified completeness.

**Architecture:** The sole Investigator returns raw message candidates under an enforced empty-findings policy. Shared pure lifecycle selection and a production findings service derive contradictions, questions, issues and snapshot observations before result hashing. An independent static inventory evaluates all 51 manifest entries; it never enters production or provider requests.

**Tech Stack:** Existing Python 3.12, Pydantic/FastAPI, SQLite, React/TypeScript, pytest and Playwright; no new dependency.

**Spec:** [Approved design](../specs/2026-10-24-deterministic-findings-design.md).

**Execution status:** Tasks 1?4 and offline Task 5 corrections/reviews passed. The frozen LIVE batch and its sole bounded continuation stopped at 38/153 because of repeated provider failures: 32 correct returned results, six provider gaps, 115 unexecuted. Qualification, model-default alignment and Gate III completion remain pending. The owner subsequently approved Gate III implementation, commit/push and starting Gate IV on 24 October 2026. T060 qualification remains outstanding; see the current Gate III report.

## Global Constraints

- This refinement covers Gate III only, T039-T061. Subsequent Gate IV authorization is recorded in the Gate III report. Preserve every earlier failed report and immutable saved result.
- Keep one Nebius model, GLM candidate with low reasoning effort, a 20-second call deadline, 55-second overall budget, one persisted automatic retry per failed step and terminal fencing. No repair loop or fallback.
- Do not open `.env`, inspect a credential value, print environment values or run secret-comparison scans. Trusted backend code may load the credential internally for approved tests without exposing it.
- Keep accounting local and excluded from Git. No Gate III commit or publication before owner review.
- Existing checkout and disjoint file ownership remain in use. Tests use fresh temporary databases and offline networking guards.
- Raw vague temporal text remains text; null means unstated. Financial decisions and mutation eligibility must remain identical.

## Review Focus

- Legacy hashed payloads: reading an older saved result must not insert new default fields or alter its hash (Task 1/4).
- Corrections and reversals: invalid/cyclic/forked records cannot become known findings while existing financial decisions remain unchanged (Task 1/2).
- Unavailable or empty sources: expose metadata observations without manufacturing quotes or missing-amount questions (Task 1/3).
- Multiple issues on COMPLETE results: retain every material issue, including those that do not alter balance/action (Task 1/3).
- A plausible but incomplete inventory match: reject missing/duplicate findings, changed manifest definitions and noncanonical qualification scope (Task 2/4).

## Shared wire contract

Use `findings_version="deterministic-1"` on new results. The existing result arrays remain, with deterministic producers. Add required `commitment_issues` and `evidence_observations` on the new result type. Legacy results omit these fields and retain their original JSON representation. Use strict legacy/new result types and exclude unset defaults on response serialization; new-result validation must require the new fields.

`SourceVersionRef = {source_id:string, evidence_version_id:UUID}`.

Financial and commitment issues expose `{code, detail, sources:string[], source_versions:SourceVersionRef[]}`. Financial `source_versions` is additive on existing issue DTOs; case-summary issues and old results may omit it.

`EvidenceObservation = {subject:"LEDGER"|"SOURCE", field:"availability"|"complete"|"content_present", value:availability-enum|boolean, snapshot_id:UUID, snapshot_hash:SHA256, source:SourceVersionRef|null}`. Always retain the two ledger availability/completeness observations with null source. SOURCE observations name the exact record: emit availability when it is not AVAILABLE, and `content_present=false` when original text is empty. Enforce consistent subject/field/value types and snapshot identity.

Questions use one identity per `(field, stable source ID)` with one exact span. Direct contradictions use one identity per `(kind, sorted source-ID pair)`; issue identities are `(code, sorted source IDs)`. Deduplicate those identities without hiding distinct fields or issues. Profile metadata, all new projections and exact references are included in new result hashes.

Bound result arrays without truncation: at most 4096 contradictions, 512 questions, 512 issues of either kind, and 128 observations. The existing packet limits and span semantics still apply. Internal helper names may be refined jointly by their owners without changing this wire contract.

### Task 1: Production extraction policy, lifecycle and findings

**Owner:** backend implementation agent. **Files:** create `backend/src/promisekeeper/domain/record_lifecycle.py` and `application/derived_findings.py`; modify `domain/payments.py`, `agents/protocol.py`, `agents/nebius.py`, `agents/validation.py`, `application/findings.py`, `contracts/cases.py`, `contracts/investigations.py`, `orchestration/investigate.py`, `api/investigations.py`; targeted tests under `backend/tests/domain`, `contract`, `integration`.

**Interfaces:** `project_records(records, *, payment=False) -> LifecycleProjection` returns active records, issues and invalid/ambiguous/superseded identities. `derive_findings(case, extraction, recommendation, commitment_facts, packet) -> dict` returns the new deterministic result projections. Production code must not import fixture expectations or evaluator code.

- [x] Write failing policy/real-persistence regressions: nonempty model findings reject with no result/action; negative/precision records never create known numeric contradictions; a raw vague date remains preserved and unresolved; COMPLETE attempts retain commitment issues; source-less incomplete lookup is an observation.
- [x] Verify failure: run the new tests using `backend/.venv/Scripts/python.exe -m pytest -q <test-paths> --basetemp=.runtime/pytest-derived-red` and retain the failing evidence locally.
- [x] Extract lifecycle selection without changing payment decisions. Preserve all existing issue codes and outputs. Derive exact known disagreements and source-specific unknowns, retaining the independent current oracle unchanged.
- [x] Enforce a versioned empty-findings policy for both STUB and LIVE; constrain the provider schema and reject violations. Bump prompt/adapter/policy versions. Keep only candidate extraction instructions in the provider responsibility.
- [x] Add strict DTOs and a new result profile; derive before hashing/persistence. Legacy reads preserve stored JSON. Verify unchanged outcomes and policy/derivation/legacy tests green.

### Task 2: Independent finding inventory and evaluator

**Owners:** independent review agent authors inventory and its semantic review; backend agent owns evaluator integration. **Files:** create `backend/tests/evaluations/expected_findings.json`, `application/evaluation_findings.py`, inventory/scoring tests; modify `evaluations.py`, `evaluation_qualification.py`; root updates the criteria report before LIVE.

**Interfaces:** `expected_findings.json` records version, canonical manifest definitions/hash and one explicit stable-ID inventory per entry. Each inventory contains contradiction identities `(kind, sorted source IDs)`, question identities `(field, sorted source IDs)`, financial/commitment issue identities `(code, sorted source IDs)` and observation identities `(subject, field, value, source ID|null)`. `score_findings(result, packet, expected) -> dict` independently reports source validity, soundness, completeness and duplicate checks.

- [x] Author and review all 51 expected inventories from approved catalogue evidence, without importing/running the new production derivation. Pin a version/hash before live tests. Expected answers remain evaluation-only.
- [x] Write failing scorer tests: omit one expected finding, add a fabricated one, duplicate a finding, alter a version/span, forge an observation snapshot and change a manifest mapping. Assert each blocks qualification; an expected empty inventory must still have source/observation checks.
- [x] Retain candidate facts, enforced model policy, derived actual findings and expected inventory separately in reports. Replace the old model-question score with explicit product soundness/completeness/provenance checks; never claim forced-empty arrays establish correctness.
- [x] Add evaluator/criteria versions and inventory hash to qualification identity. Keep all actual coverage, safety, deadline, retry and canonical 51-by-three scope guards. No retrospective regrading.
- [x] Verify all 51 oracle-packet projections and the synthetic boundary matrix against the independent inventory before any new provider call.

### Task 3: Findings UI and legacy presentation

**Owner:** frontend implementation agent. **Files:** `frontend/src/api/types.ts`, `cases/CaseEvidence.tsx`, `investigations/FindingsView.tsx`, related component tests and fixtures.

**Consumes:** shared wire contract above. Legacy data may omit new fields and issue references. **Produces:** exact-version source buttons, visible financial/commitment issues and ledger/source observations, plus legacy-profile notice requesting reinvestigation.

- [x] Write failing component tests: COMPLETE result issue remains visible; an issue opens its exact old source version after an evidence update; empty-source observation is readable without a fabricated source button; legacy result renders without new fields and is labeled legacy.
- [x] Implement the new projections using existing layout/source viewer. Preserve claim/verified-payment distinction, unknown amounts, existing action messages and saved-result navigation.
- [x] Run component tests, typecheck and production build; require passes before browser integration.

### Task 4: Root integration and independent review

**Owner:** root. **Files:** `tests/e2e/investigation.spec.ts`, applicable integration checks, reports and interface documentation.

- [x] Add a real Chrome/API/SQLite regression that displays the derived issue and opens its exact retained source; cover an observation without a readable source and a legacy-profile notice.
- [x] Verify an old stored JSON/hash survives an actual GET/restart unchanged, while a new explicit investigation creates a deterministic-profile result.
- [x] Independently review the inventory and scorer against the approved semantics, including reversal/negative/precision and valid currency disagreements; do not generate expected answers from production output.
- [x] Run backend suite, frontend checks and browser journeys using fresh paths. Fix evidenced failures; request scoped and whole-change review. Update API/research/design/task documents to the final implementation.

### Task 5: Frozen LIVE qualification and Gate III handoff

**Owner:** root with backend execution agent. **Files:** `reports/live-evaluation-criteria.md`, `reports/live-evaluation.json`, `reports/phase-iii.md`, README/setup guidance; local accounting files remain excluded.

- [x] Freeze reviewed inventory hash and extraction/findings/evaluator/criteria versions after all offline checks and reviews pass. Preserve the existing prompt-6 archive byte-for-byte.
- [ ] Run one explicit canonical 51-entry, three-repetition LIVE qualification through the trusted backend, with safe metadata-only diagnostics and no in-run model/prompt/oracle changes. Stop safely on known blocking quality errors or three consecutive no-response attempts; retain failed and unexecuted labels.
- [x] Check every observed candidate and final product finding, exact source provenance, completeness, coverage and safety. Provider failures remain distinct from successful extraction; no best-of-three selection.
- [ ] Only after qualification, align the environment template/default model with the measured configuration without opening or modifying the owner's secret file. Verify affected configuration behavior.
- [ ] Complete T060/T061 only if their actual exit evidence passes. Refresh local accounting with unknown counters preserved, verify exclusions and staged names, and stop for owner review before Gate IV. Do not commit/push Gate III automatically.

Plan self-review: all approved design behaviors map to the tasks above; shared DTO names, legacy behavior and scorer inventory identities are fixed. Existing Gate III execution authorization and the owner's explicit refinement approval cover implementation using the current team workflow; no additional plan-approval question is needed.
