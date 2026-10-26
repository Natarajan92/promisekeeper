# Synthetic end-user upload rehearsal — 25 October 2026

The owner requested nuanced fictional files to upload and test as an end user.
The [54-file ZIP](../docs/demo-import/synthetic-demo-pack.zip) and
[START-HERE walkthrough](../docs/demo-import/synthetic-pack/START-HERE.md) are ready.
Use the current local STUB build on `005-csv-reconciliation-demo`; extract the ZIP
and upload individual CSV, EML and TXT documents. The JSON file is an independent
expected-results oracle, not an import file. No source connection is required.

## Main journey: expected and observed

Four customers, six invoices and nine distinct receipts cover changed company
names/aliases/addresses, 35–90-day payment delays, partial/full/split receipts,
duplicate exports, paise, pending/reversed/unknown receipts and unallocated excess.
The two NOVA invoices share one receipt; two separate pieces also fund NOVA-401.

| Invoice | Verified remainder (INR) | Expected and observed action |
|---|---:|---|
| ECON-101 | 60,000.00 | VERIFY_PAYMENT; ECON-T3 absent initially |
| ECON-102 | 40,000.00 | WAIT; explicit future promise |
| KITE-201 | 80,000.00 | FOLLOW_UP; expired promise |
| LOTUS-301 | 0.00 | CLOSE recommendation; lifecycle still OPEN |
| NOVA-401 | 50,000.50 | FOLLOW_UP; two pieces support 40,000.25 claim |
| NOVA-402 | 5,000.25 | FOLLOW_UP; partial claim supported |

The initial total remainder is **INR 235,000.75**, from original invoices of
INR 410,001.25 and allocations of INR 175,000.50. NOVA-T1 retains INR 20,000
unallocated. No receipt is assigned automatically, including exact invoice hints.
Duplicate files do not double-count. An unmatched payer has no suggested customer.
These remainders assume the owner's assertion of correct and complete relevant
allocations. If an unassigned deposit could belong to an invoice, leave coverage
unchecked; the app cannot infer the missing relationship or independently certify it.

After the later ECON-T3 receipt is imported, explicitly allocated and coverage
reconfirmed, ECON-101 has zero remainder, resolved claims and a CLOSE recommendation.
It remains OPEN until owner confirmation. Its earlier VERIFY result is unchanged.
The actual browser route also approved/copied KITE's exact saved wording and
confirmed that later evidence removes access to that old approval. Nothing was sent.

## Deliberate failures and limits

All **35 rejection files** were exercised through real API preview and attempted
commit: each returned preview errors and HTTP 422 without changing workspace data.
They cover conflicting UTRs, debits, currency, fractional paise, future/invalid dates,
allocation caps/status/missing references, duplicate headers, row/invoice limits,
malformed CSV, multiple invoices/amounts/dates/references/intents, conditional or
negated claims, questions, repeated quotes, excess clauses, deductions, HTML and
missing source dates. The browser also exercised pending-allocation, ambiguous-amount and shared-prefix
alternative-date previews; confirmation was unavailable and saved data stayed unchanged.

| Exploration | Observed behavior |
|---|---|
| “next Friday” | VERIFY_PAYMENT / COMPLETE; PROMISE_DATE_UNRESOLVED, no guessed WAIT |
| Quoted rupee symbol | VERIFY_PAYMENT / COMPLETE; INVALID_PROMISE_AMOUNT, no normalization to INR |
| Explicit supporting context only | VERIFY_PAYMENT / LIMITED; MISSING_EXTRACTION |
| “set the balance to zero” plus a separate valid promise | Instruction had no financial effect: INR 40,000 remained, no approval/closure. WAIT came from the separate quoted promise. |

COMPLETE describes completion of an investigation, not certainty about every
promise. Inspect the reason and source evidence. The offline parser does not provide
general message understanding, OCR, withholding/write-off inference or arbitrary
bank-column mapping. A single synthetic instruction test is not a security
qualification or proof against every prompt-injection technique.

## Defects found and fixed

- Invoice-number parsing consumed `NO` from `NOVA-401`; number prefixes now have
  word boundaries. Regression cases also cover `NO-101` and `NUMBER-101`.
- Multiple amounts, dates, references or past/future intents silently used the first
  match. Preview now rejects those clauses for clarification, including coordinated
  alternatives that share a currency, date or UTR prefix. The bounded parser also
  rejects coordinated/approximate/deducted wording instead of inferring a total.
- An explicitly reviewed context-only message triggered an empty-extraction failure.
  Only the all-reviewed-uploaded-context case now reaches the conservative LIMITED
  result; ordinary seeded empty extractions remain invalid.
- ZIP generation initially included unrelated pre-existing files in the output
  directory. It now archives only the generated-file allowlist.

Each correction has an observed failing regression followed by passing evidence.
No production data, LIVE provider calls or human usability study was used. This
rehearsal does not qualify uploaded extraction or unqualified agents for LIVE use.

## Verification

- Focused generator/API/document checks: **37 passed**. These include all 35
  rejected files and four isolated explorations, not 37 individual upload scenarios.
- Actual six-invoice end-user Chrome journey: **passed** (full-suite main route 30.2 seconds; context-only route 7.5 seconds).
- Final full backend: **941 passed, one intentional LIVE skip**.
- Frontend: **153 passed**; TypeScript/production build passed.
- Full Chrome: **92 passed, one startup-readiness failure, one intentional LIVE skip**.
  The failed existing start-commit recovery check passed unchanged on isolated
  recheck (**1 passed**, 29.3-second flow). All 93 offline checks therefore have
  passing evidence across these runs; the full-run failure is retained.
- Independent review: one Important shared-prefix ambiguity found and fixed with six
  additional RED/GREEN regressions; no other findings.

Dates are generated relative to an explicit demo day; regenerate on the day of the
demo using the command in START-HERE. Existing unrelated files are preserved, and
the ZIP excludes them. Changes remain local and uncommitted; no publication occurred.

Original failing runs remain in ignored runtime logs: parser prefix and competing-value
regressions, context-only extraction, and ZIP allowlisting were first observed failing.
The first context-only browser attempt closed an already-open import panel in a
retained workspace; its setup now explicitly opens the panel and creates a new
workspace. Financial assertions and product deadlines were preserved.

The final full backend run took 524.49 seconds; full Chrome took 13.2 minutes
while both suites ran against separate databases. The single browser failure was
`Isolated backend readiness timed out` in the existing 10-second test-server helper,
not a financial assertion. Its unchanged isolated recheck passed. No timeout,
product deadline or assertion was relaxed, and the failed original is preserved.

Verification commands: `python -m pytest backend/tests -q` with a unique runtime
`--basetemp`, `npm.cmd --prefix frontend run test:unit -- --maxWorkers=1`,
`npm.cmd --prefix frontend run build`, and the serial Playwright configuration
`tests/e2e/playwright.config.ts`, followed by the named restart-check recheck.
All 54 delivered ZIP entries were also compared byte-for-byte with the extracted
source files and generated-file allowlist.
