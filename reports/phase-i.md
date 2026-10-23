# Gate I review — T001–T020

Status: draft exit record pending independent code review and final verification. Gate II is not authorized.

The project owner authorized safety-checklist review, a private GitHub repository, and Gate I only. The [safety review](safety-review.md) found 38/38 requirements-quality criteria satisfied. The built-in checklist remains 16/16. A monotonic reference-clock requirement was made explicit before implementation.

## Implemented scope

- Repository: private [Natarajan92/promisekeeper](https://github.com/Natarajan92/promisekeeper); reviewed planning baseline on main, implementation on 001-payment-case-mvp.
- Python 3.12/uv and Node 24/React/TypeScript/Vite tooling, frozen lockfiles and loopback development configuration.
- Strict, immutable evidence/projection boundaries and copy/source-version-scoped commitment anchors.
- Exact integer paise and lossless decimal-string storage/transport representation, explicit unknown/invalid/conflicting states, aware timestamps and IST boundaries.
- Three baseline cases, three staged updates, 23 financial and 17 workflow/adversarial variant branches, plus the declared FV-18 clock events. All copies contain exactly three cases.
- Pure eligibility, duplicate/reversal/correction handling, invoice balance, explicit promise attribution/fulfillment, claim reconciliation, supersession and ordered recommendations.
- Isolated temporary storage/clocks and loopback-only TCP/DNS blocking in parent and offline Python child processes; redacted diagnostics and truthful STUB/LIVE capability configuration.

The initial HTML file is a build shell only; the case UI, server, storage commands, live Investigator, review/closure workflows and release evaluations are later-gate work.

## Verification so far

- uv sync --project backend --frozen: passed, 35 resolved packages; CPython 3.12.15, SQLite 3.53.1 and Asia/Kolkata verified.
- npm.cmd --prefix frontend ci: passed; Node 24.19.0 and npm 12.2.0.
- npm.cmd --prefix frontend run typecheck and run build: passed.
- npm.cmd --prefix frontend run test:unit: exited successfully with **zero test files**; no component-test acceptance claimed.
- uv run --project backend pytest -q: **167 passed** after targeted red/green checks. See [execution ledger](implementation-ledger.md) for actual failure/pass evidence and rulings.
- API/browser journeys, live extraction/latency, durable recovery/approval/closure and five-owner evaluation: **UNEXECUTED**, intentionally outside Gate I.

Final fixture report, code-review findings and final check results will be recorded before T020 is marked complete.

## Constitution check

| Principles | Gate I evidence |
| --- | --- |
| I–III | Approved spec/plan precede implementation; bounded T001–T020; pure domain has no framework/storage/provider/UI dependency. |
| IV–VII | No LLM agent runtime added in this gate; later design still permits exactly one Investigator. Financial/time/action rules are deterministic, contracts strict, evidence original and source-linked, unknowns explicit. |
| VIII–X | No external financial/message writes or closure execution. Fixture transforms are pure test/catalogue materialization, not owner-authorized runtime commands. Normal, uncertain and failure inputs have tests; durable commands/recovery remain Gate II onward. |
| XI–XIII | ADRs retained; rulings and tests recorded; future UI stays case-centered; all fixtures fictional, credentials/runtime/build files ignored and diagnostics redacted. |
| XIV–XVI | 26 October 2026 10:00 IST remains governing; no P0 waiver, no later-gate execution, no invented live/usability/release passes. Stop for the owner after T020. |

## Proposed next scope

Gate II, T021–T038: durable SQLite/receipts/ownership/recovery, snapshots, case-bound fixture preview/confirmation and demonstration discovery/minimal case API. Begin only after the project owner reviews Gate I and explicitly authorizes Gate II.
