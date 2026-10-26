# PromiseKeeper system evaluation — 25 October 2026

Follow-up: [the fix verification report](system-eval-fixes.md) records the subsequent
product changes. This document and its 55/65 baseline remain historical evidence.

The offline evaluation is designed to answer whether the owner can trust invoice
money, communication evidence and the next action. Application acceptance must
remain blocked when unsupported evidence produces confident advice, even if all
ordinary regression tests pass. No product changes were made during this assessment.

## Scope and reproduction

Candidate: local `005-csv-reconciliation-demo` from `f1c9a46`, including the existing
uncommitted upload workflow and synthetic pack. Exact product source hashes are
in the machine report. Existing feature changes were preserved; nothing was
committed, pushed or merged. All inputs are fictional and all agents are STUB.
No LIVE provider/source connection or actual human study was performed.

The [versioned dataset](../evals/system/cases.json) contains 65 independently
authored challenges: 36 communications, 12 imports, nine allocation cases and eight
owner workflow cases. Expected money uses literal paise; product derivation code
does not compute the oracle. The author inspected the implementation, so these
are new challenge inputs, not a blind statistical holdout. See the
[runner instructions](../evals/system/README.md) to reproduce the full run.

Reports preserve each case's intent, expected behavior, automatic failures,
actual observations, failed checks, duration, business day and dataset/candidate
fingerprints. A report's overall PASS requires every case to pass; safety failures
cannot be averaged away. No arbitrary two-second/95-percent target from the
attached RAG example was adopted.

The corrected [machine report](system-evaluation/acceptance-20261025/results.json)
and [case table](system-evaluation/acceptance-20261025/results.md) record **55 passed,
10 failed, zero harness errors and zero unexecuted out of 65**. The overall eval
fails, as intended when these gaps exist. All **52 contract cases passed**;
**three of six safety challenges passed**, and **zero of seven desired capability
challenges passed**. The capability set deliberately targets suspected limits;
its result is not an estimate of real-world success rate.

The ten failures comprise three unsupported WAIT recommendations, one accepted
document whose investigation becomes INCOMPLETE, five other language/format
limitations, and the future-invoice validation decision. No tested case produced
an observed wrong monetary amount, duplicate allocation, automatic approval or
automatic closure. Missing result money in M24 is an incomplete result, not a
passing money check.

| Owner intent | Expected behavior | Automatic failure | Required success / observed |
|---|---|---|---|
| Import trustworthy records | Preview before committing; reject invalid batches atomically | Silent partial/invalid writes | Every contract case passes; invalid-batch checks passed |
| Know where money belongs | Suggest using evidence; owner confirms allocations; preserve exact INR paise | Wrong currency/money, duplicate or foreign-workspace allocation | All nine allocation challenges passed |
| Decide whether a promise deserves WAIT | Preserve conditions, speaker and quoted evidence | Unsupported confident WAIT | All safety challenges must pass; three of six failed |
| Retain control of action | Stale advice loses approval; closure requires explicit owner confirmation | Automatic approval/closure or stale authority | All eight workflow challenges passed |

Requirement keys in the dataset link cases to these owner intents. Passing the
contract subset does not compensate for the three unsafe advice outcomes. Whole
in-process scenario duration was p50 **891 ms**, p95 **1,344 ms**, max **5,094 ms**;
this includes setup/persistence and is not browser or LIVE-model latency.

## Findings

| Priority | Cases | Observed gap | Recommended next change |
|---|---|---|---|
| P1 | M28 | “We will pay INR 1000 by [date] after finance approval” becomes an active promise and WAIT. The condition is lost. | Reject or explicitly qualify conditional wording; require clarification before WAIT. |
| P1 | M30 | `He said: "We will pay ..."` becomes the uploader's active customer promise and WAIT. | Preserve quotation/attribution; distinguish a customer commitment from reported speech. |
| P1 | M32 | An owner-side sender declared in the eval is treated as a customer promisor and generates WAIT. Sender role/identity is not established by the imported customer record. | Capture participant role and customer identity; require review when attribution is unverified. |
| P1 | M24 | `₹1000` without a space passes preview/import but the investigation becomes INCOMPLETE / INVALID_INVESTIGATOR_OUTPUT. | Make preview and saved extraction validation agree; return a useful clarification instead of accepting a document that cannot be investigated. |
| P2 | M23, M25 | `Rs. 1000` and relative weekday wording do not deliver the intended future-promise behavior; they return VERIFY_PAYMENT. | Normalize supported currency/date expressions with evidence; retain clarification for unresolved dates. |
| P2 | M26, M27 | Newly uploaded Hinglish and passive-voice promises are refused. The seeded Hinglish demo does not establish general uploaded-message coverage. | Add reviewed language examples and evaluate actual extraction separately from seeded packets. |
| P2 | I11 | An ordinary Date/Description/Credit bank export is rejected because exact demo headers are required. | Add a previewed column-mapping step or clearly supply a conversion template. |
| Product decision | I12 | An invoice issued in 2099 is accepted into today's outstanding-invoice workspace. | Decide whether to reject or explicitly flag future-issued records before committing. This is a desired validation criterion, not a previously documented rejection contract. |

M28/M30/M32 are unsupported confident advice failures. None of these examples
changed the INR 1,000 balance, approved a draft, closed the case or sent a message.
The owner could still catch the problem during evidence review, but that does not
make the recommendation correct. Prioritize these failures before expanding the
happy-path demo.

Refused messages in M26/M27 were not saved; an investigation of the remaining
ledger still showed FOLLOW_UP. That result must not be interpreted as an
understanding of the rejected promise. Currency/date cases can finish an
investigation while retaining unresolved facts; COMPLETE is not certainty.

## End-to-end functionality and regression evidence

The API challenges use the real app with fresh databases, actual preview/commit,
ledger review, background investigation, multi-agent case workflow and saved
results. They cover partial allocation, over-receipt/over-invoice limits, pending
and reversed receipts, operation replay, unconfirmed settlement, read-only
previews, stale revisions, scope isolation, stale approvals, explicit closure and
scoped deletion. UNKNOWN status is allocatable only after the owner explicitly
attests settlement. These tests do not establish that a human attestation is true.

The complete Chrome suite additionally exercises rendered pages, file selection,
six invoices with split paise/duplicate exports, Morning Review, source evidence,
exact draft approval/copy, later receipt resolution, immutable history, accessibility,
reload/restart recovery and concurrent/stale browser controls.

- Full pre-eval backend candidate regression: **941 passed, one intentional LIVE skip** (619.33 s).
- New evaluator mutation/harness checks: **12 passed**, including external-network blocking and explicit STUB configuration. These are separate from the above collection.
- Frontend unit tests: **153 passed**.
- TypeScript/production build: **passed on isolated rerun**. The first concurrent build failed with Windows VirtualAlloc errno 1455/out-of-memory; original log retained. No code or compiler assertions changed.
- Complete Chrome suite: **93 passed, one intentional LIVE skip** in one full run (10.9 minutes). The six-invoice synthetic upload route passed in 19.9 seconds; context-only route in 5.5 seconds. Playwright's machine record says `status: passed`, `failedTests: []`. PowerShell returned wrapper status 1 after classifying Node's NO_COLOR/FORCE_COLOR stderr warning as NativeCommandError; there are no failed browser tests. The wrapper warning is retained separately from test outcomes.

## Results provenance and limits

The first baseline and two intermediate runs remain under
`reports/system-evaluation/`. They exposed harness issues: shell encoding corrupted
one currency symbol; a closure setup retained context that correctly blocked
closure; an expected rejection ignored explicit settlement confirmation; a
terminal INCOMPLETE investigation was initially misreported as a harness timeout.
These inputs/observations were corrected without changing application code or
silently overwriting the earlier evidence. The final acceptance denominator uses
the corrected dataset and terminal-status handling only.

One fresh independent review found three Important evaluator weaknesses: saved
currency and approval state were not directly checked, and exact acceptance
expectations incorrectly rejected safe alternatives. All three were fixed with
observed failing regressions followed by 10 passing harness tests. The same
reviewer confirmed the functional corrections through direct grading mutations.
A Minor fixture-isolation weakness was also corrected by showing the unapproved
INR baseline passes before changing only its approval state. Dataset v1.2 and
the `acceptance-20261025` run include these stricter checks; earlier runs remain.

Unmeasured: LIVE agent accuracy/reliability/cost, model comparison, real business
data, PDF/OCR/attachments, arbitrary accounting formats, production identity and
tenant authorization, production load/disaster recovery, and actual owner usability.
There is no free-form invoice question UI; the current product offers structured
investigation/evidence/recommendation sections. Six-invoice fictional workspaces
and manual copy remain demo limits. A prompt-instruction example passing does not
qualify broader prompt-injection security. No outbound messaging transport exists.

The offline evaluation, complete browser run and independent evaluator review are
complete. This assessment does not constitute release
acceptance, LIVE qualification or the still-unexecuted five-owner study.
