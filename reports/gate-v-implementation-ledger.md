# Gate V execution ledger

Plan: `specs/001-payment-case-mvp/tasks.md`, T085-T100, with the binding specification and API/UI contracts. On 24 October 2026 the owner authorized Gate IV approval/publication, followed by Gate V implementation and publication after completion. Gate IV was pushed as `0454551`. Gate V release acceptance remains blocked by the unexecuted five-owner study.

## Execution boundaries

The established feature checkout and SpecKit task ledger were retained under the reviewed execution approach. The frozen catalogue, model, prompt, schema, adapter and qualification criteria remain unchanged. Offline tests use isolated SQLite databases and owned processes with loopback-only networking. LIVE measurements are serialized without competing test/provider traffic. Fixed process-fault presets remain test-only; no product fault endpoint, sending, arbitrary ingestion or production deployment was introduced.

Implementation tasks were assigned within the approved development workflow, reviewed independently and corrected through scoped fix rounds. Task checkboxes do not establish human acceptance. The owner confirmed no five live users are available; no observations, scores or waiver were inferred.

## Implementation and task reviews

- T085-T086: commit-boundary process death, two hard restarts, real late callbacks, bounded retries, independent business/execution clocks and unreachable-server behavior exercise actual services. Review added exact pre-crash history/draft/review prefixes, persistent invalidation and unsaved browser-buffer assertions. All six restart journeys and the real-time fault journeys pass in the final browser suite.
- T087-T088: real SQLite workflow races and information-boundary checks cover review/update/start/closure serialization, receipts, redaction and isolated temporary diagnostics. Task review found a diagnostic sink escaping the test fixture; a temporary sink, pre-open write guard and metadata redaction assertions corrected it. Scoped review cleared the finding.
- T089: the fixed registry permits only the five commit boundaries and three provider presets in owned runtime processes. A private stdin pipe reaches the actual interpreter through the Windows launcher and stops it on parent EOF.
- T090: the fixture CLI replays all 51 canonical branches through domain/orchestration services, with four explicit provider failure probes. Review found incomplete financial-oracle coverage. A pinned independent literal oracle now checks invoice, verified paid amount, balance, currency, certainty and due time. Fourteen mutation controls passed; coordinated numeric offsets are rejected. Official fixture execution passed 51/51 branches and 4/4 probes.
- T091-T092: the complete recovery suite, keyboard journeys, visible focus, textual uncertainty/status and 200% text checks are executed. Five screenshots were inspected. This is implementation-agent inspection, not a representative-owner study.
- T093: isolated LIVE HTTP/browser timing and ten-cycle preservation commands were implemented. Review added exact comparisons over all 18 saved tables, immutable ordered prefixes across later commands/cycles, and receipt replay guards. The first HTTP run exposed a separate SQLite reader cleanup leak after all 30 trials; explicit connection closure and success/error-path regressions address it. Fresh final measurements are recorded in `runtime-validation.md`.
- T094-T095: the protocol, rotated order, equivalent manual packet and five blank observation rows are ready. All five rows remain UNEXECUTED. The separate personal testing kit contains 14 cases, expected results, canonical sample records and a business-owner demonstration script.
- T096: configuration reconciliation alone did not resolve the earlier unqualified T060. One fresh frozen 153-case batch was authorized under Gate V completion work, with stops on a quality failure or three consecutive missing responses. It completed 153 attempts: 152 correct returned results, one provider gap, zero unexecuted. The unchanged qualifier returned PASS_WITH_AVAILABILITY_GAPS. Earlier stopped reports were preserved; no automatic continuation is allowed.

## Execution failures and corrective evidence

The first backend integration run had 743 passes, one preservation status-GET 503 failure and one intentional LIVE skip. A real SQLite exclusive-lock reproduction established the typed retryable read behavior; the original response body was unavailable. Bounded GET-only polling now records known transient errors within the original 60-second deadline, without replaying POST commands or fabricating terminal state. Nineteen focused checks and four independent checks cleared that fix. A subsequent full run had 747 passes, one 20-second subprocess readiness timeout and one skip. The unchanged startup bound passed in the final serialized 748-pass run; the timeout's exact cause is unproven.

The first integrated browser run had 62 passes, four failures and one skip. The single consolidated final fix addressed shared empty-workspace state, invocation-dependent screenshot paths, typed transient GET handling and route cleanup. Nine GET-only regressions plus the four failed journeys passed a 13-test focused run. The complete final browser suite then passed 75 tests with one intentional LIVE skip.

Earlier launcher-only termination, taskkill denial/resource errors, DLL initialization/out-of-memory errors and automation overhead in an elapsed assertion remain failed observations. The initial LIVE browser timing batch stopped after eight trials on a saved-case read timeout; it is not a 30-trial pass. The first complete HTTP timing report met all timing limits but failed temporary-database cleanup; it is not regraded. Fresh reports use new paths.

## Independent final review

The whole-change review and scoped re-review cleared all Critical/Important findings. The later execution-discovered snapshot cleanup fix received separate scoped approval: `contextlib.closing` releases the real SQLite connection on success and query failure while preserving read-only snapshot semantics. The regression retains the connection reference, verifies it is closed and deletes the file without relying on garbage collection. Focused execution and fresh measurement outcomes are recorded in the runtime report.

The complete financial oracle is STUB evidence. The frozen LIVE evaluator checks raw extracted facts/source provenance, findings, action, balance and review time; it does not directly compare every numeric field in the fixture oracle. Neither automated tests nor LIVE qualification establish owner usability, a time-saving claim, willingness to pay or production readiness. Final acceptance disposition is in `release-acceptance.md`.

## Owner publication decision

At 2026-10-24T15:39:52.044Z the owner explicitly approved pushing the fictional test build while keeping formal acceptance pending. This authorizes the normal feature-branch commit/push, not a study waiver, accepted Release 0.1 or production deployment. T095 and the dependent formal closure tasks remain open.
