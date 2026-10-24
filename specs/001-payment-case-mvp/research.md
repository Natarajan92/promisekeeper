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


## ADR-006: Owner-selected Nebius inference for Gate III

**Context**: On 24 October 2026 the owner reported having Nebius and Claude credentials, requested an environment-file template, and explicitly selected Nebius when asked which provider should replace OpenAI. The original ADR-002 OpenAI provider/model choice is superseded for Gate III; its one-Investigator architecture and safety requirements stand.

**Decision**: Use the Nebius Token Factory OpenAI-compatible Chat Completions endpoint at `https://api.tokenfactory.nebius.com/v1/` through the existing OpenAI Python SDK. Request schema-constrained JSON, disable SDK retries, keep a 20-second call deadline and the 55-second overall budget, and run the same strict schema/source/span/anchor validation and deterministic financial rules as STUB. Read `NEBIUS_API_KEY` only in the backend from a Git-ignored root `.env` or process environment (process values win). Configure the requested model using `PK_NEBIUS_MODEL`; initial candidate `Qwen/Qwen3-235B-A22B-Instruct-2507` is subject to account access and measured acceptance. No silent provider or model fallback is permitted.

**Evidence**: [Nebius API introduction](https://docs.tokenfactory.nebius.com/api-reference/introduction) documents the SDK, endpoint and key; [structured output](https://docs.tokenfactory.nebius.com/ai-models-inference/json) documents JSON-schema output, refusals and model-dependent support. The [official model cookbook](https://dev.nebius.com/cookbook/openhands-agent-canvas) lists `zai-org/GLM-5.3-Flash`, evaluated separately after the Qwen preflight failed. These documents establish the interface, not this application's live acceptance.

**Measured configuration refinement**: Initial GLM calls exhausted the bounded extraction calls on some cases. A controlled low-effort request returned valid candidates more quickly, so the GLM candidate uses explicit `reasoning_effort=low`. [Nebius's chat reference](https://docs.tokenfactory.nebius.com/api-reference/inference/create-chat-completion) exposes this parameter; [NVIDIA's model serving documentation](https://docs.nvidia.com/nim/large-language-models/latest/get-started/advanced/get-started-glm-5.3-flash.html#control-reasoning) describes the supported effort levels. The Nebius account's omitted-parameter default was not established. The explicit setting is versioned and recorded, without changing deadlines, validation or the selected provider/model at runtime. Observed HTTP 529 responses also required application-owned HTTP 5xx retry classification; the persisted one-retry limit remains unchanged. See the phase report for actual qualification outcomes.

**Alternatives**: Anthropic was offered and not selected. Retaining OpenAI would require credentials the owner does not have. A provider-agnostic router would add unnecessary scope.

**Consequences**: Gate III implements one Nebius LIVE adapter and one explicitly labeled scripted adapter behind the same protocol. Returned model/response identity, prompt/schema/adapter versions, measured latency and provider usage must be recorded. Missing credentials, unsupported schema or failed extraction acceptance keep live evaluation unexecuted/failed and prevent Gate III acceptance; STUB cannot substitute.

## ADR-007: Explicit discrepancy categories and independent evaluation

**Context**: Live evaluation exposed an oracle that rejected every `PAYMENT_CLAIM` and `OTHER_CANDIDATE` contradiction despite those categories being in the approved schema. Independent review established acceptance boundaries before inspecting reproductions. Captured same-reference claim/ledger disagreements proved false rejections. A genuine ledger conflict labeled `INVOICE_FACT` also exposed an undocumented category distinction.

**Decision**: Clarify that `INVOICE_FACT` compares invoice records, `PAYMENT_CLAIM` requires an explicit same-transaction claim/ledger relationship, and conflicting same-transaction ledger facts use `OTHER_CANDIDATE`. Compare supported normalized facts, preserving unknowns. Reject unrelated references, arithmetic-only differences, identical duplicates and resolved corrections. An unresolved field needs an actual missing, invalid or disputed value on its exact source. Apply the same positive and negative criteria independently of the model; never infer a guessed match, financial authority or absence of uncertainty from a passing source span.

**Consequences**: Version the clarified prompt and evaluator, retain validated uncertainty findings for audit, preserve previous failed reports, and run fresh qualification. Diagnostic reproductions cannot retroactively pass earlier outputs. No financial rule or acceptance target changes.

**Further measured clarification**: The complete prompt-4 qualification failed six quality checks. Separate reproductions identified a raw vague-date expression replaced by null and an invalid-precision ledger amount treated as a known numeric disagreement. Independent contract review distinguished invoice allocation from commitment attribution; the existing `ATTRIBUTION` field refers to the latter. Clarify those general boundaries in the prompt and field descriptions, preserving raw temporal text independently of deterministic date resolution and preserving invalid money text without granting numeric authority. Future reports retain actual and expected candidate facts as well as uncertainty findings. Scoring and qualification criteria remain unchanged; the failed prompt-4 report remains available and any amended configuration requires fresh live evidence.

The prompt-5 evaluation then exposed a reversal record labeled as a payment-claim contradiction. A reversal is a later lifecycle event affecting settlement, not automatically a disagreement with an earlier claim that a payment happened. Independent review recommended explicitly excluding reversal and reversed records from active factual comparisons, matching the existing deterministic semantics and oracle. Preserve the stopped batch and version this narrow clarification; it does not authorize a model to decide settlement or weaken the correctness checks.

## ADR-008: Deterministic product findings after raw extraction

**Context**: The stopped prompt-6 evaluation still treated an invalid negative payment amount as a known disagreement despite an explicit extraction instruction. Repeated prompt amendments did not establish reliable product findings. The owner approved the independently reviewed [deterministic-findings design](../../docs/superpowers/specs/2026-10-24-deterministic-findings-design.md) on 24 October 2026.

**Decision**: Narrow the Investigator to raw message candidates with the versioned `candidate-only-1` policy. Both model findings arrays must be empty; provider schema and runtime validation enforce this. Pure production code derives source-linked contradictions, source-specific questions, financial and commitment issues, and snapshot observations before result hashing. Shared lifecycle selection preserves financial decisions while excluding invalid, ambiguous, superseded and effectively reversed facts from known comparisons. An ineligible reversal pointer cannot hide a current disagreement.

Use the `deterministic-1` result profile with exact issue version references. Preserve issues even on COMPLETE results, and represent unavailable/empty sources or incomplete lookups without invented quotations. Existing saved JSON and hashes remain unchanged; explicitly reinvestigate to obtain the new profile.

**Independent acceptance**: A separate static inventory declares all 51 canonical expected projections from approved evidence without importing or running the new production derivation. Evaluation checks raw candidate facts and policy separately from final finding soundness, completeness, duplicates and exact provenance. Expected answers never enter production or provider requests. Freeze inventory and evaluator identities before a fresh canonical LIVE evaluation; earlier failed reports remain unchanged.

**Consequences**: Model-generated findings no longer determine the displayed uncertainty inventory. Deterministic derivation and independent completeness checks become additional acceptance obligations. This decision does not establish live qualification, alter money/action/fulfillment rules or authorize Gate IV.

## ADR-009: Preserve supported deadline connectors

**Context**: The prompt-7 batch stopped after a source-valid candidate returned `by 20 October 2026` from the original commitment. The bounded parser accepted only the bare date, creating a false unknown-date question and VERIFY_PAYMENT outcome. Exact raw-field scoring also rejected the connector variation. The failed batch remains archived and unqualified.

**Decision**: Preserve raw wording and recognize one leading `by` only in deadline parsing, before an otherwise supported unambiguous expression. Keep the existing exclusive next-day IST, offset and original-source-clock rules. Payment-day parsing remains strict. Independently compare only this connector difference in commitment dates when the remainder is literally identical and a separate standard-library guard establishes a known supported deadline. Other fields, different days, vague/unanchored wording, negation, approximation, extra qualifications and overflow remain strict.

**Validation and consequences**: An offline persisted replay now retains the source phrase and produces the expected FOLLOW_UP, expiry and finding inventory. Positive/negative controls and all 51 independently expected projections pass without changing the inventory. Temporal policy `deadline-by-1`, evaluator `5` and criteria `gate-iii-live-4` identify the correction; model/prompt/adapter and financial precedence are unchanged. Require independent review, a fresh full backend check and new canonical LIVE qualification. Do not regrade prompt-7 or rewrite saved results.

## ADR-010: Multi-agent orchestration with LangGraph

**Context**: On 24 October 2026 the owner authorized a multi-agent upgrade on branch `002-multi-agent-upgrade` (see the plan in `docs/superpowers/plans/2026-10-24-multi-agent-upgrade.md`). ADR-002 and Constitution principle IV limited Release 0.1 to one Investigator and named Strategist/Communicator agents as out of scope for that release.

**Decision**: Amend ADR-002 for this branch. The existing steps become LangGraph nodes (evidence intake, promise extractor, rules engine) that keep the persisted step, deadline, retry and fencing rules. New nodes follow: client memory, a Communicator (one personal-note paragraph only), a deterministic safety check, a Tone Reviewer (Nebius or Fireworks) with at most two revisions, and an owner-review interrupt checkpointed in SQLite and resumed after the recorded review. A second graph, the Morning Review supervisor, selects cases that need work, runs the case graph and asks a Briefing agent for a summary whose numbers must appear in the case facts. Agents hand off typed messages under an explicit protocol; AI agents are read-only; customer text is screened before writing agents see it; a per-model circuit breaker protects the case deadline. Autonomous supervisor runs are opt-in.

**Unchanged**: Code owns money, dates, recommendations, eligibility, approval and closure. The qualified extraction path (prompt, schema, validation) is unchanged. Nothing is sent to customers.

**Consequences**: More moving parts and more provider calls per case. Every agent failure falls back to the standard template, a plain briefing or no memory, never to an unreviewed result. The new agents are unqualified until measured with `evaluate --suite agents` and `--suite hinglish` in LIVE mode; the Release 0.1 qualification does not cover them.

