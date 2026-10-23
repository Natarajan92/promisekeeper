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
