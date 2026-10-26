# Product verification UX cleanup implementation plan

Publication follow-up, 26 October 2026: the owner subsequently authorized publishing the required 007 product changes and merging to `main`, excluding all submission documents/folders and personal records. The local-only restrictions below describe the original implementation stage; no new LIVE authorization is implied. See [the publication report](../../../reports/product-007-publication.md).

> **For agentic workers:** Use superpowers:executing-plans to implement this plan. Work remains local; commits and publication are not authorized.

**Goal:** Remove demo suggestions, fixture controls and implementation instructions from the complete interface for product-team verification.

**Architecture:** Retain the existing five-page React workspace and API contracts. Remove fixture creation and scenario mutation controls from the interface; use the six-step upload workflow for new workspaces. Preserve saved workspace access, original evidence, exact approvals, recovery and deletion safeguards.

**Tech Stack:** React, TypeScript, FastAPI, Vitest and Playwright.

**Spec:** Owner request of 26 October 2026 with Upload screenshot: remove demo references throughout UX and clean related code for product-team verification.

## Global constraints

- Offline verification with fictional records only. No provider calls, real-data authorization or publication.
- Product language must not imply authentication, source connectors, automatic sending or production qualification.
- Keep a concise internal-verification privacy notice and truthful AI availability.
- Retain backend wire/storage names for compatibility; fixture utilities remain available to automated tests.
- Existing historical reports and datasets stay intact.

## Review focus

- No-workspace and discovery-error states must guide to Upload without creating fixtures.
- Existing uploaded and legacy workspaces must remain selectable, with stable IDs and deletion recovery.
- Each upload step must retain preview, confirmation, sender review, allocation and coverage controls.
- Case History must show saved evidence and decisions without scenario-edit controls.
- Every route, expanded panel and narrow screen must avoid demo promotion and repository paths.

### Task 1: Remove fixture interface and clean shared workspace code

- [x] Update tests to require upload onboarding, workspace language and no fixture creation/scenario controls; run and observe failures.
- [x] Replace DemonstrationPicker with WorkspacePicker, remove ScenarioUpdate, remove unused catalogue state and requests, and update labels and notices.
- [x] Verify affected unit checks and preserve recovery/deletion behavior.

### Task 2: Clean Upload and remaining product copy

- [x] Remove pack paths, filenames, sample downloads and sample instructions; retain useful file-format guidance.
- [x] Update import, coverage, history, assistant and status wording without changing financial behavior or backend restrictions.
- [x] Update existing checks to match the intended product interface; seed scenario test data through test APIs.

### Task 3: Verify and prepare handoff

- [x] Run full frontend, backend, typecheck/build and serial offline Chrome checks, retaining initial failures.
- [x] Inspect desktop and narrow-screen pages and expanded workspace/history/upload states.
- [x] Run a fresh whole-change review, address material findings and record exact results in reports/product-verification-ux.md.
