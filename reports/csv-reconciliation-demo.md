# Separate-file workflow verification — 25 October 2026

Branch `005-csv-reconciliation-demo`, based on main `f1c9a46`. The owner authorized
the complete six-step fictional upload workflow, separate communication documents,
continuous implementation and final combined tests. The original 30-minute cutoff
was superseded by the owner's choice to complete and test every step. This increment
is local and uncommitted; it has not been pushed or merged.

## Result

The owner can import customer and invoice CSVs, upload receipts independently,
reuse reviewed accounting allocations, inspect explained matching suggestions and
confirm partial or split allocations. Matching does not assign money automatically.
Generic company suffixes or a shared city alone do not suggest an unrelated customer.

Remittance emails, customer emails and WhatsApp messages are separate documents.
The bounded offline parser reads actual text, preserves original quotes and dates,
and keeps claims separate from settlement. New evidence invalidates earlier payment
coverage, recommendations and approval. Explicit coverage review feeds existing
Morning Review, evidence inspection, draft editing/approval/copy and case closure.
Original documents and historical results remain inspectable after updates/restart.

The [sample walkthrough](../docs/demo-import/README.md) provides ten independent
files. Initially EC-101 requires verification, EC-102 waits for a promise and AD-201
supports follow-up. A later ECON-T3 receipt, explicitly allocated and reviewed,
resolves the claim and supports zero/CLOSE; the owner separately confirms closure.

## Verification

| Check | Observed result |
|---|---|
| Full backend | 923 passed; one intentional LIVE skip |
| Full frontend | 153 passed on the final version |
| Source-date fallback | RED regression confirmed; final full suite includes the IST-preserving fix |
| TypeScript and production build | Passed, including final presentation polish |
| Full serial offline Chrome | 91 passed; one intentional LIVE skip |
| Actual six-step Chrome upload journey | Passed in the full suite and again after the final promise-parser refinement, including original-source inspection, approval/copy, delayed settlement, explicit closure and reload |
| Desktop and 390px / 200% inspection | Screenshots inspected; no page-level horizontal overflow |
| Fresh independent code review | Three Important findings reproduced and fixed with RED/GREEN regressions |

Commands: `backend/.venv/Scripts/python.exe -m pytest backend/tests -q` with a
unique `--basetemp` under the ignored runtime directory; `npm.cmd --prefix frontend
run test:unit -- --maxWorkers=1`; `npm.cmd --prefix frontend run build`; and
`node frontend/node_modules/@playwright/test/cli.js test --config tests/e2e/playwright.config.ts`.
All checks use STUB; the intentional LIVE test remains disabled.

The review found refusal/conditional wording being interpreted as a positive
promise, mixed-invoice attribution and a preview/materializer candidate-limit
mismatch. Preview now rejects these inputs before confirmation. Only explicit first-person future payment wording becomes a
promise; a due-date instruction or stated need to pay does not. Regression tests
cover all three, source currency grounding, malformed amounts, timezone retention,
receipt/invoice caps, atomic batch rejection, replay, scoped originals, deletion,
restart, uncertain browser operations and approval revision barriers.

Original failures are retained in ignored runtime logs. An initial full backend run
had 907 passes, three failures and one intentional LIVE skip: two CLI tests received
an unsupported test environment variable; a preservation subprocess returned HTTP 404 during a run that overlapped
shared-temp cleanup. A concurrent focused run also produced Windows file-lock setup errors. Subsequent runs remove the
unsupported variable and use distinct temp directories; no product assertion or
deadline was weakened. Early browser walkthrough failures were selector assumptions
and then an overly broad ambiguity guard rejecting a separate advisory sentence;
the final check distinguishes payment requests from an actual quoted claim.

## Limits

Fictional local demonstration only, without authentication or live source
connections. Positive INR values, fixed CSV headers, six invoices per workspace,
256 KiB / 100-row CSV uploads, 8,000-character communication documents and at most
30 quoted claims/promises per document. XLSX/PDF/OCR, arbitrary column mapping,
general message understanding and free-form invoice chat are outside this increment.
Only explicit first-person future wording creates a promise. Negative/conditional/ambiguous payment wording and conflicting invoice references
require an individual unambiguous message. Context-only unsupported text remains
LIMITED under existing missing-extraction checks. Currency stays verbatim; only
exact `INR` is supported by the money rules.

Allocation and coverage confirmation represent owner assertions for fictional
records, not independent bank authentication. No message is sent. No LIVE provider
qualification or human usability study was performed; browser walkthroughs are
automated rehearsals. This does not qualify the uploaded-input workflow or the planning supervisor
for LIVE use. No new LLM role or constitutional exception is introduced.
