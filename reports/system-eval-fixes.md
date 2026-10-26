# System evaluation fixes — 25 October 2026

The owner authorized fixing the findings from the [55/65 offline assessment](system-evaluation.md).
Changes remain local on `005-csv-reconciliation-demo`, based on `f1c9a46`, alongside
the earlier upload workflow. Nothing in this stage was committed, pushed or merged.
Only fictional data and STUB agents were used. No LIVE provider evaluation, source
connection, outbound message or actual owner study was performed.

## What changed

| Original gap | Resulting behavior |
|---|---|
| M28: conditional promise produced WAIT | Conditional and unsupported surrounding text is refused for clarification. The parser checks the whole supported promise statement, body and email subject. Header-like body lines and quoted history cannot silently disappear. |
| M30: reported quotation produced WAIT | Reported/quoted promises cannot become the customer's direct commitment. Extra English/Hinglish attribution and condition regressions cover variations beyond the original examples. |
| M32: owner message became a customer promise | Every communication preview requires an explicit sender review. API default is UNVERIFIED; only CUSTOMER can provide active claims/promises. Other roles can be explicitly attached as context. Changing the role invalidates the preview; replacing a file resets role, date and context selection. |
| M23/M24: currency aliases and touching symbol/amount failed downstream | Reviewed uploaded quotes support INR, Rs., lowercase notation and the rupee symbol, including no-space forms. Exact original tokens remain visible; interpreted currency is INR. Domain provenance checks still reject truncated or unrelated tokens. |
| M25: next Friday unresolved | Reviewed uploads resolve the strictly next weekday after the source's local date, with the same weekday seven days later. Preview displays the resolved date and rule. The run date and historical seeded policy do not replace that source clock. |
| M26/M27: Hinglish/passive promises refused | Bounded direct first-person Hinglish and explicit passive future payments with money/date are supported. These rules do not claim general language understanding. |
| I11: ordinary bank export rejected | Receipts accept Date/Description/Credit plus documented optional columns. Preview explains date/currency assumptions and skipped debit rows. Original files/rows remain inspectable. Settlement starts UNKNOWN; allocations still require owner confirmation. |
| I12: future-issued invoice accepted | Future-issued outstanding invoices and due dates preceding issue dates are refused atomically. Date-only due dates use the existing end-of-day policy, including same-day invoices. |

Final review also identified a duplicate-funds path: the same deposit could be
imported first without a reference and later with a real reference. Ambiguous
overlap with a generated fingerprint now rejects the entire import for review,
in either order and within a batch. Separate genuine bank references remain
distinct. A BANK- fingerprint is explicitly labeled as a source identity, never
as a bank UTR or evidence of settlement.

Sender review is an owner assertion, not authenticated identity. A migration
invalidates current advice/approval authority for older unreviewed uploaded
communications while retaining their immutable originals and result history.
Those workspaces need a new import from the originals with each sender reviewed;
the UI explains this and blocks reinvestigation until resolved. Existing legacy
operation receipts retain narrowly scoped, full-payload-hash replay support.

## Evaluation contract and results

The [final primary run](system-evaluation/fixes-primary-verified-20261025/results.json)
records **65 PASS, zero FAIL/ERROR/UNEXECUTED**, using dataset v1.4. Candidate source
fingerprints, exact inputs, expected values and observations accompany each run.

This is **64 unchanged original action expectations plus one deliberately revised
refusal policy**, under the new sender-review input contract. M21 previously
expected WAIT from a document mixing an instruction with a promise. Full-message
validation now refuses that unsupported mixed prose. Its earlier expectation is
retained in `previous_contract_expected` and the frozen baseline artifacts. This
is a documented capability restriction, not a claim that the original 65 inputs
and action oracles all stayed unchanged. Financial/owner-control invariants remain
required; preview refusals must be atomic.

The [final expanded run](system-evaluation/fixes-extended-verified-20261025/results.json)
adds 25 authored challenges for 90 total: **90 PASS, zero FAIL/ERROR/UNEXECUTED**.
Both processes exited zero. All recorded product-file hashes match the current
code, and both runs have the same candidate fingerprint.
The primary 65 cases are included in those 90, not an additional independent set.
The sets are author-inspected challenges, not blind holdouts or estimates of
real-world accuracy. Passing STUB scenarios does not qualify a LIVE model.

## Regression and review evidence

| Verification | Result |
|---|---|
| Focused final parser, bank, legacy and synthetic-pack checks | 63 passed |
| Agent boundary, parser, legacy and synthetic recheck after module move | 84 passed |
| Primary / expanded system evals | 65/65 and 90/90 passed, with the contract changes disclosed above |
| Full backend | 1,011 passed; one intentional opt-in LIVE skip; process exit zero |
| Frontend | 154 passed across 17 files |
| TypeScript and production build | Passed |
| Full serial Chrome | Completed in the [multi-page UX follow-up](multi-page-ux.md): 95 passed / one intentional LIVE skip; failed candidates retained there |
| One independent final review and bounded rechecks | Two Important and one Minor findings resolved; seven final subject/header checks passed independently |

Regressions were observed failing before fixes. Preserved local evidence includes
the initial 24 communication failures, four bank/date failures, two legacy replay/
migration failures, the adjacent Rs. amount failure, 13 final-review regressions,
the file-replacement role failure, and six subject/header failures. Focused final
checks passed after the corresponding fixes; assertions and product deadlines
were not weakened. An early expanded run found RS.1000 unsupported (84/85 passed),
which was reproduced in a unit regression and corrected.

The first full backend attempt found one architecture regression (1 failed,
1,010 passed, one opt-in LIVE skip): agent validation imported the pure parser
through the application layer. The parser/rules now live in the domain layer;
intake retains a compatibility entry point, and agents import the pure module
directly. The existing agent safety test remains unchanged. Fresh full backend
and system eval runs follow this correction; earlier passing eval artifacts are
retained as pre-move candidates.
The same reviewer independently confirmed the pure dependency chain and passed
all four agent-safety checks in this bounded recheck.

The first focused Chrome run had two failures during concurrent evaluation;
an unchanged serial recheck passed all four journeys. Both attempts are retained.
The new browser journey uses actual file selection and preview/commit, raw bank
credit/debit data, explicit settlement/allocation, unsafe source refusals, a
rupee/weekday promise, a Hinglish promise and Morning Review. It checks exact
saved paise, WAIT, OPEN lifecycle and zero owner approvals.

## Limits and owner rehearsal

The [updated sample guide](../docs/demo-import/README.md) describes the workflow
and [synthetic upload pack](../docs/demo-import/synthetic-pack/START-HERE.md) exercises
54 files, 36 intentional refusals, three bounded explorations and six financial
oracles. The pack's initial verified remainder stays INR 235,000.75.

The parser deliberately refuses unfamiliar promise subjects, footers, quoted
history and mixed prose. A real-language extractor would need a separate approved
LIVE evaluation. Supported bank files remain a documented profile, not arbitrary
mapping, PDF/OCR or a live feed. Different descriptions/dates can prevent detecting
the same bank deposit; identical genuine deposits without distinct references
cannot be distinguished. Use stable real references in fictional rehearsals and
review overlap rather than manufacture a second receipt.

INR-only scope, six invoices per imported workspace, file/row limits and manual
settlement/allocations remain. No source-role authentication or actual human
usability results were established. Owner approval/copy and explicit closure
remain necessary; nothing is sent automatically.
