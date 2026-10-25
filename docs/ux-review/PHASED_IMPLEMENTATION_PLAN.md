# PromiseKeeper: proposed spec-driven UX roadmap

**Date:** 25 October 2026. **Audited baseline:** `002-multi-agent-upgrade` / `1f13b86`. **Status:** planning only. Nothing here starts the implementation workflow.

## Governing decisions

The owner must review these six documents and explicitly approve a bounded next phase. The designated human reviewer is the project owner. This roadmap does not amend the constitution, original feature artifacts, agent behavior, APIs or tests, and does not authorize a commit, push, merge, dependency install or LIVE call.

The [constitution](../../.specify/memory/constitution.md) requires written requirements before code, typed boundaries, deterministic financial authority, exact human approval, durable recovery, tests and human review between phases. The installed [Spec Kit workflow](../../.specify/workflows/speckit/workflow.yml) has specification and plan gates; original [spec/plan/tasks](../../specs/001-payment-case-mvp/) remain authoritative until an approved change. Template examples do not override the constitution's requirement to test relevant invariants.

The original comparison AC-28/FR-024 is deferred. Current multi-agent roles differ from Constitution IV and the old one-agent plan; ADR-010 records the upgrade but does not itself amend the constitution. Resolve that mismatch rather than declaring an automatic compliance pass. This is a documentation/readiness gate, not a proposal to rewrite the implemented agents during UX work.

## Phase 0 — Approve scope and restore traceability

**Coherent outcome:** an agreed, reviewable description of the owner experience and its policy boundaries before application changes.

**Proposed work after authorization:** approve the decision-first scope; determine whether comparison is activated for submission; reconcile role/governance and release wording; decide whether the demonstration is STUB or an independently evaluated LIVE path. Use a bounded feature specification/amendment under the established `specs/<approved-feature-id>/` convention, with user stories, acceptance scenarios, constraints, research/decisions, plan and dependency-ordered tasks. The exact feature identifier is chosen at that approval step; none is created now.

**Candidate impacted artifacts, only after approval:** `.specify/memory/constitution.md` if an amendment is approved; relevant `specs/001-payment-case-mvp/{spec,plan,research,tasks}.md` or an approved new feature's artifacts; README/release-status wording where conflicting. Preserve historical reports and failed/unexecuted evidence.

**Dependencies:** owner review of this pack. Broader architecture-policy decisions are the owner's; they are not implementation defaults.

**Acceptance criteria:**

- G-01: written scope names the designated reviewer, baseline, exclusions and per-phase exit gates; approval covers only the selected increment.
- G-02: comparison is either explicitly activated with AC-28/FR-024 traceability or remains deferred; no existing checkbox is silently closed.
- G-03: current agent roles and the constitution/specification are reconciled through the approved amendment/clarification process before dependent implementation.
- G-04: fictional-build publication, formal release acceptance, historical extractor qualification, new-agent qualification and human study status are stated separately.
- G-05: no new provider, sending, import, authentication or memory-service dependency enters this UX scope.

**Verification:** read-only consistency review of the approved artifacts; no product test required for prose-only corrections. Record any unresolved policy choice. **Exit:** stop for owner acceptance and explicit Phase 1 authorization. This audit has not performed Phase 0 amendments.

## Phase 1 — Make the next decision clear and trustworthy

**User story:** As an owner opening a case, I can see what the saved facts support and what I can do next without interpreting agent configuration or losing my place.

**Scope:** B-01/B-02/B-04 from the [backlog](UX_IMPROVEMENT_BACKLOG.md). Preserve the existing tabs. Reorder Findings around the business decision; make technical detail optional; focus case context after explicit opening; use concise, truthful state/fallback/local-feedback labels. Exact evidence and approvals remain unchanged.

**Estimated size:** approximately 2–4 hours of implementation/focused regression work, dependent on the approved state wording. No new dependencies.

**Candidate impacted files:**

- `frontend/src/App.tsx`: explicit case-opening focus, user-initiated navigation handling; retain scope guards.
- `frontend/src/investigations/FindingsView.tsx`: financial/decision hierarchy and optional trace placement.
- `frontend/src/agents/{MorningReview,AgentTrace,FeedbackButtons,AgentRoster}.tsx`: compact owner-facing summary, disclosure and confirmed status wording.
- `frontend/src/investigations/InvestigationControls.tsx`, `frontend/src/components/format.ts`, `frontend/src/styles.css`: supported state labels and shared presentation.
- Relevant `frontend/tests/{findings,agents,morning,feedback,ux,ux-gaps,investigations}.test.tsx`; `tests/e2e/{personas,accessibility,ux-flow}.spec.ts`. Extend existing suites rather than rebuilding them.

**API/backend dependencies:** existing case, attempt/activity, health and morning-review responses only. No command payload, money rule, validation rule, polling deadline or agent transition changes. If a desired stage event is not supplied, show an unknown/last-confirmed state or defer it; do not expand backend telemetry in this phase.

### Proposed acceptance criteria

| ID | Observable requirement | Existing invariants / gaps |
| --- | --- | --- |
| UX-AC-01 | On a current result, selected invoice, certainty-labelled money, supported reason/source and action appear before the expanded technical event list. At 1280×800, explicitly opening a case reveals its decision context without traversing that trace. | Original AC-02/08/09; UX-01. |
| UX-AC-02 | Developer details remain keyboard-accessible on demand. Model/provider/revision and raw payload information are not prerequisites for ordinary review. No prompts or hidden reasoning are shown. | Constitution VII/XII/XIII; UX-03/09 subset. |
| UX-AC-03 | Explicitly opening a case from Morning Review focuses its heading, including when it is already selected. Background refresh/polling retains the user's focus and unsaved edits. At 390–400px/200% text, the case remains reachable and controls unobscured. | AC-01/16/25; UX-04/12 subset. |
| UX-AC-04 | FOLLOW_UP, WAIT, VERIFY_PAYMENT and CLOSE each expose an appropriate action; advice acceptance, draft approval and closure stay distinct. Historical/limited/running states remain explicit; unknown money remains unknown. | AC-03–15/19–25; UX-07. |
| UX-AC-05 | A saved recommendation with a preparing/failed draft is distinguished from an incomplete investigation. Progress names only observed stages; missing/quiet trace data is not fabricated. Existing sixty-second case limitation and safe check-status recovery remain intact. | AC-24/25; UX-06. |
| UX-AC-06 | False `sent_to_langsmith` is displayed as feedback saved locally, without claiming the service is unconfigured or that agents have learned. True forwarding may be explained in optional details. | UX-10; truthful outcomes. |
| UX-AC-07 | Current exact-version save/review/copy/closure and stale/pending/changed-head blocks behave identically; no application POST is added by opening a disclosure or changing layout. | AC-12–20/25; existing clipboard fences. |

**Meaningful verification:** component tests for hierarchy/disclosure, all four actions, historical/unknown money, explicit focus versus background refresh, absent progress and feedback outcomes; retain review/operation-lifecycle tests. Browser journeys cover keyboard opening from Morning Review, source Escape/focus return, reading the financial basis before technical details, no-send approval/copy, and mobile/large-text context. Inspect actual resulting screenshots. Test expectations should follow approved behavior; do not change money, safety, timeout or exact-text assertions to obtain green results.

**Independent review:** presentation/state boundaries, truthful fallback language, focus behavior, stale results and unchanged command payloads. **Exit:** present actual results, remaining failures and a reviewable diff; stop for owner acceptance and explicit Phase 2 authorization.

## Phase 2 — Explain what changed between saved investigations

**User story:** As a returning owner, I can compare two saved investigations and see whether the recommendation, evidence or timing changed without rewriting either result.

**Scope:** B-03 only. Implement a read-only comparison within Findings with links from History. Follow the [proposed comparison contract](PROPOSED_USER_JOURNEY.md#proposed-comparison-contract); use deterministic differences over persisted fields, not an LLM-generated change story.

**Estimated size:** approximately 3–5 hours of implementation/focused regression work; Medium complexity. Pair discovery and legacy compatibility are the main uncertainty.

**Candidate impacted files:** new `frontend/src/investigations/WhatChanged.tsx` and a pure comparison/pair-selection helper; existing `App.tsx`, `FindingsView.tsx`, `history/CaseHistory.tsx`, `api/client.ts`, `api/types.ts` only if presentation helpers need them; scoped CSS. Candidate tests: new comparison component/helper tests under `frontend/tests/` and a new browser comparison journey under `tests/e2e/`. These are proposed names, not created files.

**Dependencies:** approved AC-28/FR-024 activation and Phase 1 acceptance; existing paginated history, saved attempts/results and evidence-version reads. No result-table migration, hash/profile rewrite, comparison API, provider call or new state-changing command. If the available reads prove insufficient, report a bounded follow-up proposal and stop rather than expanding the phase.

### Proposed acceptance criteria

| ID | Observable requirement |
| --- | --- |
| UX-AC-08 | The comparison names two completed results from the same copy/case, their evaluation times and saved statuses. An incomplete newer attempt is shown separately and does not displace either completed side. Original AC-28 links remain accessible. |
| UX-AC-09 | PK-003 before/after `PK-003-U1` shows VERIFY_PAYMENT → CLOSE, recorded/contested INR 60,000 → verified INR 0, and the new ledger version for CR-T2. The case stays open until existing explicit closure. Both saved results/hashes remain intact. |
| UX-AC-10 | Same-action changes, identical results and time-only changes have distinct truthful summaries. Source additions/replacements use stable IDs plus exact versions; payment event time is not confused with evidence arrival. Saved nulls, uncertainty and reason codes are preserved. |
| UX-AC-11 | Commitment pairing uses saved stable identity when available. Missing identity, unsupported legacy profiles, absent source/result and changed finding profiles produce a limitation rather than guessed matches or a zero-change claim. |
| UX-AC-12 | The first partial history page is never assumed to contain the latest pair. Automatic discovery uses at most three 50-event pages; if not exhausted, show partial history and offer explicit load/selection without claiming “latest.” Requests/responses remain copy/case-scoped. |
| UX-AC-13 | Case/copy navigation discards late reads. If a newer completed result appears while loading, mark the pair historical or refresh explicitly. A failed request leaves existing saved findings inspectable. |
| UX-AC-14 | Opening/loading/using comparison performs read requests only, changes no draft state/approval/closure and runs no model. Historical “next action” text is labelled as recorded advice, never a new authorized action. |

**Meaningful verification:** pure helper cases for identical/action-only/evidence-only/time-only/unknown/legacy changes and stable source/commitment matching; component tests for zero/one/two results, incomplete latest attempt, paginated sequence ordering, read limits, unavailable historical records and navigation during delayed requests. Browser test the PK-003 claim → verified settlement → compare originals → explicit closure journey against the real isolated STUB API. Add an assertion that comparison requests cause no mutations; retain source/history integrity and approval regression suites.

**Independent review:** correct pairing, bounded reads, provenance, uncertainty labels, historical/current distinction, accessibility and absence of new write paths. **Exit:** present actual evidence and remaining limitations; stop for owner acceptance. An unfinished comparison stays unadvertised and the existing manual-history demo remains available.

## Phase 3 — Rehearse the approved submission build

**Coherent outcome:** an honest, repeatable demonstration of the exact accepted engineering increment; not completion of missing product studies.

**Scope:** run the [demo plan](BUILDER_OF_THE_WEEK_DEMO_PLAN.md), verify the selected mode, measure real duration, preserve failures and prepare a saved-record fallback. No new feature work. Estimated 1–2 hours plus owner review; external evaluations/study recruitment are not included in that estimate.

**Dependencies:** owner accepts the selected UI increment(s), authorizes the mode and approves any separate LIVE evaluation. LIVE morning-review provenance and retained technical issues need their own review before relying on that path. No LIVE authorization is supplied by this roadmap.

**Candidate artifacts:** the existing approved feature's verification report/demo instructions after authorization; no edits to original failed reports or unexecuted human observations. The exact submission branch/merge is a separate owner decision.

**Acceptance:**

- UX-AC-15: the exact five-minute route is rehearsed with measured duration, explicit fictional/mode/date disclosure, checkable sources, human review, re-evaluation and supported closure.
- UX-AC-16: unavailable providers or writes lead to the existing safe fallback/reconciliation; a failed attempt is not called a completed LIVE result. Saved-record inspection is labelled as saved.
- UX-AC-17: reported tests distinguish new execution, prior retained evidence, skips, failures and isolated rechecks. Simulated personas do not populate the five-owner study.
- UX-AC-18: a final scope check confirms no new integration/agent/sending capability and no regression in source versions, exact financial values, review invalidation or history.

### Planned verification commands, not run for this audit

Use the existing environment and the README's ignored workspace caches. No dependency installation or lockfile update is proposed. Run suites serially to avoid the previously reported load-related startup failures:

```powershell
uv run --project backend pytest
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run test:unit
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
```

Use fresh isolated fictional test copies, never retained demonstration data. Leave opt-in LIVE tests skipped unless separately authorized. A failing full run remains failed even if its unchanged-code isolated recheck passes; record both. Broaden verification only for new changes or unresolved concerns.

**Exit:** owner reviews the actual demo/evidence and decides submission/publication. Formal Gate V / Release 0.1 acceptance still requires its actual missing observations; this phase does not waive them.

## Later, separately authorized increments

1. **Promise timeline readability:** B-05/B-06; one coherent story, saved-data-only, with unknown/event/arrival/supersession tests.
2. **History and setup clarity:** B-07/B-08; friendly business labels plus exact identity access and paginated history tests.
3. **Loading/recovery refinement:** B-09; region-specific status and pending-write preservation.
4. **Template wording or navigation redesign:** B-10/B-11; higher regression surface and separate requirements. No “while we are here” implementation.

Each requires its own approved story, impacted files, acceptance criteria, actual verification and human exit gate. The governing cutoff is 26 October 2026, 10:00 IST; deadline pressure reduces scope, not financial integrity or human control.

## Traceability and review boundary

| Proposed increment | New criteria | Existing requirement links | Main risks |
| --- | --- | --- | --- |
| Phase 1 | UX-AC-01–07 | AC-01–03, AC-08–20, AC-24/25; NFR-005/007 | Misleading currentness, hidden controls, lost focus, weakened exact approval |
| Phase 2 | UX-AC-08–14 | AC-08, AC-16–18, AC-25, AC-28 / FR-024 after activation | Wrong historical pair, null-to-zero, source version mismatch, invented causality |
| Phase 3 | UX-AC-15–18 | NFR/outcome evidence and Constitution X/XIV–XVI | Unsupported LIVE/usability claims, unsafe retry, unrehearsed duration |

These IDs exist only in this proposal. They are not checked tasks or executed acceptance results. **Suggested first implementation phase:** Phase 1 after Phase 0's approval/traceability decisions. Stop here for owner review.
