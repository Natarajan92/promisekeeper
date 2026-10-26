# Multi-page business UX recovery

The interrupted work is complete locally on `005-csv-reconciliation-demo`, preserving the earlier uncommitted upload and evaluation changes. The approved Bright fintech interface now separates Dashboard, Upload records, Cases and individual case pages, Assistant at work, and Your approvals. Hash routes retain deep links and browser navigation; the shared workspace store supplies case data and decision counts across pages. Final engineering checks are green; owner visual acceptance, LIVE qualification and publication remain separate.

Publication authorization, 26 October 2026: the owner subsequently requested pushing the completed work to GitHub and merging to `main`. This authorizes publication of the completed 005 work; the local/uncommitted statements below describe its verification checkpoint. The LIVE and human-acceptance limits remain in force.

Fresh publication checks passed before committing: 109 focused backend integrations covering the course pack, evaluation fixes, upload robustness and existing synthetic pack; 226 frontend unit checks; TypeScript/production build; and five Chrome journeys covering the course pack, legacy rehearsal and keyboard/200% accessibility. The retained full-suite results are listed below. Personal records and runtime artifacts stay excluded from the publication.

The recovery checkpoint found Tasks 1, 2, 3, 5, 6 and 8 completed in the saved work ledger. Task 4's Dashboard/case implementation was present, with browser navigation migrations unfinished. Task 7's complete browser demonstration and Task 9's final review, verification and reporting remained. The original session's three-hour target had already elapsed during its account-limit interruption.

## Behavior and demonstration

The Dashboard computes balances from eligible open INR cases and identifies recorded, unknown and other-currency amounts. Upload retains read-only previews, explicit import/allocation/coverage confirmations and sender review across six steps. Case pages retain original evidence, saved findings, reminder review, history, comparison, closure and reopening. Approvals reuses the existing exact-version decisions and copy handoff. The Assistant page explains the AI and rule-based roles and retains technical details behind disclosures. Nothing sends a customer message.

The compact fictional pack is in [course-demo/START-HERE.md](../docs/demo-import/course-demo/START-HERE.md). Its generator dates files relative to the demonstration day. Six distinct customer stories cover FOLLOW_UP, WAIT, VERIFY_PAYMENT, CLOSE, partial payment, a conditional-message refusal and a later-statement finale. Initial expected balances total INR 250,500.00. The independent oracle is generated alongside the files, and the existing larger synthetic pack is retained.

One LIVE API rehearsal had already completed before recovery. Its [saved-artifact report](course-demo-live-rehearsal.md) preserves the Meera recommendation difference, matching balances, Arun finale, premature sequencing and narrower evidence scope. No LIVE run was repeated during recovery. The generator and presenter script now warn about the observed difference and use Lotus for the LIVE approval/copy example. Agent qualification and formal human acceptance remain pending.

## Review and fixes

A fresh independent whole-change review compared the stage against its pre-UX snapshot and found three Important issues and no Critical issue. Recovery added regressions and corrected each:

1. Arbitrary trailing prose could be accepted as a signature, converting hedged wording into a firm commitment. Signature support now uses a conservative positive name/role grammar and qualifier screening; unrecognized prose fails closed.
2. **New upload workspace** continued the selected imported workspace. That action now clears the selection and opens Customers in a separate workspace scope; ordinary Upload still continues the selected workspace.
3. The case story could reuse an earlier investigation's nonreceipt/fulfillment conclusions after evidence or time changed. Those conclusions now require a current result; earlier checks are labeled with their saved time, and promise/questions request a fresh check.

Laptop screenshot inspection then found an internal allocation key labeled as a bank reference and long explanation source IDs displayed by default. Two additional failing UI regressions demonstrated these. The story now uses the saved original transaction reference; explanation source identifiers sit behind the **Why we think so** disclosure, retaining the same exact-source controls and version access. The focused UI recheck passed all 22 tests.

The pre-recovery backend sweep also fixed 20 documented issues covering courtesy lines and invoice-label safety, verbatim UTF-8 email evidence, amount grouping/INR notation, date/header/blank-row errors, bank dash cells, unsupported encoding explanations and STUB wording. Existing recorded regression and review evidence was preserved.

## Verification

Final verification is complete with the evidence chronology below. The initial recovery frontend run passed 221 tests, TypeScript and the production build; the first backend run passed 1,243 tests with one intentional LIVE skip, before the final signature regressions were collected. Both offline system evaluation sets passed after the initial signature fix: [primary 65 scenarios](system-evaluation/ux-recovery-primary-2026-10-26/results.md) and [extended 90 scenarios](system-evaluation/ux-recovery-extended-2026-10-26/results.md), with no failures, errors or unexecuted scenarios and unchanged oracles. The later bounded qualifier extension adds Probably/Likely/Presumably/Proposed screening; none occurs in either dataset. The final backend run includes all 139 new signature regressions (292 document checks).

The first full browser baseline recorded **82 passed / 12 failed / one intentional LIVE skip**. Seven failures were unfinished route/status-locator migrations; five were isolated-server readiness failures while backend/frontend checks ran concurrently. The migrations were corrected without weakening assertions or changing timeouts. Original failed logs and traces remain preserved. Final counts, clean serial-browser evidence and screenshot inspection appear below.

The new complete course-demo Chrome journey passed independently (one test, 17.9 seconds of test work / 28.9 seconds including setup). It additionally selects an existing imported workspace, uses **New upload workspace**, confirms a different workspace is created, and verifies the original records remain unchanged. The first wrapper invocation stopped on an npm stderr notice before tests; its log is retained and the wrapper now uses actual native exit codes. The journey passed again in the final suite after the visual corrections above.

The first ordered candidate passed 1,382 backend checks, then recorded 225 frontend passes and one stale route assertion: the test still expected `#/upload` after the deliberate new-workspace action began targeting `#/upload?step=1`. That navigation expectation was corrected; all nine routing checks passed. A serial recheck of all 14 affected browser flows then passed, including every earlier failed flow, the source disclosure and the complete course journey. The complete ordered pass was restarted, preserving that failed candidate rather than presenting it as clean.

The repeated ordered pass completed backend verification: **1,382 passed / one intentional LIVE skip**, exit zero, in 538.98 seconds. Frontend verification passed **226 tests across 25 files**, followed by TypeScript and the production build. The retained backend warning is the existing pytest `cache_dir` warning when cacheprovider is disabled.

That browser candidate recorded **94 passed / one failed / one intentional LIVE skip**. The older Phase 3 rehearsal still tried to click an explanation source without first opening the new disclosure. Two disclosure-navigation steps were added; all exact-original, focus-return, immutable-hash, read-only comparison, explicit closure and 200% assertions remain. This browser-test-only correction leaves product, backend/unit tests and build inputs unchanged. Their passing results were retained and the entire serial Chrome suite was rerun. Accordingly the evidence is combined ordered verification with preserved failed candidates, not a claim that a single clean batch passed every suite.

The corrected rehearsal passed its focused recheck, then the final **full serial Chrome passed 95 tests with one intentional LIVE skip**, exit zero, in 10.8 minutes. No product code changed between the green backend/frontend/build checks and that browser run. All five earlier startup-readiness failures passed in the final serial run; no timeout was raised.

| Final check | Result |
|---|---|
| Backend | 1,382 passed; one intentional opt-in LIVE skip |
| Frontend unit | 226 passed across 25 files |
| TypeScript | Passed |
| Production build | Passed |
| Full serial Chrome | 95 passed; one intentional opt-in LIVE skip |
| Offline system evaluations | Primary 65/65 and extended 90/90 passed, at the disclosed checkpoints |
| Whole-change review | Three Important findings corrected with regressions; Minor observations retained below |

Final local evidence: `.runtime/ux-final2-backend.log`, `ux-final2-unit.log`, `ux-final2-typecheck.log`, `ux-final2-build.log`, and `ux-final3-chrome.log`. Failed candidates remain in `recovery-chrome-baseline.log`, `ux-final-unit.log`, `ux-final2-chrome.log` and their original browser traces. The browser lock was released after the successful run. This also closes the earlier evaluation-fix report's unrecorded final browser verification.

## Test migration

Existing behavior assertions remain. Migrations change page/section navigation, scope co-located controls/notices to the relevant card, and update deliberately changed headings or INR display formatting:

- Frontend: `cases`, `findings`, `history`, `operation-lifecycle`, `presentation`, `ux`, `whatChanged`, and the new workspace-deletion checks.
- Browser: `accessibility`, `case-review`, `comparison`, `deadline-recovery`, `draft-review`, `history-lifecycle`, `investigation`, `personas`, `restart-recovery`, `ux-completion`, `ux-flow`, `intake`, `reviewed-intake`, and `synthetic-pack`.
- New tests cover routing, shared workspace state, Dashboard totals, case pages, the upload stepper, approvals, the assistant and the complete course-demo browser journey.

No existing safety assertion or product deadline was removed or relaxed. The review sampled exact-copy, stale-result, original-source, comparison, keyboard, deletion/recovery and upload assertions. The complete suites supply execution evidence separately.

## Visual evidence

The course journey captures Dashboard, Upload, Cases, Meera's case, Approvals, Assistant and Arun's finale at 1440×900, each with a full-page companion. All seven pages were inspected after the presentation corrections; the story shows `UPI-552104` and `ARUN-T9`, the source disclosure starts closed, controls and amounts are readable, and the automated captures assert no horizontal overflow. Local artifacts are `.runtime/ux-shots/course-demo-<page>.png` and `course-demo-<page>-full.png`, where page is `dashboard`, `upload`, `cases`, `case`, `approvals`, `assistant` or `arun-finale`. Earlier Upload step 3/5 and narrow/200% captures are retained separately. These are automated inspections, not human-study observations.

## Decisions and limits retained

The prior work's tradeoffs remain explicit: duplicate case-detail GETs/queue computation, non-INR locale grouping, partial-load badge counts with errors shown on Approvals, count-based Match payments invalidation, transient Assistant loading wording, and persistent deletion status until the next switcher action. These have no demonstrated material finding in the final review.

The remaining Minor observations carried from the earlier task reviews are recorded rather than silently treated as fixed:

- The `max(default=-1)` parser guard has no dedicated direct regression, although public extraction paths are covered.
- The demo generator retains an unused `as_of` argument in `expected_action`, a hardcoded Lotus formatting example, and a presenter-guide test that checks order rather than all prose.
- Case details, approval queues, technical attempt details and upload overviews can be fetched/computed redundantly.
- Deletion status can persist until the next switcher action; deletion errors appear globally beside case notices.
- A partial case-load failure can undercount the approval badge; explicit failure/retry guidance appears on Approvals.
- The Assistant can briefly show its no-review wording while loading; MorningReview supplies the live-region status.
- Upload completion requires all open results CURRENT; sender-review guidance lacks a direct step-1 link; Match payments invalidation compares open-receipt counts and can miss an allocate-one/import-one substitution.
- Some encoded MIME/HTML combinations can receive a less specific refusal reason under the single-span evidence constraint.
- Conservative invoice-label screening can refuse genuine-looking IDs containing qualifier words, such as `UNPAID-1`.

The earlier deferred invoice-label loopholes, false STUB personal note and overdue-day pluralization were fixed in the backend sweep, with regressions; they are not outstanding findings.

Recovery deliberately narrowed the signature heuristic to one-to-three capitalized ASCII name words or bounded accounts/finance roles after the safety finding. All-caps/lowercase personal names, longer signatures, ampersand company forms and unfamiliar prose can be refused; legitimate sources may therefore need a supported fictional representation. Original source evidence is never silently edited. This is a bounded lexical check, not sender authentication or general language understanding. Unsupported email encodings/formats remain clearly refused.

Work stays local and uncommitted. Publication, another LIVE rehearsal, real customer data/connectors and formal human acceptance are outside this recovery.
