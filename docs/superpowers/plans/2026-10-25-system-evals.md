# PromiseKeeper System Evals Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Deliver a repeatable independent offline eval set, complete regression/browser verification and an evidence-backed gap report.

**Architecture:** A dev-only Python runner calls the actual app with explicit STUB settings and a fresh database per scenario. JSON case inputs and literal expected outputs are separate from the application. Existing browser tests provide actual frontend evidence.

**Tech Stack:** Python 3.12, FastAPI TestClient/httpx (existing dev dependency), pytest, Playwright/Chrome, SQLite.

**Spec:** docs/superpowers/specs/2026-10-25-system-evals-design.md

## Global Constraints

- Fictional/STUB only; block external networking and tracing, never read credentials.
- Preserve all current branch changes; no product fixes or publication in this evaluation baseline.
- Never count unsupported, error, skipped or unexecuted scenarios as passes.
- No final human acceptance or LIVE qualification inferred.

## Review Focus

- Unsupported natural language must not become confident WAIT advice.
- Payment names and addresses are evidence, never automatic allocation authority.
- Grader mutation checks must detect incorrect money and unauthorized review state.
- A harness/setup error must remain ERROR, never product pass or supported rejection.
- Baseline output must not overwrite prior evidence or mislabel reused cases as held out.

### Task 1: Independent dataset and grading

**Files:** evals/system/cases.json, scripts/system_eval/grading.py, backend/tests/evaluations/test_system_eval_harness.py.
**Interfaces:** Produces JSON case schema and grade(case, actual) -> checks, verdict. Consumed by Task 2.

- [x] Author held-out message/import/payment challenges and literal oracles; tag contract versus capability and safety severity.
- [x] Add failing grader tests for wrong paise, wrong action, unauthorized approval, missing observations and safe refusal versus capability failure. Expected: module missing on first run.
- [x] Implement strict checks and denominator/status aggregation; run focused tests. Expected: all harness tests pass.

### Task 2: Actual application runner

**Files:** scripts/evaluate_system.py, scripts/system_eval/workflow.py, scripts/system_eval/runner.py.
**Interfaces:** Consumes Task 1 case schema/grader; produces immutable JSON/Markdown run artifacts and nonzero exit on failure/error.

- [x] Add failing tests for report reservation, failed-case exit, dataset validation and offline settings. Expected: runner missing.
- [x] Implement per-case fresh API workspaces, actual import previews/commits, owner allocation/coverage, investigation and authority observations. Add workflow cases for replay, scope and stale approval.
- [x] Run all cases; preserve observations and classify gaps without changing product code. Expected: report complete even when desired behavior fails.

### Task 3: Complete verification and findings

**Files:** evals/system/README.md, reports/system-evaluation.md; immutable results under reports/system-evaluation/.
**Interfaces:** Consumes Task 2 artifacts, full backend/frontend/build/browser logs; produces traceable findings and reproduction commands.

- [x] Run complete backend, frontend/typecheck/build and serial Chrome suites; retain original failures and distinguish rechecks.
- [x] Run fresh independent final review under executing-plans; correct harness/report errors only, retaining baseline observations.
- [x] Report case counts, automatic failures, capability gaps, precise test evidence and unmeasured areas. Expected: truthful completion of evaluation, not a claim that the application passed acceptance.
