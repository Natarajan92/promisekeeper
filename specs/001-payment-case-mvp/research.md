# Research and Architecture Decisions

**Feature**: PromiseKeeper Release 0.1 | **Date**: 2026-10-23 | **Status**: Design decisions for implementation planning; no implementation authorization.

The repository contains specification scaffolding, not an existing application stack. Research covered runtime/tooling, the single agent boundary, exact money/time rules, durable transactions, approval recovery, and verification. The three accepted clarifications in [spec.md](spec.md) are binding. All technical choices needed for this design are resolved below; credentials, dependency installation, measured performance, and human acceptance remain implementation prerequisites rather than assumed results.

## ADR-001: Local application and explicit layer boundaries

**Context**: One owner, three fictional starting cases, Windows desktop browser, no authentication or production deployment, and a fixed 26 October 2026 10:00 IST deadline.

**Decision**: Python 3.12, uv, FastAPI/Uvicorn, strict Pydantic 2 boundary models, standard-library sqlite3, React/TypeScript/Vite, pytest, Vitest, and Playwright. Serve the built UI from FastAPI on loopback; use Vite's proxy in development. Use Node 24, matching the locally observed 24.19.0. Resolve compatible versions during authorized setup, commit uv.lock and package-lock.json, and record the exact Python patch and SQLite runtime. Do not fabricate dependency pins before installation.

**Rationale**: A local database and one API process need no hosted infrastructure. Keep domain logic independent of FastAPI, SQLite, the model SDK, and React. Strict runtime models validate API, tool, and model boundaries; typed domain values carry validated facts internally.

**Alternatives considered**: A TypeScript-only service would reduce language count but adds a SQLite binding/runtime choice; Next.js/SSR adds no required capability; PostgreSQL and a distributed queue add operations outside the single-owner scope.

**Consequences and constraints**: Two toolchains must be locked and checked. Existing commands report Python 3.10.10, uv 0.12.23, Node 24.19.0, and npm.cmd 12.2.0; Python 3.12 still needs setup. Use npm.cmd because npm.ps1 is blocked. Put uv caches, managed interpreters, npm cache, and browser downloads under ignored .runtime/ paths so setup does not depend on inaccessible user-profile caches. No installation was performed during research.

Sources: [uv Python management](https://docs.astral.sh/uv/concepts/python-versions/), [uv locking](https://docs.astral.sh/uv/concepts/projects/sync/), [FastAPI versioning](https://fastapi.tiangolo.com/deployment/versions/), [Pydantic strict validation](https://docs.pydantic.dev/latest/concepts/strict_mode/), [Vite requirements](https://vite.dev/guide/), [Vitest requirements](https://vitest.dev/guide/), [Playwright installation](https://playwright.dev/docs/intro).

## ADR-002: Exactly one bounded Investigator

**Context**: Constitution IV permits an initial single agent; financial decisions and approval must remain deterministic.

**Decision**: One Investigator protocol, one sequential execution slot, no autonomous delegation or open-ended tool loop. Orchestration supplies an immutable evidence packet through a bounded read-only snapshot tool. The Investigator extracts candidate commitments, payment claims, explicit replacement/link statements, unresolved questions, and source spans. It cannot verify payments, choose an action, compute a balance/deadline, approve, close, send, browse, execute shell commands, or modify evidence. Recommendation selection, explanations, and customer draft templates are deterministic. There is no Strategist or Communicator agent in Release 0.1.

Use OpenAI Responses with Structured Outputs behind an adapter. The initial configured model candidate is gpt-5.6-terra with reasoning effort none, subject to account availability and measured acceptance. Record requested/returned model identifiers, prompt/schema/adapter versions, and response ID. The official model page does not provide a distinct dated snapshot: model output reproducibility is not claimed. Configuration changes require the same extraction evaluation; do not silently substitute models.

**Rationale**: Structured extraction supplies the LLM contribution while bounded deterministic code owns consequential conclusions. Validate completion/refusal, JSON schema, source membership, exact spans, field syntax, and supported interpretation; schema compliance alone does not establish truth.

**Alternatives considered**: Three collaborating agents would violate the initial limit and expand handoffs. Regex-only extraction would not satisfy the intended LLM-driven release. Generative drafts introduce another semantic validation burden without being necessary for the fixtures.

**Consequences and constraints**: Stub mode is explicitly labeled and supports deterministic offline tests; it does not establish live-agent acceptance. Set SDK max_retries=0. Orchestration permits at most two calls for a failed extraction step, with 20-second limits per call, transient errors only, and a 55-second overall deadline including persistence. Refusal, invalid structure, foreign references, and unsupported spans do not trigger hidden repair loops. Reserve the remaining margin for UI failure display by 60 seconds. Check account access and actual latency/quality during the authorized agent phase.

Sources: [Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs), [model capability reference](https://developers.openai.com/api/docs/models/gpt-5.6-terra), [Python SDK timeout and retry controls](https://developers.openai.com/api/reference/python).

## ADR-003: Deterministic financial and temporal truth

**Context**: Customer claims, invoice settlement, and individual promise fulfillment are separate facts. FV-16 distinguishes invoice allocation from commitment attribution.

**Decision**: Preserve source money strings, validate their syntax/precision, and normalize valid values to integer paise. Calculate with Python integers; represent paise as decimal strings over JSON and in SQLite TEXT fields to avoid numeric coercion or storage overflow. Never construct monetary values from floats or round invalid input. Unknown and invalid values remain explicit states with original evidence.

Only eligible settled, designated ledger allocations with explicit verification_status=VERIFIED affect the invoice balance. Authority designation alone does not establish verification. A separate explicit source-backed link credits a specific commitment; derive fulfillment from eligible attributed amounts, not an owner click or an LLM flag. For the approved catalogue, each attribution links a whole payment to one commitment; unsupported conflicting or excessive attributions require review. Full allocation across multiple invoices remains excluded. A fulfilled partial promise no longer justifies WAIT; unknown attribution that changes the action produces VERIFY_PAYMENT while retaining the known balance.

**Approved analysis refinement (2026-10-23)**: Catalogue-defined immutable CommitmentAnchor IDs bind copy/source-version/key before extraction. Model quotes remain provenance; changed valid boundaries or candidate IDs cannot change payment attribution. Supplied keys must validate against the snapshot and one supported commitment clause; missing/ambiguous identity stays unresolved. Corrections/replacements get distinct source-version identities with no silent link transfer. This replaces span-derived identity; span hashing and extraction-order numbering were rejected because equivalent extractions could break attribution (FV-16).

Store source event and arrival times separately. Persist aware UTC instants and original timezone/date expressions; use zoneinfo Asia/Kolkata plus an explicit tzdata dependency for Windows. Date-only expiry is the exclusive next-day midnight boundary. Parse supported source expressions deterministically; relative expressions require the original timestamp/timezone, and unsupported or ambiguous expressions remain unknown. Freeze the evaluation time per investigation and separate it from execution timeout. REFERENCE demonstration mode uses only catalogue clock events; REAL mode uses the server clock and is visibly identified.

WAIT review_at is the earliest future invoice boundary or active, unfulfilled promise expiry justifying waiting. At that instant, mark the saved result for review and reapply ordered rules on reinvestigation; another waiting condition can yield WAIT again. Choosing the latest boundary would hide the earlier due/promise transition. FV-18 covers both date orderings and exact boundaries; this policy never schedules contact.

**Rationale**: Exact arithmetic and a narrow parser make fixtures reproducible without delegating date or money authority to an LLM.

**Alternatives considered**: Floats, fuzzy payment matching, latest-promise-wins, inferred installment credit, and model-selected dates contradict the specification. Arbitrary document/date ingestion is outside this release.

**Consequences and constraints**: Reversals/corrections rederive both balance and fulfillment while retaining history. A known remainder can coexist with a disputed payment claim and cannot become a demand until the conflict is resolved. Use the ordered rules exactly; no fifth completed-result action.

Sources: [Python exact decimal behavior](https://docs.python.org/3.12/library/decimal.html), [zoneinfo and Windows tzdata](https://docs.python.org/3.12/library/zoneinfo.html).

## ADR-004: Durable SQLite commands, review generations, and restart recovery

**Context**: Repeated clicks, lost responses, mid-run evidence, and failed reruns must not duplicate decisions or resurrect approval.

**Decision**: One local SQLite file contains separately identified demonstration copies. Use foreign_keys=ON on every connection, journal_mode=DELETE, synchronous=EXTRA, a 250ms busy timeout, parameterized queries, and short explicit transactions. Use BEGIN IMMEDIATE for eligibility checks plus mutation. Never retain a transaction while calling the model. An exclusive nonblocking Windows msvcrt byte lock is held for the server lifetime before recovery; use one server worker and fail startup if ownership is unavailable.

Each mutation has a durable operation ID, canonical request fingerprint, and receipt. Same ID/same payload replays its receipt; same ID/different payload fails. Check idempotency before optimistic revisions/capacity rejection. Reserve the global Investigator slot before committing a new start and release it on rollback/terminal outcome; another case cannot persist RUNNING while capacity is unavailable. A partial unique index additionally permits one RUNNING investigation per case. Start atomically captures evidence versions and evaluation time, increments review_epoch, and invalidates approval. Evidence_revision and case_revision are separate from review_epoch.

Results and drafts are immutable versions. Each case records its current draft head; editing atomically advances the head and review_epoch and invalidates approval. Approval requires that head and binds exact text/recipient/invoice, originating investigation, evidence scope, and current review_epoch. After a failed rerun, an older current draft may receive a new explicit approval only when its originating result is still latest completed/current and all checks pass; the earlier approval remains invalid. A failed draft step has a separate idempotent manual retry, original result/time unchanged, with per-step automatic retry usage preserved. Closure rechecks current eligible CLOSE and explicit human confirmation inside its transaction.

On startup, after acquiring ownership, mark previous RUNNING attempts INCOMPLETE, preserve the last completed result, and do not restart generation silently. Persist attempt counts and fence late output by attempt ID, terminal state, and deadline. A recommendation can be saved independently of later draft generation failure.

**Rationale**: A single writer and durable constraints provide inspectable serialization without distributed infrastructure. Explicit immutable snapshots remain valid after the database transaction closes.

**Alternatives considered**: In-memory idempotency, an unpersisted background task, automatic job replay, and restoring old approval lose the required audit/recovery guarantees. WAL is unnecessary for this workload and adds a runtime patch prerequisite; it is not selected.

**Consequences and constraints**: Handle lock/save failures visibly and acknowledge only committed decisions. A response lost after commit must be reconciled by operation ID. History orders by persisted sequence plus timestamps. Deleting an explicitly selected demonstration purges its content but retains a content-free deletion receipt for replay protection.

Sources: [SQLite transactions](https://sqlite.org/lang_transaction.html), [isolation](https://sqlite.org/isolation.html), [partial indexes](https://sqlite.org/partialindex.html), [foreign keys](https://sqlite.org/foreignkeys.html), [synchronous](https://sqlite.org/pragma.html#pragma_synchronous), [busy timeout](https://sqlite.org/pragma.html#pragma_busy_timeout), [Windows locking](https://docs.python.org/3.12/library/msvcrt.html).

## ADR-005: Human gates, fictional authority, and release evidence

**Context**: All P0 requirements remain essential; the deadline does not waive review, integrity, or acceptance evidence.

**Decision**: Use the requesting project owner as the designated human reviewer for each named implementation phase in plan.md. No implementation phase is authorized by this planning command. Every phase delivers its own tests and review evidence; final release evaluation adds full-system, live-model, usability, timing, accessibility, and recovery evidence. P1 comparisons and optional conversation are deferred.

Only versioned approved fictional catalogue entries may enter a demonstration. Applying a named update that changes authoritative fixture records requires a preview and explicit owner confirmation bound to its version, target, and payload hash. The fixture defines verification authority; the confirmation does not promote an arbitrary claim or receipt to a verified transaction. Draft approval is internal review only. No sending endpoint, transport dependency, scheduled contact, or financial edit API exists.

**Approved analysis refinement (2026-10-23)**: Implement shared case-bound preview/confirmation service and API in Gate II, before staged Gate III/IV tests. Hash exact copy/case/event/version/revision/evidence/clock changes; reject stale confirmation and replay known receipts before eligibility checks. Gate IV adds the update UI and closed-case lifecycle integration, reusing that command. Deferring the service until Gate IV was rejected because earlier acceptance journeys require it. Persisted-copy discovery is a read-only GET; the browser retains selected_demonstration_id, restores it only if present in that list, otherwise selects the sole copy or offers an explicit chooser/create action. No backend global active-copy state or implicit reseeding is needed.

**Rationale**: Explicit scope and phase exits preserve the constitution without inventing a release approval. Loopback binding, same-origin checks, strict request schemas, and no arbitrary ingestion fit a fictional demo without authentication.

**Alternatives considered**: Automatic case closure, blanket approval, live integrations, real customer data, cloud deployment, and silently waiving evaluations are excluded by the spec/constitution.

**Consequences and constraints**: Keep credentials server-side; redact diagnostics; do not persist raw provider payloads containing secrets. Human approval is required before any later real-data or additional-agent phase. Principle XIV's 26 October 2026 10:00 IST deadline governs; the constitution's older 25 October open-decision text is a documented governance cleanup, not silently amended here. If P0 cannot be accepted by cutoff, report the shortfall and request an explicit scope decision.

## Research outcome

Pre-design constitutional gates pass for planning. No product ambiguity remains that blocks this design. Installation, model account access, dependency compatibility, and runtime acceptance remain unexecuted. No application code, database, network integration, or product tests were created by this research.
