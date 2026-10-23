# Gate I independent code review and disposition

Review scope: baseline `bd5357f`, implementation head `fdcf34ad330db3b2a202a2003c64d78105e2eab4`. One fresh read-only reviewer examined the entire Gate I branch against T001–T020, the spec, plan, contracts, model, constitution, fixture report and execution ledger. It ran direct in-memory reproductions and independently collected an identical 35/35 domain report. It did not rerun the then-reported 167-test suite or modify files/index/HEAD.

The reviewer reported no Critical issues, three Important issues and one Minor issue. The implementer reproduced each issue before fixing it in one remediation pass. There was no second independent review of the fixes; their evidence is the regression tests and the final whole-suite run.

| Finding at reviewed head | Effect and reproduction | Final disposition |
| --- | --- | --- |
| Important: substring date/reference validation, commitments.py original lines 132–134 and 192–194 | PK-002 accepts extracted `5 October 2026` inside `25 October 2026`, changing WAIT to FOLLOW_UP. PK-003-U1 accepts extracted CR-T2 inside changed original CR-T20, falsely matching settlement and suggesting CLOSE. | Fixed: complete token boundaries in the original anchored clause/quote. Tests additionally reject prefixed references, slash/dot suffixes and partial claim dates. |
| Important: competing correction successors, payments.py original lines 41–67 | Two verified INR 60,000 corrections each replace PK-001 L1, but distinct transaction references are summed into INR 120,000 paid and CLOSE. | Fixed: correction forks and descendants remain unresolved; ambiguous branches/aliases are ineligible and financial totals unknown. Linear correction chains and identical transaction aliases still count once. |
| Important: omitted stated payment date, commitments.py original lines 192–205 | After PK-003-U1, move settlement one day earlier. Original `today` gives VERIFY_PAYMENT, but null extraction incorrectly gives CLOSE. | Fixed: stated date omitted from extraction yields LIMITED/VERIFY_PAYMENT and an unresolved claim. A stated date with an unknown settlement day also stays unresolved. Truly unstated dates remain supported. |
| Reported Minor, regraded Important: capitalized relative date, dates.py original line 56 | `Tomorrow`/`TOMORROW` are mistaken for ISO timestamps; normal supported future-date input becomes unresolved and changes expected behavior. | Fixed: recognize actual ISO timestamp syntax. Today/TODAY/Tomorrow/TOMORROW now match their lowercase forms. |

Regression evidence: `backend/tests/domain/test_review_regressions.py` produced **15 failed, 2 passed before implementation**, then the complete backend suite produced **184 passed**. Existing tests plus the two passing new checks retain valid correction chains/duplicate aliases and truly unstated dates. The [execution ledger](implementation-ledger.md) records each RED→GREEN disposition.

An implementer configuration check also found Playwright's external config re-export was loaded as CommonJS. The original command failed with an import.meta error. Declaring the e2e config directory as an ES module made the same enumeration command pass, listing **0 tests**. No API/browser workflow acceptance is inferred.

## Reviewer exclusions and owner-visible rulings

Each exclusion was assessed explicitly rather than treated as a pass:

- Persistence, API ownership, transactional receipts, restart recovery and runtime fixture confirmation: Gate II is absent and unauthorized. The current increment cannot run a durable application workflow.
- Live Investigator accuracy, provider behavior, browser journeys, accessibility and latency: later gates must establish these; catalogue candidates cannot prove them.
- Draft approval, closure execution, deletion and human acceptance: later workflows remain unimplemented/unexecuted.
- Production readiness and real financial verification: outside this fictional Gate I scope; no production approval follows from the tests.

Final disposition: the Important findings have regression evidence and a green full suite. The increment may be presented for **Gate I human review**. This is neither release approval nor authorization to start T021.
