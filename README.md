# PromiseKeeper

A local, fictional payment-case assistant for one agency owner. It preserves invoice evidence, payment claims, customer promises, and human decisions separately. The approved design uses one Investigator; deterministic code owns money, dates, recommendations, and eligibility.

Gates I-IV are owner-approved and published; Gate IV is `0454551`. Gate V engineering and technical verification are complete, including LIVE timing and ten preservation cycles. **Formal Gate V / Release 0.1 acceptance remains blocked by the unexecuted five-owner study.** The owner approved publishing the engineering work as a fictional test build while keeping formal acceptance pending. Frozen LIVE qualification returned 152 correct results from 153 attempts, with one retained provider gap. Earlier failed reports remain preserved. No customer message is sent.

To try the product yourself, start with the [hands-on guide](docs/user-testing/README.md), [14 test cases and expected results](docs/user-testing/test-cases.md) and [fictional sample data](docs/user-testing/sample-data.json). The [small-business explanation](docs/user-testing/small-business-pitch.md) includes a short pitch, demonstration script and honest answers about current limits.

## Project documents

- [Specification](specs/001-payment-case-mvp/spec.md)
- [Implementation plan and human gates](specs/001-payment-case-mvp/plan.md)
- [Tasks](specs/001-payment-case-mvp/tasks.md)
- [Requirements-quality safety review](specs/001-payment-case-mvp/checklists/safety.md)
- [Setup and validation guide](specs/001-payment-case-mvp/quickstart.md)
- [Gate I review and verification evidence](reports/phase-i.md)
- [Gate II review and verification evidence](reports/phase-ii.md)
- [Gate III implementation and acceptance status](reports/phase-iii.md)
- [Gate IV implementation and verification status](reports/phase-iv.md)
- [Live qualification criteria](reports/live-evaluation-criteria.md)
- [Gate V implementation and verification](reports/phase-v.md)
- [Requirement evidence matrix](reports/acceptance-matrix.md)
- [Release acceptance decision](reports/release-acceptance.md)

## Development

Use Windows PowerShell, Python 3.12 managed by uv, Node 24, and npm.cmd. Direct local caches into this ignored workspace directory before setup:

```powershell
$repoPath = (Get-Location).Path
$env:UV_CACHE_DIR = Join-Path $repoPath '.runtime\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repoPath '.runtime\python'
$env:npm_config_cache = Join-Path $repoPath '.runtime\npm-cache'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $repoPath '.runtime\playwright'
uv sync --project backend --frozen
npm.cmd --prefix frontend ci
uv run --project backend pytest
npm.cmd --prefix frontend run typecheck
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:unit
npm.cmd --prefix frontend run test:e2e
```

Use the frozen lockfiles. Browser tests use the installed Chrome channel and start a separate loopback server with a fresh temporary database. Do not run tests against retained demonstration data. Credentials, databases, virtual environments, caches, and build output are excluded from Git.

## Run the case workspace

Create a new fictional copy explicitly, then start the one-worker service:

```powershell
$env:PK_AGENT_MODE = 'STUB'
$env:PK_DB_PATH = Join-Path (Get-Location).Path '.runtime\promisekeeper.sqlite'
uv run --project backend python -m promisekeeper.cli init-demo --catalogue release-0.1 --clock REFERENCE
uv run --project backend python -m promisekeeper.cli serve --host 127.0.0.1 --port 8000 --workers 1
```

`init-demo` always creates a fresh copy; restarting `serve` preserves existing copies. Only one process may own a database. `/api/v1/health`, `/api/v1/demonstrations` and the generated `/docs` expose the current API. Case, source, history and scenario routes require a `demonstration_id` query parameter. Mutations require JSON and `X-PromiseKeeper-Request: 1`; obtain the exact case-bound fixture preview before confirming an event. Keep the same operation ID and payload when reconciling an unknown outcome.

Build the frontend before serving, then open `http://127.0.0.1:8000`. Select a retained copy, inspect its three cases and source versions, and explicitly investigate when ready. STUB uses approved extraction packets through the same runtime validation and deterministic rules as LIVE.

Open **Review** to edit and explicitly approve or reject an exact saved draft. **History** provides prior results and source versions, advice decisions, fictional update previews, and explicit closure/reopening or selected-copy deletion. Each confirmation rechecks the saved case; approval never sends a message.

For Nebius configuration, copy [.env.example](.env.example) to the ignored `.env` and set `NEBIUS_API_KEY`. The backend reads this file; existing process variables take precedence. Keys stay outside frontend code. `PK_NEBIUS_MODEL` selects one explicit Nebius model; there is no automatic provider/model fallback. Keep `PK_AGENT_MODE=STUB` for offline demonstrations. A live candidate must pass the recorded extraction evaluation before Gate III acceptance:

```powershell
uv run --project backend python -m promisekeeper.cli evaluate --suite live --catalogue release-0.1 --repeats 3 --output reports/live-evaluation-new.json
```

This explicit command makes real Nebius calls even when the interactive workspace is configured STUB. See the Gate III report for actual results and unexecuted checks. The owner approved and committed Gate II as `9b0da8f`, then authorized Gate III and selected Nebius. The owner authorized Gate IV publication and Gate V implementation on 24 October 2026; release acceptance still requires the recorded checks and actual human observations.

## Gate V verification commands

Run the fixture report offline without credentials. Each output path must be new; preserve earlier failed reports.

```powershell
uv run --project backend python -m promisekeeper.cli evaluate --suite fixtures --catalogue release-0.1 --output reports/fixture-evaluation-new.json
```

The following measurement commands require the explicitly configured LIVE Nebius model and make real provider calls in isolated temporary copies. HTTP timing is separate from browser display timing; neither establishes extraction qualification.

```powershell
$env:PK_AGENT_MODE = 'LIVE'
$env:PK_NEBIUS_MODEL = 'zai-org/GLM-5.3-Flash'
uv run --project backend python -m promisekeeper.cli measure --suite responsiveness --trials-per-case 10 --report reports/responsiveness-new.json
uv run --project backend python -m promisekeeper.cli measure --suite preservation --cycles 10 --report reports/preservation-new.json
```

For the opt-in real browser measurement, after building the UI:

```powershell
$env:PROMISEKEEPER_LIVE_MEASUREMENT = '1'
$env:PROMISEKEEPER_LIVE_BROWSER_REPORT = Join-Path (Get-Location).Path 'reports/live-browser-responsiveness-new.json'
node frontend/node_modules/@playwright/test/cli.js test --config tests/e2e/live.playwright.config.ts
Remove-Item Env:\PROMISEKEEPER_LIVE_MEASUREMENT
```

Default browser tests skip the LIVE measurement. The [owner-study protocol](reports/owner-evaluation-protocol.md) and [blank observations](reports/owner-observations.csv) require actual participants. Automated passes cannot populate those results or authorize a production release. See the final acceptance reports for executed outcomes.
