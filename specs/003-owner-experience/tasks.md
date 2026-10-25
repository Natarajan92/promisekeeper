# Tasks: owner experience Phase 1

Spec: [spec.md](spec.md). Plan: [plan.md](plan.md). Baseline: `1f13b86`.
Owner authorization: “Improve the ux as per plan.” Implementation stops at this
phase's owner review; these tasks do not activate original AC-28/FR-024.

- [x] T001 Record approved presentation scope, synchronize existing governance approval
  and release wording, and run the complete installed frontend baseline.
- [x] T002 [US1] Add RED regressions and implement decision-first Findings, optional
  developer details and truthful investigation/drafting/progress states. Depends T001.
- [x] T003 [US1] Add RED regressions and implement explicit case-heading focus (including
  same-case opening), stable background focus and compact completed briefing. Depends T002.
- [x] T004 [US1] Add RED feedback regressions and implement truthful local-save/confirmed
  delivery wording with unchanged mutation payloads. Depends T001.
- [x] T005 Verify full component/typecheck/build and serial offline browser journeys,
  financial/approval/recovery regressions, screenshots and one independent whole-change
  review. Fix material findings with RED/GREEN coverage; report actual outcomes and
  leave the local phase ready for owner review. Depends T002, T003, T004.

Traceability: T002 → UX-AC-01/02/04/05/07; T003 → UX-AC-03/07;
T004 → UX-AC-06/07; T005 → all criteria and existing source/approval/recovery invariants.
