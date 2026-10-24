# Implementation Plan: PromiseKeeper MVP Release 0.1

**Branch**: `001-payment-case-mvp` (feature branch for the owner-authorized implementation) | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

**Input**: `specs/001-payment-case-mvp/spec.md`, including all three accepted clarifications, the four approved analysis remedies, and FV-01 through FV-18.

**Status**: Gates I-IV are owner-approved and published; Gate IV is `0454551`. Gate V engineering and technical verification are complete. T060 qualifies under frozen criteria after 153 attempts (152 correct returns, one provider gap, zero unexecuted). The required five-owner study remains UNEXECUTED; formal Gate V / Release 0.1 acceptance is blocked. The owner approved publishing the fictional test build while retaining that acceptance block. Earlier failures remain preserved.

## Summary

Build a local, case-centered fictional payment follow-up app for one agency owner. The owner opens one of three seeded cases, inspects evidence, investigates, receives one supported action, reviews a draft when appropriate, and returns to durable history. Exactly one LLM-driven Investigator extracts source-backed candidates; deterministic code owns financial truth, dates, recommendation precedence, explanations, draft templates/validation, approval eligibility, and closure.

Preserve all accepted rules: invoice allocation does not imply promise credit; a fulfilled partial promise no longer justifies WAIT on an eligible overdue remainder; and a failed rerun permits fresh eligible approval without restoring the old approval. No customer messages are sent. All P0 remains essential; P1 comparisons and optional conversation are deferred.

Bind commitments to immutable catalogue anchors scoped to copy/source version, independently of model quote boundaries. WAIT reviews the earliest relevant future invoice/promise boundary and may remain WAIT after reinvestigation. Root navigation discovers persisted demonstration copies and restores the browser's valid selection. Shared case-bound fixture preview/confirmation commands precede every staged journey in Gate II; their UI and closed-case integration remain in Gate IV.

## Technical Context

**Language/Version**: Python 3.12; TypeScript with Node 24 for UI tooling. Select and record supported patch/compiler versions during authorized setup.

**Primary Dependencies**: FastAPI/Uvicorn, strict Pydantic 2, uv, OpenAI Python SDK for Nebius Chat Completions/JSON-schema adapter, tzdata; React/Vite; pytest, Vitest, Playwright. Resolve compatible versions and commit uv.lock/package-lock.json during setup; do not invent exact pins. Provider amendment approved on 24 October 2026: Nebius Token Factory via its OpenAI-compatible Chat Completions/JSON-schema interface; PK_NEBIUS_MODEL candidate subject to account access and measured acceptance (ADR-006). The previous OpenAI provider/model choice is superseded. See [research.md](research.md).

**Storage**: One local SQLite file under ignored `.runtime/`, isolated demonstration-copy IDs, explicit transactions, immutable evidence/results/drafts, operation receipts, append-only case history. Standard-library sqlite3; DELETE journal, synchronous EXTRA, foreign keys per connection. No ORM, broker, cloud database, or distributed queue.

**Testing**: Pure domain/fixture tests; API/schema contracts; actual temporary SQLite race/restart tests; component tests; Playwright against the real API with a scripted Investigator; separately recorded live-model and human release evaluations. Fault tests accompany each phase.

**Target Platform**: Windows 11 desktop browser, FastAPI at `127.0.0.1:8000`, one worker. Built UI served from the same origin; Vite loopback proxy during development.

**Project Type**: Local Python web service and React application; no production deployment.

**Performance Goals**: NFR-002: at least 29/30 saved case opens within 3 seconds; at least 29/30 start acknowledgements within 2 seconds; every attempt visibly completed/limited/incomplete within 60 seconds. Backend overall deadline 55 seconds, provider calls at most 20 seconds each, no SDK retries, UI watchdog at 60 seconds. Final measurements meet the timing limits: HTTP 30/30 fast opens/starts; browser 30/30 fast opens and 29/30 fast starts, all visible terminal results within 10.414 seconds. See `reports/runtime-validation.md` from the repository root.

**Constraints**: One agent role and one sequential Investigator execution slot; at most one automatic retry per failed step. Approved fictional input only; no arbitrary uploads, authentication, financial edits, sending, unattended contact, or automatic closure. Exact INR paise and Asia/Kolkata boundaries. Deadline: 26 October 2026, 10:00 IST.

**Scale/Scope**: One owner in one selected demonstration copy; server discovery lists retained copies and browser selection survives reload/restart. Exactly three starting cases per copy; fresh variant copies preserve existing history. AC-01–AC-27, all 18 variant groups, NFR-001–NFR-008, and SC-001–SC-008 are release coverage. AC-28 is deferred P1. Bound evidence packets by the versioned catalogue without silent truncation.

## Constitution Check

**Before research**: PASS for planning. Written scope and accepted clarifications support bounded design; no implementation approval is inferred.

**After design**: PASS for design; runtime and human acceptance gates remain unexecuted. No exception is requested.

| Principle | Design evidence/gate |
| --- | --- |
| I — Specification first | spec.md remains the product authority; phases trace to its acceptance criteria. |
| II — Small increments | Five bounded implementation phases; detailed tasks are a later artifact. |
| III — Separation | Domain, tools, agent, orchestration, persistence, application, contracts, and UI boundaries below. |
| IV — Bounded agent | Only Investigator, one slot, no subagents/autonomous writes. ADR-002. |
| V — Deterministic safety | Integer money, explicit parser/time boundaries, ordered rules, transactional eligibility. ADR-003. |
| VI — Typed contracts | Strict versioned API/tool models and source-validated output schema. contracts/. |
| VII — Traceable evidence | Immutable source versions/spans, claims/unknowns, explicit attribution. data-model.md. |
| VIII — Human control | Exact draft review, explicit closure/reopening and fixture confirmation; no send transport. ADR-005. |
| IX — Recovery | Durable receipts/snapshots, review_epoch, restart fencing, bounded retries. ADR-004. |
| X — Tests | Normal/uncertain/failure/race/recovery checks accompany each phase, plus live evaluation. |
| XI — Decisions | ADR-001–ADR-005 in research.md record context, decisions, alternatives, consequences. |
| XII — Case UX | Direct case/evidence/timeline/findings/review/history views. contracts/ui.md. |
| XIII — Information | Fictional catalogue, loopback/same-origin controls, backend credentials, redacted diagnostics. |
| XIV — Deadline | All P0 essential; P1 deferred; shortfall requires explicit scope decision without waived safety. |
| XV — Human gates | Requesting project owner reviews each phase and must explicitly authorize its start. |
| XVI — Truthful reports | This delivery checks artifacts only; no application/live-model/usability results claimed. |

Constitution open decisions are addressed by ADR-002 (initial role), ADR-003 (verification), ADR-004/005 (approvals), and the phase/release gates. Principle XIV's explicit 26 October 10:00 IST deadline governs; the older 25 October open-decision reference is a documented governance cleanup, not amended here.

## Project Structure

### Documentation (this feature)

```text
specs/001-payment-case-mvp/
  spec.md
  plan.md
  research.md
  data-model.md
  quickstart.md
  contracts/
    api.md
    investigator-output.schema.json
    ui.md
  checklists/requirements.md
  tasks.md                          # Dependency-ordered work; no implementation authorized
```

### Source Code (repository root)

These are planned paths, not existing application code:

```text
backend/
  pyproject.toml
  uv.lock
  src/promisekeeper/
    domain/                         # Pure money, dates, rules, eligibility
    contracts/                      # Strict Pydantic boundary models
    tools/                          # Read-only snapshot lookup
    agents/                         # Investigator protocol, Nebius/scripted adapters
    orchestration/                  # Attempts, deadlines, retries, output fencing
    persistence/                    # SQLite migrations/repositories, ownership
    application/                    # Commands, queries, receipts, draft templates
    api/                            # FastAPI routes and safe errors
    fixtures/                       # Versioned approved fictional catalogue
    cli.py                          # Local run/seed/evaluation commands
  tests/{domain,contract,integration,evaluations}/
frontend/
  package.json
  package-lock.json
  src/{api,cases,investigations,reviews,history,components}/
  tests/
tests/e2e/
reports/                            # Verification evidence, no secrets
.runtime/                           # Ignored DB, lock, caches, managed interpreters
```

**Structure Decision**: One backend and UI. Domain imports no database, provider, presentation, or web framework. Application/orchestration depend on interfaces; adapters implement them. FastAPI and React never recalculate authoritative finance/eligibility. No agent framework or distributed infrastructure.

## Execution and State Design

1. Replay a known operation receipt before capacity rejection; reserve the process-wide Investigator slot before persisting a new start. Check revisions in a short transaction; persist immutable evidence scope, evaluation time, RUNNING attempt, review_epoch increment, approval invalidation and receipt before acknowledgement. Release the slot on rollback or terminal outcome.
2. Call the single Investigator outside the transaction. Validate completion/refusal, schema, allowed sources, exact spans and supplied catalogue commitment keys before deterministic normalization/reconciliation/action selection. Bind only unambiguous source-version anchors; quote boundaries/candidate IDs never create persistent identity. Embedded source instructions remain untrusted evidence.
3. Persist COMPLETE/LIMITED with one action; INCOMPLETE has none. Later evidence makes old-scope results historical. A separate draft failure cannot erase a saved recommendation.
4. Generate explanations/drafts from validated facts and source references. Persist a current draft head; edits atomically advance it and invalidate approval. Retry a failed draft step with a separate idempotent operation while preserving the completed recommendation. A conservative deterministic validator blocks unsupported financial clauses, modified monetary facts, fees, invented instructions and placeholders; unrecognized financial claims fail closed. Neutral wording edits remain reviewable.
5. Approval/closure atomically recheck exact payload, current draft head when approving, revisions, latest completed result, current evidence/time and no running investigation. After failed rerun, a fresh eligible review may use the earlier current draft with the new epoch; old approval stays invalid.
6. Acquire exclusive process ownership before restart recovery; mark old RUNNING attempts INCOMPLETE and fence late output. No silent generation replay or seed reset. Reconcile unknown save outcomes by operation ID.
7. List persisted nondeleted demonstration summaries read-only. Restore a valid browser selection; otherwise select the sole copy, show a chooser for multiple copies, or require explicit creation for no copies. Preserve copy-scoped pending work when navigating.
8. Before applying a registered fixture event, return a read-only preview bound to catalogue version, copy/case/event IDs, current revision and exact evidence/clock changes. Confirm the hash/revision atomically with arrival/invalidation/receipt. Early tests submit this exact confirmation through the real API; they do not depend on the later update UI.

See [data-model.md](data-model.md) and [contracts/api.md](contracts/api.md). Business evaluation time is separate from execution timeout; REFERENCE catalogue replay and REAL modes are visible. No API accepts arbitrary evidence, verification flags, or scenario dates.

## Implementation Phases and Human Review Gates

**Designated reviewer**: the requesting project owner, the human user of this session. Before each implementation phase, obtain explicit authorization for its scope. At each exit present changes, acceptance evidence, tests actually run, unresolved/unexecuted checks, and proposed next phase; stop until authorized. These implementation phases differ from speckit-plan's research/design phases.

| Phase | Bounded scope and prerequisites | Required exit evidence |
| --- | --- | --- |
| I — Domain and fixtures | Setup, strict boundaries, approved catalogue/commitment anchors, exact money/date/attribution/action rules; no UI/provider dependency. | Pure baseline/update/FV business tests, FV-16 identity/attribution invariance, FV-18 earliest-boundary/repeated-WAIT cases, before/at-midnight boundaries, unknowns/conflicts/reversals/duplicates. AC-03–AC-09, AC-21–AC-23, AC-26–AC-27. |
| II — Durable case commands | After I review: SQLite, receipts, ownership/recovery, snapshots/history, shared fixture preview/confirmation service and routes, demonstration discovery and minimal case API. | Real temporary SQLite commit-failure, repeated-operation, concurrent-start, snapshot and restart tests; case-bound exact fixture confirmation, stale/hash/target rejection, immutable anchor links and persisted-copy listing. AC-01–AC-02, AC-16–AC-18, AC-24–AC-25. |
| III — Investigation and inspection | After II review: sole Investigator, bounded worker, demonstration selection, case/evidence/timeline/findings UI and deterministic explanations. | Offline contract checks plus recorded live extraction evaluation; identity invariance under changed quote boundaries, refusal/invalid-source/timeouts/retry/fencing tests; FV-18 and accessible evidence/action journeys; reload/restart selection. Staged tests use Gate II confirmation API. AC-01–AC-09, AC-21–AC-27. |
| IV — Human review and disposition | After III review: drafts/edit/save/validation, approve/reject, advice disposition, closure/reopening/history and fixture-update UI; reuse Gate II commands for closed-case integration. | Exact-payload/stale/racing approval tests, no send capability, FV-17 fresh approval recovery, closure eligibility, closed-case update/reopening and duplicate-save checks. AC-10–AC-20, AC-25. |
| V — Release acceptance | After IV review: full-system fault/restart drills and measured acceptance; tests already accompany I–IV. | AC-01–AC-27 and all 18 FV groups; all NFR/outcome measures; 30 timing trials, ten preservation cycles, five-owner evaluation, keyboard/200%/non-color checks, live-model report. Disclose unmet learning targets and unexecuted evaluations. |

Every phase is P0-essential; no phase covers the whole application. Detailed dependency-ordered tasks and full requirement/test mapping belong to speckit-tasks. AC-28 and optional chat remain deferred.

## Verification and Release Limits

[quickstart.md](quickstart.md) distinguishes available setup/run/check commands from later release measurements. Gates I–II are implemented and owner-approved; Gate III implementation is undergoing live acceptance as recorded in [its report](../../reports/phase-iii.md). Later-gate product acceptance remains unexecuted. Account access, resolved dependency compatibility and actual model latency/quality are phase gates; failure cannot silently change provider or weaken a target.

Reject non-loopback Host/non-allowlisted browser Origin, require JSON plus a custom same-origin mutation header, and disable wildcard CORS. This is a fictional demo boundary, not authentication or production readiness. Keep secrets backend-only and redact diagnostics. Retain demonstration history until explicit deletion; never reset on restart. Real-data release requires access/retention/deletion policy first.

## Complexity Tracking

No constitutional violations or exceptions. The two-language boundary, conservative draft validator and explicit process lock are bounded decisions recorded in research.md. No extra agent, hosted service, broker or production deployment is justified.
