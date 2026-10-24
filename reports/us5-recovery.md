# Whole-flow recovery evidence

Gate V T085-T091 exercises the real application services, SQLite transactions and browser. The final backend suite passed 748 tests with one intentional opt-in LIVE skip; the final Chrome/API/SQLite suite passed 75 tests with one intentional LIVE measurement skip. The fixture command separately passed all 51 canonical branches and four failure presets.

| Evidence | Observed outcome |
| --- | --- |
| Process death after START, RESULT, DRAFT, APPROVAL and CLOSURE commits | Five actual subprocess journeys passed. Operation receipts replay once. An interrupted start becomes PROCESS_RESTARTED incomplete; a committed result survives with its recoverable draft intent; draft, approval and closure commits survive a lost response. |
| History and stale approval across two hard restarts | Exact pre-crash result/draft/review records and ordered history prefixes survive. Invalidation stays effective. A second restart preserves the complete recovered history without duplicates. |
| Unsaved wording across a hard restart | The browser buffer survives process restart and reload, remains explicitly unsaved and does not change the saved server draft. |
| Real late provider callback | Two actual 20-second reservations expire. The attempt becomes incomplete; a callback arriving after 45 seconds cannot write a result. |
| Retry exhaustion and independent clocks | Real transient calls exhaust the bounded retry path. Advancing the registered business clock changes evaluation time without extending the wall-clock execution budget. |
| Unreachable backend | The actual owned process is killed. Visible connection limitation and the real elapsed watchdog are observed using passive browser timestamps. No fake execution clock or increased product deadline is used. |
| SQLite races and information boundaries | Workflow race tests and information-boundary tests pass, including simultaneous review/update/lifecycle actions, receipt integrity, redaction and isolated temporary diagnostics. |
| Canonical financial/source branches | `fixture-evaluation.json` records 51/51 passes against independent literal financial and findings expectations, plus 4/4 timeout/unavailable/refusal/malformed-response safety probes. |
| Prior history over ten LIVE cycles | The separate measurement result is recorded in `preservation.json` and `runtime-validation.md`; this browser/fault suite alone does not certify that measurement. |

Process controls are fixed test-only presets installed in an owned temporary `fresh.sqlite` process. A private stdin KILL reaches the actual Python interpreter through the Windows virtual-environment launcher; STOP requests graceful exit and EOF prevents orphan servers. No arbitrary paths, SQL, Python or provider commands and no HTTP fault-control endpoint are added to the product.

Earlier failed and interrupted runs are retained locally. These include launcher-only termination, denied/resource-failed taskkill, DLL initialization and out-of-memory errors, and an elapsed assertion that included automation scheduling. A subsequent integrated run exposed four browser harness failures: shared empty-workspace state, a screenshot path dependent on the invocation directory, an unhandled retryable status GET and the corresponding route-cleanup failure. The consolidated fixes and nine status-read regressions passed a focused 13-test run, then the complete 75-test browser run. A transient GET remains unobserved until an actual terminal response; it never triggers automatic mutation replay.

The final independent review and scoped re-review reported no open Critical or Important findings. Scripted failure tests establish recovery behavior; they do not substitute for LIVE extraction qualification or observations from business owners.
