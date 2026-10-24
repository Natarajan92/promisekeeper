# Implementation and Validation Guide

**Status**: Gates I-III implementation is owner-approved; Gate III was pushed as 078c4db. On 24 October 2026 the owner authorized completing, approving and publishing Gate IV, then Gate V implementation and publication after completion. Gate IV final publication checks are in progress. T060 LIVE qualification remains outstanding and is not waived by implementation approval. Gate V and release acceptance evidence will preserve failed, skipped and unexecuted checks.

## Prerequisites and phase authorization

Follow the separate human gates in [plan.md](plan.md). Generate tasks before implementation; get explicit authorization for each implementation phase. Use Windows 11, Node 24, npm.cmd, uv and a managed Python 3.12 environment. Do not use the currently installed Python 3.10 as the application interpreter. Provider credentials/account access are required only for LIVE mode; keep them server-side and out of source control/logs.

Phase I created backend/frontend manifests, test configuration and ignore rules for `.runtime/`, virtual environments, credentials and generated build output, with resolved uv.lock/package-lock.json. Subsequent setup uses frozen lockfiles. Repository setup was separately owner-authorized after planning: private Natarajan92/promisekeeper, feature branch 001-payment-case-mvp.

## Setup (PowerShell, repository root)

These variables direct tool data into the workspace. They do not repurpose system HOME variables or change PowerShell execution policy.

```powershell
Set-Location -LiteralPath 'E:\maai-projects\promisekeeper'
$repoPath = (Get-Location).Path
$env:UV_CACHE_DIR = Join-Path $repoPath '.runtime\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repoPath '.runtime\python'
$env:npm_config_cache = Join-Path $repoPath '.runtime\npm-cache'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $repoPath '.runtime\playwright'
$env:PK_DB_PATH = Join-Path $repoPath '.runtime\promisekeeper.sqlite'
uv python install 3.12
uv sync --project backend --frozen
npm.cmd --prefix frontend ci
```

Initial lockfile generation belongs to authorized Phase I; `--frozen`/`ci` intentionally fail if manifests/locks are missing or inconsistent. Record Python, SQLite, Node, dependency and catalogue versions in the validation report. Add tzdata for Windows and verify Asia/Kolkata resolves. Do not present planned compatibility as a successful install.

## Start an explicitly fictional demonstration

`python -m promisekeeper.cli` provides `init-demo`, `serve` and `evaluate --suite live`. The `measure` and `report` commands remain planned for later gates. Optional `init-demo --variant <registered-id>` creates a fresh approved variant copy; it never modifies another copy.

```powershell
$env:PK_AGENT_MODE = 'STUB'
uv run --project backend python -m promisekeeper.cli init-demo --catalogue release-0.1 --clock REFERENCE
npm.cmd --prefix frontend run build
uv run --project backend python -m promisekeeper.cli serve --host 127.0.0.1 --port 8000 --workers 1
```

The built case workspace is served at `http://127.0.0.1:8000`; use `/docs` or `/api/v1/demonstrations` to inspect the API. Each copy contains exactly PK-001, PK-002 and PK-003; a baseline REFERENCE copy starts at 23 October 2026 10:00 IST. Restart `serve` without `init-demo` to preserve copies/history. The server acquires its process lock and records old running attempts incomplete before readiness. A second process fails without changing the owning process's state. Case/evidence/history/scenario/investigation routes require `?demonstration_id=<selected-copy-id>`. Mutations require JSON, `X-PromiseKeeper-Request: 1`, and a strict version-1 operation envelope.

The root page lists retained copies, restores a valid browser selection, selects a sole copy, shows a chooser for multiple copies, or requires explicit creation for an empty list. Listing errors preserve the saved preference and show recovery. Automated Chrome/API journeys exercised these states, reload and backend restart; representative-owner usability acceptance remains unexecuted.

For frontend development, use `npm.cmd --prefix frontend run dev -- --host 127.0.0.1` in another terminal; proxy `/api` to port 8000 and allow only that explicit loopback development origin. Avoid backend auto-reload/multiple workers while testing ownership/recovery.

For LIVE acceptance, copy the repository's `.env.example` to the Git-ignored `.env`, fill in `NEBIUS_API_KEY`, set `PK_NEBIUS_MODEL` to the explicitly selected Nebius model, and choose `PK_AGENT_MODE=LIVE` for live application runs. The backend loads this file; existing process environment variables take precedence. Keep credentials out of frontend/VITE variables. Nebius replaced the original OpenAI provider at the owner's direction; see ADR-006. Restart the backend and verify the LIVE label. Missing credentials, unavailable account/model or refusal must produce truthful capability/incomplete behavior, without switching providers, models or STUB silently. Record requested/returned model, response identity and prompt/schema/adapter versions. An explicit `evaluate --suite live` command performs real provider calls independently of the application's STUB setting and reports actual acceptance results.

## Baseline and update walkthrough

| Journey | Expected evidence and outcome |
| --- | --- |
| Open each case without investigation | Inspect invoice, ledger verification, raw messages, source IDs and missing records; no claim changes paid total. AC-01–AC-03. |
| Investigate PK-001 | INR 120,000 invoice minus verified INR 40,000 = INR 80,000 remainder; missed 20 October promise; FOLLOW_UP and respectful draft. |
| Investigate PK-002 | INR 50,000 remainder; WAIT on 25 October promise; review at 26 October 00:00 IST, no draft. |
| Investigate PK-003 | INR 60,000 recorded remainder plus unverified CR-T2 claim; VERIFY_PAYMENT, internal lookup, no demand. |
| Preview/confirm PK-003-U1; reinvestigate | Exact linked INR 60,000 settlement; zero remainder; CLOSE recommendation; explicit eligible owner confirmation required to close. Earlier VERIFY_PAYMENT remains. |
| Preview/confirm PK-001-U1 | Prior result/approval historical; new investigation WAIT on replacement promise; original evidence remains. |
| Apply PK-002-U1 clock event | At exactly 26 October 00:00 IST, old WAIT expires; reinvestigation FOLLOW_UP. Original evaluation time is preserved. |

The REFERENCE clock is controlled by registered catalogue events; do not accept arbitrary evaluation dates in the UI/API. REAL mode uses displayed server time and is evaluated separately. Evidence chronology uses source event time, with arrival time visible independently.

Gate II implements GET /api/v1/cases/{id}/scenario-events/{event_id}/preview and the matching confirmation POST. The preview includes exact copy/case/event/version/revision, evidence/clock changes and their hash. Gate III/early Gate IV test helpers submit that exact confirmed payload through the real API; they do not require the later update UI. Gate IV adds the visible preview/confirmation control. Stale revisions or changed hashes require a fresh preview and confirmation, never forced overwrite.

## Required regression journeys

- Replay all FV-01–FV-18 and every branch using fresh variant copies. Preserve baseline copies. Use the exact facts in spec.md, not new interpretations.
- FV-16: linked INR 20,000 fulfills its partial promise and leaves INR 30,000/FOLLOW_UP. Return the same catalogue commitment key with both specified valid quote boundaries and assert identical anchor identity, attribution and action. Remove only commitment attribution: known remainder unchanged, fulfillment unresolved, VERIFY_PAYMENT and no demand. Reject foreign keys and retain ambiguous binding as unresolved.
- FV-17: approve -> persist rerun start -> old approval invalid and review blocked -> incomplete rerun -> new explicit eligible approval allowed. Never restore old approval. Repeat with intervening PK-001-U1 and with a newer successful result; original draft stays blocked.
- FV-18: test both future invoice/promise date orderings. At baseline WAIT/review 25 October 00:00 IST; confirm the registered first clock event, mark the prior result for review, and reinvestigate to WAIT/review 27 October 00:00; confirm the second clock event and reinvestigate to FOLLOW_UP. Check exact-boundary behavior without automatic contact.
- Discover zero/one/multiple copies, restore a valid selection after reload/backend restart, and recover from a missing/deleted selection or failed listing. Switching copies must not retarget pending operations or unsaved draft text.
- Edit approved text/recipient and attempt stale-payload review. Block unsupported amount/fee/assertion/placeholder, preserve edits unapproved, allow supported neutral wording alternatives. Rejection remains historical; no customer transmission or sent state exists.
- Force missing/unavailable evidence, designated but unverified ledger entries, conflicting records, invalid precision/currency, duplicate/reversed payments, injection text, refusal, malformed/foreign source output, timeout and retry exhaustion. Assert safe limited/incomplete states and precise next steps. Fail draft generation after saving a recommendation; use the separate draft-retry command and verify unchanged investigation/history, bounded automatic usage and no overwrite of a concurrent edit.
- Kill the backend after start commit; after approval commit before response; during result save; and during draft work. Restart without reseeding. Reconcile operation IDs, preserve last committed state, never duplicate an approval/closure or accept a late callback.
- Race evidence update/start/approve/close commands with real temporary SQLite connections. Assert serialized eligibility and source snapshots; repeated same ID replays, changed payload with same ID conflicts. Race starts on different cases: only the one that reserves the global slot may persist RUNNING/invalidate approval. Save a newer draft edit and verify approval of the older exact version remains blocked.

## Available automated commands

```powershell
uv run --project backend pytest backend/tests/domain backend/tests/contract backend/tests/integration
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run test:unit -- --run
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
```

The e2e script uses installed Chrome, the real local API and a separate temporary database with a scripted Investigator. Its Python child is restricted to loopback networking. It covers complete UI/API/data flows. Unit fake time does not prove actual 60-second UI behavior; real-time forced-failure measurements remain a release requirement. Contract tests cover strict extra-field/source-span cases for [the Investigator contract](contracts/investigator-output.schema.json). Do not use a retained demonstration database in automated tests.

With live access configured during Phase III:

```powershell
uv run --project backend python -m promisekeeper.cli evaluate --suite live --catalogue release-0.1 --repeats 3 --output reports/live-evaluation.json
```

The following measurement commands remain planned for Gate V and are not currently available:

```powershell
uv run --project backend python -m promisekeeper.cli measure --suite responsiveness --trials-per-case 10 --report reports/responsiveness.json
uv run --project backend python -m promisekeeper.cli measure --suite preservation --cycles 10 --report reports/preservation.json
```

Live evaluation covers baseline/update and named variants, checks provenance/unknown handling/injection resistance and compares financial/action truth with deterministic expected outcomes. Three repeats assess observed variability; they do not prove universal model reproducibility. Record failures, latency and returned model identity. Responsiveness uses a declared environment and LIVE mode; a STUB report must be separately labeled and cannot stand in for live latency acceptance.

## Human acceptance and report

Run the five-owner evaluations for NFR-001/SC-001–SC-003/SC-007 using equivalent fictional manual-review copies, rotate order, record times, correctness, ratings and reasons. Execute keyboard-only tasks, visible focus/status checks, non-color interpretation and 200% text enlargement. Record 30 responsiveness trials and ten return/reinvestigation/restart cycles. Automated scripts cannot manufacture these human observations.

Release requires recorded passes for AC-01–AC-27, all named financial/failure variants, and every NFR. Evidence/approval/history checks require 100% pass. Record all SC measurements; disclose unmet SC-002/SC-007 learning targets. Preserve failed/skipped/unexecuted labels. A passing offline fixture suite or walkthrough alone is insufficient for live-agent, human usability or production-readiness claims.

Each phase report names scope, changed artifacts, commands actually executed, actual outcomes, unresolved/unexecuted checks, constitution check and proposed next phase. Stop for human review. Cutoff is 26 October 2026 10:00 IST; report any P0 shortfall and obtain an explicit scope decision rather than waive safety/tests or declare an unvalidated release passed.
