# Gate I review — T001–T020

Status: **Gate I complete through T020; reviewed and approved by the project owner on 24 October 2026.** Gate II is not authorized and T021 has not started.

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

## Final verification — 23 October 2026

- `uv sync --project backend --frozen`: passed, 35 resolved packages; CPython 3.12.15, SQLite 3.53.1 and Asia/Kolkata verified.
- `npm.cmd --prefix frontend ci`: passed; Node 24.19.0 and npm 12.2.0.
- `npm.cmd --prefix frontend run typecheck` and `npm.cmd --prefix frontend run build`: passed. The build contains only the initial HTML shell.
- `npm.cmd --prefix frontend run test:unit`: exited successfully with **zero test files**; no component-test acceptance claimed.
- `npm.cmd --prefix frontend run test:e2e -- --list --pass-with-no-tests`: configuration loads and enumerates **zero tests**. The initial load failed at the external config's CommonJS/module boundary; declaring the config directory as an ES module fixed it. No server or browser journey was started by enumeration.
- `uv run --project backend pytest -q`: **184 passed** after targeted RED→GREEN checks. See [execution ledger](implementation-ledger.md) for actual failure/pass evidence and rulings.
- `uv run --project backend python backend/tests/support/report_gate_i.py` with `PYTHONPATH=backend/src`: **35/35 declared domain outcomes**; [actual fixture report](phase-i-fixtures.json). All **17 workflow presets remain UNEXECUTED** as application workflows. The catalogue contains 40 branches across all 18 FV groups; not every preset represents an executable workflow at this gate.
- `uv build --project backend --out-dir .runtime/dist`: source distribution and wheel built. A separate isolated Python process imported the built wheel and read all three bundled JSON catalogues; all 40 variants materialized with exactly three cases.
- `git diff --check`: passed. Credentials, runtime data, virtual environments, dependency directories and build output are untracked/ignored. Constitution and checklist artifacts are unchanged since the reviewed main baseline.
- API/browser journeys, live extraction/latency, durable recovery/approval/closure and five-owner evaluation: **UNEXECUTED**, intentionally outside Gate I.

Locked backend versions observed in this run include FastAPI 0.161.1, Pydantic 2.14.1, OpenAI 2.54.0, pytest 9.1.1 and tzdata 2026.5. Their presence does not imply provider/API execution. Frontend package versions are recorded in `frontend/package-lock.json`.

## Independent review and remaining limits

The [independent review](phase-i-code-review.md) found three Important defects and one reported Minor defect. All were reproduced before fixes; the relative-date defect was regraded Important because ordinary supported source text changes its action. The one remediation pass fixed partial date/reference tokens, competing correction successors, omitted/unverifiable claim dates and capitalized relative dates. New regressions first produced 15 failures/2 passes; the full suite now passes 184/184. Fixes were verified by tests, without a second independent review. No deferred minor finding remains.

The review independently reproduced the 35/35 domain report and confirmed the Gate I boundary. Remaining unknowns are the deliberately absent later-gate workflows and production/live/human evaluation, not passing acceptance claims. Reference time is monotonic within a retained copy; replaying an earlier time requires a fresh copy.

The custom safety checklist is a requirements-quality review only. No external model call, message dispatch, database command, draft approval or actual closure was executed. The 17 workflow presets are data for later tests. The built application shell and declarative Playwright lifecycle do not yet provide a runnable end-user application.

There is no `.specify/extensions.yml`; no after_implement extension hook is registered. All implementation work stays on `001-payment-case-mvp` for human review; main retains the planning baseline.

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
