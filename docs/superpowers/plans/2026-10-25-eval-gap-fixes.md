# Evaluation Gap Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix unsafe advice, currency/date/language gaps, bank CSV usability and future-invoice validation with evidence.
**Architecture:** Explicit sender role at intake; bounded parser plus provenance-preserving domain normalization; documented bank adapter feeding existing atomic imports. Preserve original eval artifacts and owner controls.
**Tech Stack:** Existing Python/FastAPI/SQLite, React/TypeScript, pytest and Playwright.
**Spec:** docs/superpowers/specs/2026-10-25-eval-gap-fixes-design.md

## Global Constraints

- Fictional offline/STUB only; no credentials, LIVE providers, connectors or sending.
- Preserve original baseline reports and existing005 branch work; no publication inferred.
- Original financial/authority oracles remain; annotate new sender review. Final-review ruling: M21 changes from mixed-prose WAIT to conservative refusal; preserve old oracle and identify this capability restriction separately. Other64 action expectations remain.
- Raw quotes and original bank rows remain inspectable; suggestions never allocate funds.

## Review Focus

- Conditions or reported speech in new English/Hinglish variations must not create WAIT.
- Owner/third-party/unverified messages must not become active customer promises.
- Currency aliases must preserve token boundaries and exact money, including no-space symbols.
- Generated bank fingerprints cannot silently double-count overlapping exports; skipped rows/assumptions are visible.
- Relative weekdays must use source time, disclose interpretation, and leave seeded historical policy intact.

### Task 1: Safe communication and supported language/money/date

**Files:** domain/document_extraction.py and document_rules.py with application/document_extraction.py compatibility entry point, domain/commitments.py, domain/dates.py, contracts/intake.py, application/intake.py, agents/scripted.py and validation.py; domain/integration tests.
**Interfaces:** extract_document(...,sender_role='CUSTOMER') preserves raw candidates and returns interpreted fields. API defaults sender_role UNVERIFIED, passes it explicitly. Uploaded candidate normalization is separate from raw ledger parsing. Consumed by Task 3 UI/eval.

- [x] Write failing regressions for conditions, reported speech, noncustomer role, no-space rupee quotes, Rs/₹/inr, passive/Hinglish and source-relative weekdays.
- [x] Run focused tests, confirm failures; implement minimal bounded rules, explicit role and domain normalization. Keep historical fixtures unaffected.
- [x] Run focused domain/API checks; update legacy helpers to provide explicit reviewed customer role.

### Task 2: Bank profile and invoice validation

**Files:** new application/bank_import.py, intake_parsing.py, intake.py; contract/integration tests and sample CSV.
**Interfaces:** parse_upload(kind,content) -> rows,errors,warnings; canonical rows feed existing atomic commit. Source hashes/metadata preserve raw bank reference identity. Consumed by Task 3 preview.

- [x] Write failing tests for raw profile, reference/no-reference dedupe, debit rows, mixed/negative/foreign/future values, day-first dates and future/ill-ordered invoices.
- [x] Run RED, implement adapter/validation and actionable preview warnings.
- [x] Run API allocation/replay/overlap tests; no automatic allocations or settlement inference.

### Task 3: Reviewed UX, evals and final verification

**Files:** frontend/src/intake/*, frontend/tests/intake.test.tsx, browser intake/synthetic tests, evals/system and runner input metadata, synthetic pack guide/oracles, reports/system-eval-fixes.md.
**Interfaces:** consumes Tasks1/2 fields and role contract; returns owner-selected review metadata through preview/hash/commit unchanged.

- [x] Add UI regressions for explicit role, preview invalidation, interpreted money/date and bank assumptions.
- [x] Update source-role selections in end-user journeys; add browser challenge route for unsafe wording and supported variants.
- [x] Run new version of 65-case eval plus expanded challenge cases, preserving old expected outcomes and baseline. Record source-role input change.
- [ ] Run complete backend/frontend/typecheck/build and serial Chrome; inspect actual failures before reruns.
- [x] Request one fresh final reviewer per executing-plans; fix demonstrated findings with RED/GREEN, record limitations and final results.
