# Owner experience Phase 3: completed presentation and STUB rehearsal

Date: 25 October 2026. Branch `003-owner-experience`, based on `1f13b86` plus the
accepted local Phase 1/2 work. The owner instructed approval of completed Phase 2,
starting Phase 3 and finishing the UX with improved look and feel. Scope and tasks:
[specification](../specs/003-owner-experience/phase3-spec.md),
[implementation plan](../specs/003-owner-experience/phase3-plan.md).
Status: implementation and engineering verification complete. Phase 2 is
approved under the owner's instruction. The owner subsequently authorized pushing
the completed UX and merging to main on 25 October 2026. The verification below
retains the original pre-publication checkpoint and its failures.

## What changed

The existing casebook now uses one visual hierarchy across all five sections: a
clearer header identity, compact case rail, distinct selected case and tab, consistent
spacing and type sizes, quieter evidence surfaces and a stronger remainder/next-step
hierarchy. Morning Review, message approval, confirmations, history and comparisons
share the same restrained palette. Native controls, keyboard focus and the five-tab
workflow remain in place. No font download, framework or dependency was added.

Saved-copy choices use scenario, clock and saved date with ordinal numbers; exact
copy identity remains available in Saved copy details. Comparison choices use ordered
saved-result labels and completion times. Source buttons show the earlier/later side
and known version; missing metadata stays a saved reference rather than an invented
version. Exact IDs remain under disclosures and still supply every selection/request.
History uses human event titles, retains raw codes/payloads under Event details, and
correctly labels its ascending pagination as Load more history.

## Actual verification

- Fresh frontend baseline: 138 passed. Three new behavior tests failed first, then
  all 32 focused selector/source/history checks passed. Complete frontend: **141 passed**.
- Production build and TypeScript passed. Backend code did not change; the preceding
  Phase 2 **868 passed / one intentional LIVE skip** is retained evidence, not a new
  Phase 3 backend execution. Existing financial, approval and recovery browser checks
  are part of the final browser run.
- Measured text/background contrast: body 13.14:1, muted text 6.03:1, white primary
  action 7.94:1, blue on soft blue 7.07:1, notice 8.17:1, focus against white 5.52:1.
  These are the specified color pairs, not a claim that an automated tool audited
  every possible runtime state.
- Actual desktop and all-five-section 390px/200% screenshots were inspected; the
  rehearsal asserts the root size is **32px**, and checks no sideways page overflow.
  Existing initial case-opening tests still verify full money/action visibility and
  heading focus. The later desktop capture after source inspection uses a different
  scroll position and is not substituted for that initial-opening assertion.
- Two comparison browser journeys passed. The existing busy-owner Morning Review /
  initial-decision viewport journey passed. The first full rehearsal failed because
  its new historical-state matcher incorrectly assumed lowercase text; an unchanged
  application passed after making that matcher case-insensitive. The failure is retained.
- One independent read-only review found no Critical or Important findings. One Minor
  mobile heading issue was also observed during visual inspection: Communication
  review split within a word at 200%. Its mobile type size was adjusted; the refreshed
  capture was inspected and the word now fits intact. No declined judgments.
- Full offline Chrome: **87 passed, two failed, one intentional LIVE skip** (8.5 minutes).
  Both failures are `Isolated backend readiness timed out` in the existing 10-second
  startup helper: result-commit recovery at its second startup, approval-commit
  recovery at its initial startup. The full failed run and traces are retained.
  Both passed unchanged isolated rechecks (**two passed**, 55.2 seconds). All 89
  offline checks have passing evidence across the full run and these rechecks;
  the full run itself remains recorded as failed. No timeout, assertion or product
  deadline was relaxed.

## Rehearsal and owner route

The automated agent executed the original five-minute presentation route on a fresh
fictional STUB/REFERENCE copy. The first passing run recorded **7,491ms for automated
UI actions and assertions**; the final full-suite rehearsal recorded **9,234ms**.
This is not a measured human narration, reading time,
usability result or LIVE latency claim. The original five-minute presenter script
remains in [the demo plan](../docs/ux-review/BUILDER_OF_THE_WEEK_DEMO_PLAN.md).

1. Show the explicit STUB/fixed-date/fictional disclosure and start Morning Review.
2. Open Northstar, inspect the exact invoice/ledger/promise, verify INR80,000 and
   explicitly approve its unchanged saved message. No message is sent.
3. Open Cedar's original payment claim and its recorded contested INR60,000. The
   guidance explains checking bank/accounting records outside PromiseKeeper.
4. Preview and explicitly confirm fictional `PK-003-U1`, inspect the old historical
   result, and reinvestigate. The new saved result has verified INR0 and CLOSE.
5. Compare both originals and the exact new CR-T2 evidence. Assert both saved result
   objects/hashes and history are unchanged; comparison produces GETs only.
6. Verify the case remains open, then explicitly confirm closure through Case actions.
7. Reload and reopen the saved result as a read-only fallback, without another
   investigation. Check all five sections at390px and actual200% text without writes.

Checkpoint timings, screenshots, the initial heading capture, failures and traces are
retained locally in ignored `.runtime/owner-ux-phase3` and `.runtime/e2e`. They are
engineering evidence, not observations from the missing five-owner study.

Reproduction commands used the installed dependencies: `npm.cmd --prefix frontend
run test:unit -- --maxWorkers=1`, `npm.cmd --prefix frontend run build`, and `node
frontend/node_modules/@playwright/test/cli.js test --config tests/e2e/playwright.config.ts`.
The unchanged recovery recheck added `tests/e2e/restart-recovery.spec.ts --grep
'actual process kill after (result|approval) commit'`. LIVE measurement and LIVE
test opt-ins were set to `0` for browser execution.

## Publication verification, 25 October 2026

After the explicit push-and-merge instruction, fresh verification recorded **868
backend tests passed / one intentional LIVE skip**, **141 frontend tests passed**,
and a successful TypeScript/production build. The rebuilt asset names/hashes match
the tested Phase 3 build. Seven focused Chrome publication checks passed in 49.6
seconds: keyboard-only use, 200% text, both comparison journeys, busy-owner Morning
Review, small-screen Morning Review and the complete Cedar demonstration/fallback.
These are fresh publication checks; they do not replace or relabel the earlier
full Chrome run and its two passing isolated recovery rechecks above.

The already-merged baseline PR #2 was fetched before publication; its file tree
matches the UX starting point. The feature branch was fast-forwarded to that merge
without changing product files. Personal local records and runtime artifacts are
excluded from the published file set.

## Completion boundary

The authorized presentation increment completes the existing owner UX and original
Phase 3 demonstration work. Future product features from the backlog remain separate.
No source/result/draft wording, financial rule, approval payload, polling deadline,
backend/API/schema/agent/integration or sending capability changed. No LIVE provider
calls, commit, push or merge occurred during the implementation checkpoint above.
The later publication authorization does not qualify new agents for LIVE use or
replace the five-owner study and formal release acceptance.
