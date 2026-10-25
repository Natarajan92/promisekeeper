# Implementation plan: owner experience Phase 1

**Baseline:** `1f13b86`. **Spec:** [spec.md](spec.md). **Reviewer:** project owner.
**Scope:** frontend presentation only, using installed React/TypeScript, CSS, Vitest
and Chrome/Playwright. No backend or lockfile changes; no provider calls.

## Constitution check

Keep domain/agent/persistence boundaries, integer money, source versions, exact approved
wording, server eligibility, pending-operation recovery and no-send behavior intact.
The constitution sync records the already-approved ADR-010 role exception; this UI
increment adds no role. Correct README publication wording without revising retained
evaluation results. Comparison stays deferred until the Phase 1 exit gate.

## Tasks and verification

1. Record scope, authorization and baseline. Complete frontend baseline must pass.
   Expected: no tracked source changes before new tests; current tests pass.
2. Make Findings decision-first with optional developer details and truthful saved/draft
   states; compact live progress uses only observed state/events.
   Targets: `FindingsView.tsx`, `AgentTrace.tsx`, `InvestigationControls.tsx`, CSS and
   relevant component tests. RED: missing decision hierarchy/disclosure or incorrect
   state assertions fail. GREEN: focused findings/agents/investigation tests pass.
3. Focus case context only on explicit opening and compact completed Morning Review.
   Targets: `App.tsx`, `MorningReview.tsx`, CSS and navigation/morning tests.
   RED: case heading not focused, refresh steals focus or completed detail is expanded.
   GREEN: explicit/same-case/background-refresh and briefing tests pass.
4. Report locally saved feedback without inferring remote configuration or learning.
   Targets: `FeedbackButtons.tsx`, feedback tests. RED: existing text asserts an
   unsupported configuration reason. GREEN: false/true/error cases preserve payloads.
5. Verify the whole increment and conduct independent review. Run complete component
   suite, typecheck/build, appropriate backend regression suite and serial offline
   Chrome journeys. Inspect actual desktop/390px/200% screenshots. Update any browser
   assertions deliberately affected by disclosure/navigation changes, preserving money,
   exact-text, timeout, approval and source assertions. Record failures and rechecks.

Shared interfaces: task 2 owns optional trace rendering consumed by task 3 case
navigation; keep the case/attempt API and ReactNode trace boundary compatible. Task 4
changes feedback copy only and retains the existing response boolean and commands.

Verification adjustment: the legacy byte-preservation browser test performs three
backend startups, each with an existing ten-second readiness budget. Its overall
test budget is aligned to the other multi-restart tests at sixty seconds, leaving
time for the fixture and browser checks. Product deadline and byte assertions stay
unchanged; retain earlier timeout runs in the phase report.

## Review focus

Historical results must not gain current actions; null money must remain unknown;
technical disclosures must not initiate writes; explicit focus must work on the same
case while refresh leaves draft typing alone; async case/copy changes must not move
focus to the wrong invoice; running/complete/drafting states must reflect saved data;
fallbacks and false forwarding flags must not claim model execution or configuration.

## Exit

Leave changes local and reviewable, with actual verification evidence. No automatic
commits, push, merge, comparison implementation, LIVE evaluation or study acceptance.
