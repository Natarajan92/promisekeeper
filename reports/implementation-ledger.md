# SDD ledger — plan: specs/001-payment-case-mvp/tasks.md (Gate I only)

Authorization: the project owner requested safety-checklist review, private GitHub repository setup, and T001–T020 only, stopping after T020 for review. No Gate II authorization.

## Pre-flight interfaces and rulings

- T007/T008 -> T013/T016/T017/T018: immutable copy/source-version anchors and raw invalid values are shared across evidence, fixtures and reconciliation; validated extraction candidates remain separate from authoritative ledger records.
- T009/T011 -> T017/T019: exact INR integer paise, unknown versus zero and negative overpayment remain explicit. No floats or currency conversion.
- T010/T012 -> T013/T019: aware source/business instants and exclusive next-midnight boundaries; WAIT selects the earliest remaining future boundary.
- T013/T014/T015 -> T016: baseline/update and every variant branch are a versioned approved catalogue. Workflow presets declare future expected outcomes; Gate I must not claim workflow implementation or evaluation.
- T004/T005 -> later gates: isolated temporary storage and network blocking accompany setup; real API/browser journeys remain unexecuted until the APIs exist.
- Ruling: add an explicit prohibition on moving the REFERENCE clock backward within a retained copy — otherwise an expired result could become current after an older event. Replay earlier times only in a fresh copy. Cost if wrong: a future scenario would need a new copy rather than a clock reset.
- Ruling: implement in this newly initialized workspace on feature branch `001-payment-case-mvp`; there is no existing application branch/work to protect, and a second worktree was not requested. No main-branch implementation. Cost if wrong: less filesystem separation during this first increment.
- Ruling: use the SpecKit T### task list and this ledger rather than the executing-plans shell helpers, which expect a different task-heading format. Preserve per-task test/commit evidence directly.
- Ruling: repository creation/initialization is separately authorized by the current user request and supersedes the earlier planning-only prohibition in T001. Remove only the constitution's temporary sync-impact comment as that comment requires before committing; governance principles are unchanged.

## Progress

- T001: complete — workspace directories and Python 3.12 selector inspected; git check-ignore confirmed credentials, runtime/build output, environments and worktrees are excluded. No application test exists yet.
- GitHub: connected profile Natarajan92; sandboxed CLI returned HTTP 401, escalated verification succeeded. Use authenticated CLI outside that restriction for repository operations.

- Repository: private https://github.com/Natarajan92/promisekeeper verified; main baseline bd5357f pushed; feature branch 001-payment-case-mvp checked out. Default sandbox Git ownership differs; read-only commands use per-command safe.directory for this explicitly trusted workspace, not a global setting.
- T002: complete — uv sync and frozen sync succeeded; CPython 3.12.15, SQLite 3.53.1, tzdata/Asia/Kolkata verified; 35 resolved packages in backend/uv.lock.
- T003: complete — Node 24.19.0/npm 12.2.0 dependencies resolved and lockfile produced; frontend build/typecheck succeeded.
- T004: complete — temporary storage, separate clocks, subprocess environment isolation and external socket blocking exercised by test_configuration; all saved demonstrations remain separate. Pytest OS temp was inaccessible; explicit workspace .runtime/pytest-temp resolved it.
- T005: complete — TypeScript/Vite/Vitest and real-API/isolated-DB Playwright lifecycle configuration compiled. Build succeeded; Vitest reports zero test files (no UI tests claimed). Actual API/browser journeys remain unexecuted until Gate III.
- T006: complete — 8 meaningful configuration/redaction failures observed after correcting temporary storage; 11 checks passed after implementation (t006-red.log/t006-green.log).
- T007: complete — evidence contracts/identity tests written and run; 10 unsafe/coercion/ownership/identity failures plus 2 existing passes observed (t007-red.log).
- T008: complete — strict immutable evidence/projection types and copy/source-version commitment identity implemented; full backend suite 23 passed (t008-green.log).
- T009/T010: complete — monetary/date tests written and run; 29 meaningful failures and 7 passes observed (t009-t010-red.log).
- T011/T012: complete — exact arbitrary-size paise, decimal-string encoding, explicit unknowns, aware IST boundaries/relative dates, monotonic reference time, earliest WAIT boundary and stable timeline implemented; full backend suite 59 passed (t011-t012-green.log).

- T013: complete — 5 seed/update/registry contract failures observed; immutable copy builder implemented; full suite 64 passed (t013-red.log/t013-green.log). Baseline three cases/three updates and source/event/arrival times retained.
- T014: complete — 23 registered financial branches encoded with literal expected balances/actions; includes both FV-16 and FV-18 branches/clock events.
- T015: complete — 17 workflow/adversarial branches encoded with expected future outcomes; no approval/recovery state-machine execution claimed. All 40 variants materialized successfully, each with exactly three cases.
- T016: complete — reconciliation/decision/catalogue tests written; 48 functional failures and 43 existing passes observed (t016-red.log). Registry/ownership immutability and all 18 FV groups exercised.
- T017–T019: implementation in progress — eligibility/dedupe/reversal/unknown balance, anchored attribution/claims/replacement and four-action precedence implemented; first full suite 155 passed (t017-t019-green.log). Before completion, broaden targeted coverage for duplicate-version reversal/attribution aliases, unavailable candidates, whole monetary tokens, replacement cycles, per-anchor extraction completeness and subprocess network isolation. These are unresolved concerns, not claimed passes.

- Boundary verification: 8 real failures observed for duplicate-version links/reversals, partial amount tokens, stated-but-omitted amount, unavailable message, skipped clause, replacement cycle and child network bypass; 2 additional failures for reversal credit/negated replacement (boundaries-red.log, reversal-replacement-red.log). Fixed canonical transaction aliases, source/whole-token/clause checks, replacement cycles/positive wording, and shared child startup network guard.
- Ruling: the reversal fixture retains an earlier unlinked INR 25,000 payment that could affect the INR 20,000 promise; VERIFY_PAYMENT is correct there. Isolate the reversal-only test by omitting that unrelated payment; retain a separate assertion that the original case stays VERIFY_PAYMENT. Cost if wrong: the owner sees an additional attribution review, never an unsupported demand.
- T017/T018/T019: complete — final full backend suite 167 passed (boundaries-green.log). Genuine unknown promise amount remains distinct from omitted extraction; explicit reversal rederives credit, duplicate aliases never add a second allocation/credit, per-clause extraction gaps remain LIMITED/VERIFY_PAYMENT, negated/cyclic replacement cannot silently supersede.
- Gate I fixture evidence: test-support report generator executed with 35/35 declared pure-domain outcomes; all 17 workflow presets explicitly UNEXECUTED as application workflows. reports/phase-i.md drafted; T020 remains pending independent review/final verification.
