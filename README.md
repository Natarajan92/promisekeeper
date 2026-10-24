# PromiseKeeper

A local, fictional payment-case assistant for one agency owner. It preserves invoice evidence, payment claims, customer promises, and human decisions separately. The approved design uses one Investigator; deterministic code owns money, dates, recommendations, and eligibility.

Gates I–II are implemented and owner-approved. The owner approved the Gate III implementation, its GitHub push and starting Gate IV on 24 October 2026. The case/evidence/history UI and bounded Investigator pipeline work against the scripted adapter, with a Nebius LIVE adapter and an explicit extraction evaluation runner. The owner-approved [deterministic-findings refinement](docs/superpowers/specs/2026-10-24-deterministic-findings-design.md) is implemented and independently reviewed. **LIVE qualification remains outstanding (T060)**: the newest frozen evaluation stopped at 15 of 153 attempts with 12 correct returned results, three provider gaps and 138 unexecuted. Owner approval to proceed does not establish LIVE or release qualification. Gate IV covers draft review and lifecycle workflows; Gate V requires separate authorization. No customer message is sent.

## Project documents

- [Specification](specs/001-payment-case-mvp/spec.md)
- [Implementation plan and human gates](specs/001-payment-case-mvp/plan.md)
- [Tasks](specs/001-payment-case-mvp/tasks.md)
- [Requirements-quality safety review](specs/001-payment-case-mvp/checklists/safety.md)
- [Setup and future validation guide](specs/001-payment-case-mvp/quickstart.md)
- [Gate I review and verification evidence](reports/phase-i.md)
- [Gate II review and verification evidence](reports/phase-ii.md)
- [Gate III implementation and acceptance status](reports/phase-iii.md)
- [Live qualification criteria](reports/live-evaluation-criteria.md)

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

For Nebius configuration, copy [.env.example](.env.example) to the ignored `.env` and set `NEBIUS_API_KEY`. The backend reads this file; existing process variables take precedence. Keys stay outside frontend code. `PK_NEBIUS_MODEL` selects one explicit Nebius model; there is no automatic provider/model fallback. Keep `PK_AGENT_MODE=STUB` for offline demonstrations. A live candidate must pass the recorded extraction evaluation before Gate III acceptance:

```powershell
uv run --project backend python -m promisekeeper.cli evaluate --suite live --catalogue release-0.1 --repeats 3
```

This explicit command makes real Nebius calls even when the interactive workspace is configured STUB. See the Gate III report for actual results and unexecuted checks. The owner approved and committed Gate II as `9b0da8f`, then authorized Gate III and selected Nebius. Gate IV is now owner-authorized; **Gate V still requires new explicit owner authorization.**
