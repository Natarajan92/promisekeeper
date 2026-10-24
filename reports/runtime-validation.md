# Runtime validation

Environment observed on 24 October 2026: Windows, Python 3.12.15, SQLite 3.53.1, Node 24.19.0, npm 12.2.0, FastAPI 0.161.1, Uvicorn 0.54.0, Pydantic 2.14.1, OpenAI SDK 2.54.0, pytest 9.1.1, React/ReactDOM 19.3.1, TypeScript 7.0.2, Vite 8.3.5, Vitest 5.0.5 and Playwright 1.64.1. Asia/Kolkata timezone loaded. Resolved dependencies were inspected locally.

| Executed check | Final outcome |
| --- | --- |
| `uv sync --project backend --frozen --check` | 35 installed packages checked; no changes required |
| `uv sync --project backend --frozen` | Exit 0 using the workspace cache |
| `npm.cmd --prefix frontend ci --offline` | Exit 0; lockfile install of 107 packages using the workspace cache |
| `npm.cmd --prefix frontend run build` | Typecheck and production build passed |
| `npm.cmd --prefix frontend run test:unit -- --maxWorkers=1` | 57 passed across six files |
| `backend/.venv/Scripts/python.exe -m pytest backend/tests -q --basetemp .runtime/pytest-gate-v-serialized` | 748 passed, one intentional opt-in LIVE skip; exit 0 in 310.70 seconds. One existing Starlette/httpx deprecation warning retained |
| `node frontend/node_modules/@playwright/test/cli.js test --config tests/e2e/playwright.config.ts` | 75 passed, one intentional LIVE measurement skip; exit 0 in 5.3 minutes |
| `evaluate --suite fixtures --catalogue release-0.1 --output reports/fixture-evaluation.json` | 51/51 branches and 4/4 failure presets passed; STUB only |
| Frozen LIVE qualification | 153/153 attempted, 152 correct returned results, one provider gap, zero unexecuted; PASS_WITH_AVAILABILITY_GAPS under unchanged criteria |
| LIVE HTTP responsiveness | `responsiveness-final.json`: PASS, 30/30 opens within 3 seconds, 30/30 acknowledgements within 2 seconds, 30/30 completed within 60 seconds; database cleanup succeeded. Maxima 0.047 / 0.156 / 8.625 seconds; exit 0 |
| LIVE browser responsiveness | `live-browser-responsiveness-final.json`: PASS, 30/30 opens within 3 seconds, 29/30 visible start acknowledgements within 2 seconds, 30/30 visible completed results within 60 seconds; one Playwright test passed, exit 0 in 3.1 minutes |
| LIVE preservation | `preservation.json`: PASS, 10/10 cycles with exact rows over 18 tables, preserved immutable prefixes, expected counts, model identity and zero duplicates; temporary database removed; exit 0 |
| Five-owner study | UNEXECUTED; owner confirmed five users are unavailable |

The final backend and browser runs were serialized. Earlier executions remain failures: the first backend run had 743 passes, one preservation status-GET 503 failure and one skip. A bounded GET-only retry was reproduced under a real SQLite exclusive lock, fixed and independently reviewed; the original response body was unavailable. The next run had 747 passes, one subprocess readiness timeout and one skip. The unchanged 20-second startup bound then passed in the final serialized run. Host resource pressure was observed in adjacent executions, but the exact cause of that startup timeout is not proven.

The first integrated browser run had 62 passes, four failures and one skip. The final consolidated harness fixes passed 13 focused checks and then the complete suite above. Earlier Windows launcher/taskkill/resource failures and the original elapsed-watchdog assertion are documented in `us5-recovery.md`. No failed report was overwritten or represented as a pass.

All automated copies use isolated runtime databases. Default browser tests run installed Chrome headless with one worker and loopback-only child networking. Frozen setup and built same-origin serving were exercised through the actual API. Existing API/configuration tests cover loopback/Host/Origin restrictions, explicit one-worker configuration, strict mutation envelopes and fictional catalogue-only creation. Synthetic sentinels verify information boundaries and redaction; credential values were not inspected. Approved LIVE backend code loads configuration internally without printing it.

The product discloses STUB/LIVE, REFERENCE/REAL, fictional-only data and lack of authentication. Exact draft approval records review only. Sending, arbitrary ingestion, authentication, billing, real customer connectors and production deployment remain outside this release.

The final independent whole-change review and scoped re-review cleared all Critical/Important findings. The complete literal financial oracle is STUB fixture evidence. The frozen LIVE evaluator separately checks extracted facts and source provenance, findings, action, balance and review time; it does not directly compare every numeric field covered by the fixture oracle. Human usability and willingness to pay remain unmeasured.

The first complete LIVE HTTP timing run exposed a measurement-only resource leak: the SQLite connection context committed/rolled back but did not close its reader. A minimal real-file reproduction kept the Windows file locked until garbage collection. New success/error-path tests both failed before adding explicit connection closure. The failed timing report is preserved; only a fresh report can establish the corrected command outcome.

After the measurement-only resource correction, all 29 focused runner checks passed in 178.24 seconds, including two new actual SQLite success/error cleanup regressions, 30 STUB HTTP trials, ten actual STUB subprocess preservation cycles, financial/history mutation controls and status-read deadline controls. The full 748-test backend run predates this minimal runner fix; UI/product code is unchanged. Scoped independent review approved it.

## Declared timing conditions

The final LIVE HTTP, browser and preservation commands run serially with no competing evaluation or offline test suite. All use NEBIUS `zai-org/GLM-5.3-Flash`, one worker and fresh isolated fictional databases. HTTP timing uses the REFERENCE business clock and actual monotonic elapsed time; it does not measure paint. The browser uses REAL business time, installed Chrome headless at 1280x720, the built same-origin UI and actual visible content. Its wall-clock measurement includes Playwright click/wait overhead. The slowest browser open was 0.144 seconds; the slowest visible start was 3.237 seconds (first trial), with 29/30 within the required two seconds. All 30 attempts completed visibly; the maximum was 10.414 seconds. No outlier was removed. Latency success does not qualify extraction quality.

The earlier complete HTTP run retained 29 completed attempts and one truthful provider-incomplete attempt within 8.344 seconds, before its temporary-directory cleanup failure. The corrected fresh run has 30 completed attempts and no retained database. Its pass does not alter the older failed report.
