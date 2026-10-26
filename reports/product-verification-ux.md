# Product verification UX cleanup

Publication authorization, 26 October 2026: the owner subsequently requested pushing the required 007 code, tests, fixtures and product documentation and merging to `main`, while excluding submission documents/folders and personal records. Local/uncommitted statements below describe the original verification checkpoint. Fresh publication checks are recorded in [the publication report](product-007-publication.md); LIVE and human-acceptance limits remain unchanged.

26 October 2026. Local implementation on `007-product-verification-ux`, based on `24eb358`. Publication and production deployment are separate decisions.

The interface now presents PromiseKeeper as an invoice and payment-review workspace. The Upload header has no pack location, repository path, sample filename or demonstration disclaimer. New workspaces start through file uploads. Saved workspaces remain accessible.

## Changes

- Removed fixture creation, scenario selection, clock selection and scenario-update controls from the interface. Removed their React components, unused catalogue requests/types/state and obsolete CSS selectors.
- Replaced sample-download prompts with file-format requirements. Retained file previews, explicit imports, sender review, settlement confirmation, partial/split allocation and payment-coverage review.
- Updated Dashboard, workspace selection/deletion, status messages, Assistant, case guidance, History and import error text. Processing details use a neutral product label. Removed the duplicate raw execution-mode badge from Dashboard.
- Kept a concise internal-verification privacy notice and truthful AI-provider availability. The application still has no authentication, source connectors or customer-sending capability. This work does not establish production readiness.
- Kept database/API identifiers compatible with saved workspaces. Historical source documents and prior evidence are not rewritten. Fictional fixture generators and test APIs remain available to offline automation.

## Review and verification

The clean frontend baseline passed 226 tests. Twelve new route/onboarding checks were observed failing before implementation. Obsolete tests of removed scenario components and fixture selection were replaced with interface-absence, upload and retained recovery assertions. Browser scenario setup now uses test APIs; investigation, comparison, financial and lifecycle assertions remain.

One independent read-only whole-change review found no Critical or Important findings. Its two Minor findings were fixed: a demonstration phrase in the seven-invoice error and an obsolete CSS selector. The invoice-limit API regression failed before the wording fix and passed afterwards; it also proves preview does not create a workspace. A final CSS inspection restored shared selectors that had been grouped with obsolete selectors.

| Check | Result |
|---|---|
| Frontend unit suite | 234 passed |
| TypeScript / production build | Passed |
| Invoice-limit API regression | 1 passed after observed failure |
| Full backend suite | 1,382 passed; one intentional LIVE skip. New invoice-limit regression additionally passed separately. |
| Full serial offline Chrome | 95 passed; one missing-helper-import test setup failure; one intentional LIVE skip. Corrected focused recheck: 1 passed (18.4s). All 96 offline checks have passing evidence across those runs. |
| Desktop and phone surface audit | Passed; 26 screenshots at 1440px and 390px. Seven main desktop and seven phone/expanded-menu images visually inspected. |

The first browser candidate was stopped after 25 passing and seven failing checks, with 64 unexecuted. Four failures used old labels/selectors, two were isolated-backend startup/readiness failures, and one exceeded the existing 80-second recovery-test budget. Original output and traces remain under `.runtime`; no deadlines, readiness budgets or substantive assertions were weakened. A later partial candidate was stopped after six passes and one startup failure for the final CSS rebuild; 90 checks were unexecuted or interrupted. The initial new surface audit failed because its workspace menu remained open between desktop/mobile iterations; the test now closes that menu between iterations.

The intermediate full frontend candidate had 233 passing and one failing check: a test asserted an effect callback before it ran. The corrected check waits for that callback under the existing wait budget; the final suite passed all 234. Earlier candidate failures are preserved locally. The final Chrome suite completed all 97 entries: 95 passed, one was intentionally skipped and one failed because the adapted test lacked its `confirmScenarioEvent` import. Only that test import was corrected; the focused recheck passed without changing product code, deadlines or substantive assertions. The full-run failure remains preserved.

The new real-browser surface audit uploads neutral test records, checks the seven-invoice error and every upload step, visits all five primary pages plus case History, expands workspace details and deletion review, checks for promotional/fixture language and horizontal overflow at 1440px and 390px, and saves screenshots. The existing complete upload-to-investigation-to-approval/late-payment journey passed again on the final build. The final checks also include 200% text, real restart recovery and the real 60-second connection watchdog.

All checks use fictional records and STUB execution. No LIVE calls, real-data imports, customer messages, human-study observations, commit, push or merge were performed.

Final local checks: diff whitespace clean; no files staged; personal accounting and authorization records remain excluded. Product changes are uncommitted and unpushed.
