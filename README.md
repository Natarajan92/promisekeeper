# PromiseKeeper

A local, fictional payment-case assistant for one agency owner. It preserves invoice evidence, payment claims, customer promises, and human decisions separately. The approved design uses one Investigator; deterministic code owns money, dates, recommendations, and eligibility.

The implemented scope is **Gates I–II, T001–T038**: strict evidence and pure domain rules, approved fictional fixtures, durable SQLite commands, immutable snapshots/history, and a minimal loopback case API with exact fixture-event confirmation. Investigator execution and the case UI begin in Gate III; draft review and release acceptance belong to later gates. No customer message is sent.

## Project documents

- [Specification](specs/001-payment-case-mvp/spec.md)
- [Implementation plan and human gates](specs/001-payment-case-mvp/plan.md)
- [Tasks](specs/001-payment-case-mvp/tasks.md)
- [Requirements-quality safety review](specs/001-payment-case-mvp/checklists/safety.md)
- [Setup and future validation guide](specs/001-payment-case-mvp/quickstart.md)
- [Gate I review and verification evidence](reports/phase-i.md)
- [Gate II review and verification evidence](reports/phase-ii.md)

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
```

Lockfiles are created during authorized setup. The complete application startup and e2e journeys in the guide remain future work until their implementation gates. Do not run tests against retained demonstration data. Credentials, databases, virtual environments, caches, and build output are excluded from Git.

## Run the Gate II API

Create a new fictional copy explicitly, then start the one-worker service:

```powershell
$env:PK_AGENT_MODE = 'STUB'
$env:PK_DB_PATH = Join-Path (Get-Location).Path '.runtime\promisekeeper.sqlite'
uv run --project backend python -m promisekeeper.cli init-demo --catalogue release-0.1 --clock REFERENCE
uv run --project backend python -m promisekeeper.cli serve --host 127.0.0.1 --port 8000 --workers 1
```

`init-demo` always creates a fresh copy; restarting `serve` preserves existing copies. Only one process may own a database. `/api/v1/health`, `/api/v1/demonstrations` and the generated `/docs` expose the current API. Case, source, history and scenario routes require a `demonstration_id` query parameter. Mutations require JSON and `X-PromiseKeeper-Request: 1`; obtain the exact case-bound fixture preview before confirming an event. Keep the same operation ID and payload when reconciling an unknown outcome.

The built root page is still the Gate I placeholder. Investigation, draft review and closure commands remain unavailable; the case view reports these limits. Gate I was reviewed and approved on 24 October 2026. The owner authorized Gate II on the same date; its exit report is ready for review. **Gate III and later gates require new explicit owner authorization.**
