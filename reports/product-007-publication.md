# Product 007 publication verification

26 October 2026. Verification of `007-product-verification-ux` against published base `24eb358`, for the owner's instruction to push required project changes and merge to `main` while excluding submission documents and folders.

## Resulting behavior

New workspaces begin with file uploads; saved workspaces remain accessible through a neutral workspace picker. The interface no longer exposes fixture creation, scenario updates or pack-promotion controls. Consequential actions retain their explicit review, exact-version approval and recovery safeguards. Dashboard greets the owner with "Namaste Anand".

Email and WhatsApp import review now offers a recoverable choice when recognised payment wording was mistakenly selected as supporting context. **Review payment wording** requests a fresh preview using the original content and reviewed details; the user must review and explicitly confirm that preview before anything is saved. Conditional or ambiguous wording retains its refusal behavior.

The revised fictional upload pack supplies two presenter stories: a Lotus follow-up-to-payment journey and Arun's payment claim without matching bank evidence. Later receipts require explicit allocation, coverage review, a fresh investigation and owner-confirmed closure. No customer message is sent.

## Fresh offline verification

All application checks used fictional records and STUB agents. These results apply to the combined publication candidate; earlier local checkpoints and their original failures remain in the linked source reports.

| Check | Result |
|---|---|
| Full backend, final unchanged rerun | 1,391 passed; one intentional LIVE skip |
| Full frontend unit suite | 240 passed |
| TypeScript | Passed |
| Production build | Passed |
| Full serial offline Chrome | 100 passed; one intentional LIVE skip |
| Fresh independent read-only whole-change review | No Critical, Important or Minor findings |
| Required-file and submission-preservation audit | Candidate hashes unchanged; local submission hashes preserved; no submission file tracked |

The first fresh backend run had **1,390 passes, one failure and one intentional LIVE skip**. The approve/edit parameter of `test_same_revision_race_has_one_durable_winner_and_no_stale_side_effects` raised `sqlite3.OperationalError: database is locked` while acquiring `BEGIN IMMEDIATE` under the existing 250 ms SQLite busy timeout. Transaction code, the review service and race tests are unchanged from the published base. The original database passed read-only integrity and foreign-key checks; it contained the winning edit and no approval record. The exact scheduling or I/O condition behind the contention was not established.

The same failing parameter passed unchanged in isolation (**1 passed**), and the entire concurrency module then passed unchanged (**13 passed**). The final full backend rerun used a separate temporary directory. No code, test assertions, SQLite timeout, test deadline or retry budget was altered to obtain these results. The original failed log, database and subsequent logs are preserved locally under `.runtime/publication-007/`. Disabling pytest's cache provider produces the existing `cache_dir` configuration warning.

The full serial Chrome suite completed all 101 entries with 100 passes and one intentional LIVE skip. It includes the complete upload and two-story journeys, all three message-recovery forms, desktop/mobile interface wording, actual process-kill recovery and the real 60-second watchdog. These are automated browser checks, including simulated personas; they are not human usability validation.

## Scope and exclusions

Publication includes the application changes, their regression tests, the revised fictional fixtures, relevant design/workflow documentation and product verification reports. All files under `submission/`, including Markdown/DOCX exports, evidence appendices, images and rendering tools, are excluded. Their hashes were checked against the pre-publication manifest. Personal authorization/accounting records, runtime data and credentials are also excluded. The staged path list and canonical tested tree are retained locally for comparison with the merged result.

No new LIVE calls, real customer-data imports, source connectors, customer sending or human usability observations were performed. The planning supervisor and revised two-story pack remain unqualified by LIVE evaluation. Formal human acceptance and production readiness remain separate obligations. The earlier six-case LIVE rehearsal and its discrepancy are historical evidence, not a result of this publication.

## Detailed evidence

- [Product interface cleanup](product-verification-ux.md)
- [Message import recovery](message-upload-confirmation.md)
- [Two-story fictional upload pack](two-scenario-course-pack.md)
- [Historical six-case LIVE rehearsal](course-demo-live-rehearsal.md)
- [Independent offline evaluation and remaining limits](system-eval-fixes.md)
