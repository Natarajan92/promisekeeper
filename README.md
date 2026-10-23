# PromiseKeeper

A local, fictional payment-case assistant for one agency owner. It preserves invoice evidence, payment claims, customer promises, and human decisions separately. The approved design uses one Investigator; deterministic code owns money, dates, recommendations, and eligibility.

The current implementation scope is **Gate I, T001–T020**: project tooling, strict evidence values, approved fictional fixtures, and pure financial/date/recommendation rules. Database commands, the application UI, live model integration, draft review, and release acceptance belong to later gates. No customer message is sent.

## Project documents

- [Specification](specs/001-payment-case-mvp/spec.md)
- [Implementation plan and human gates](specs/001-payment-case-mvp/plan.md)
- [Tasks](specs/001-payment-case-mvp/tasks.md)
- [Requirements-quality safety review](specs/001-payment-case-mvp/checklists/safety.md)
- [Setup and future validation guide](specs/001-payment-case-mvp/quickstart.md)
- [Gate I review and verification evidence](reports/phase-i.md)

## Gate I development

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

The project owner authorized repository setup and **Gate I only** on 23 October 2026. Stop after T020 and review the actual evidence before beginning Gate II. Passing tests do not authorize a phase transition.
