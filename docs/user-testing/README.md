# Test PromiseKeeper yourself

Allow 30-45 minutes for the complete checklist, or ten minutes for the first three cases. Use only the supplied fictional data. You do not need an API key for this walkthrough.

## Start the app (Windows PowerShell)

Open a terminal in `E:\maai-projects\promisekeeper`. On first setup:

```powershell
$repoPath = (Get-Location).Path
$env:UV_CACHE_DIR = Join-Path $repoPath '.runtime\uv-cache'
$env:UV_PYTHON_INSTALL_DIR = Join-Path $repoPath '.runtime\python'
$env:npm_config_cache = Join-Path $repoPath '.runtime\npm-cache'
uv sync --project backend --frozen
npm.cmd --prefix frontend ci
npm.cmd --prefix frontend run build
```

Start a separate fictional testing database so your other demonstrations stay available:

```powershell
$env:PK_AGENT_MODE = 'STUB'
$env:PK_DB_PATH = Join-Path (Get-Location).Path '.runtime\owner-user-tests.sqlite'
uv run --project backend python -m promisekeeper.cli serve --host 127.0.0.1 --port 8000 --workers 1
```

Keep that terminal open. Visit **http://127.0.0.1:8000** in Chrome. If port 8000 is occupied, stop its existing server or use `--port 8001` and open that port. Never start two servers on the same database.

In the browser, open **Create another fictional copy**, select **Standard payment examples** and **Fixed sample date**, then choose **Create fictional demonstration**. In an empty workspace the creation form is already open. Note the selected copy ID and the time shown. The reference business time is 23 October 2026, 10:00 IST; it intentionally differs from today's date. The STUB label means extraction uses approved scripted answers through the real rules and storage. It does not demonstrate LIVE model reliability.

## Follow the tests

1. Open [test-cases.md](test-cases.md). Run UT-01 through UT-14 in order, creating a fresh copy whenever instructed.
2. Compare what you see with each expected outcome. Record Pass, Fail or Blocked in [results-template.csv](results-template.csv), including the copy ID, test time, observed amount/action and any problem.
3. Use **View recommendation** after investigating. **Findings > Case actions** records your advice decision and offers closure when settlement is supported; the same controls remain available in History. Use **Review suggested message** when offered. After approving an exact saved version, **Copy approved message** copies it for use in your usual communication tool. Nothing is sent. If clipboard access is unavailable, select the exact approved text in the manual-copy field.
4. For a source, choose **Evidence**, then **Inspect exact source version**. For the reasoning choose **Findings**. **Timeline** orders source events; arrival time may be later. **Review** holds exact draft versions and decisions. **History** holds previous decisions, update previews, closure/reopening and earlier results. The case overview shows recorded balances, current recommendations and next review dates; changed evidence clears old advice from the overview.
5. Do not change the displayed amount or payment instructions to make a test pass. A claim from a customer is not a verified payment. Approval records your decision; it does not send a message.

The [sample data](sample-data.json) contains the original catalogue records and staged updates, with amounts as written. It is a readable reference, not an upload file. The [manual review packet](manual-review-packet.md) contains inputs without the answer key, for comparing your unaided decision with the app.

## Return later or restart

For a browser return, reload the same browser profile and choose your saved copy. For a backend restart, press **Ctrl+C** in the server terminal, then run the same `serve` command with the same `PK_DB_PATH`. Do not create a new copy when checking preservation. Saved evidence, results, exact drafts and decisions should remain. A running attempt interrupted by restart becomes incomplete; a previously invalidated approval must not become approved again. Unsaved wording is a local browser recovery buffer, not a saved version; clearing site data or switching browser profiles can remove it.

If a connection fails during a save, use **Check saved request outcome** or **Check operation outcome**. If the server confirms it was not recorded, retry the original request. Do not change its payload or create a second decision while the first outcome is unknown. A failed draft has its own **Retry failed draft step**, separate from investigating the case again.

## Report a problem

Record the UT ID, selected fictional copy/case, STUB or LIVE label, business time, exact steps and expected/actual result. A screenshot may help. Keep credentials and real customer information out of your report. Leave failed or blocked checks visible; do not turn them into passes after a refresh without recording both observations.

To remove only your testing copy, use **History > Delete selected demonstration > Review selected-copy deletion**, check the exact copy ID and explicitly confirm. That removes all three cases and their history in that copy; verify the ID first.

For the formal five-owner study, use [the observation protocol](../../reports/owner-evaluation-protocol.md). Your personal test is valuable, but one tester does not satisfy that acceptance sample.
