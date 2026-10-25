# Owner experience Phase 3 implementation plan

Spec: [phase3-spec.md](phase3-spec.md). Existing React/TypeScript/CSS and installed
Vitest/Chrome only. Use inline execution with one fresh final code review. No commits.

- [x] T011 Record Phase 2 acceptance and Phase 3/visual scope; run the 138-test
  frontend baseline. Continue accepted work in the same feature checkout.
- [x] T012 Add RED component regressions for friendly copy/result choices preserving
  exact values, exact source inspection/disclosures, and ascending history loading.
  Implement presentation labels/disclosures in DemonstrationPicker, WhatChanged,
  CaseHistory and relevant tests. Keep native controls, request guards and payloads.
- [x] T013 Refine styles.css and small existing semantic markup for the approved
  visual system across header, case rail, briefing, financial/evidence/review/history
  surfaces. Preserve keyboard targets and decision-in-viewport behavior. Build and
  inspect screenshots, then adjust only observed layout/contrast problems.
- [x] T014 Add an automated real-STUB Phase 3 rehearsal in tests/e2e, using existing
  explicit UI commands and scoped reads. Capture checkpoint timings, exact source /
  before-after integrity, saved-result fallback and desktop/mobile/actual200% shots.
- [x] T015 Run complete frontend/typecheck/build and offline Chrome regressions,
  one independent review and material fix pass; record truthfully and finish local UX.

Shared interfaces: T012 preserves exact selection/request identity while T013 styles
existing class names and disclosures; T014 consumes their accessible labels. Original
copy/investigation/source identifiers stay in select values and scoped callbacks.
History event title changes do not change event ordering or command availability.

Review focus: truncated/duplicate friendly labels still identify distinct records;
missing source metadata must not fabricate version numbers; disclosures are read-only;
all selected/history/current states remain textual; font/spacing changes do not push
the decision CTA outside the existing viewport or obscure controls at200%; rehearsal
distinguishes STUB/UI-action timing from LIVE performance or actual human narration.

Workspace: .runtime/owner-ux-phase3/progress.md. Verification log/screenshot artifacts
remain ignored; reports contain no personal accounting information.
