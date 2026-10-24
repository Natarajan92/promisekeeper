# Gate II: durable foundation and minimal case API

Implemented T021–T038 after the project owner's explicit authorization on 24 October 2026. Gate I had already been reviewed and approved. The owner approved Gate II and authorized proceeding to Gate III on 24 October 2026.

## Result

- One owned SQLite file with per-operation connections, foreign keys, DELETE journal, EXTRA synchronization, a 250 ms busy timeout, explicit short transactions and versioned migrations.
- Copy-scoped immutable evidence, normalized projections, exact source-version commitment anchors/attributions, immutable snapshots, append-only history and monotonic case/evidence/review revisions. Workflow storage includes attempts/results, steps, drafts/reviews and dispositions, with terminal fencing and persistent retry uniqueness; later gates supply those feature commands.
- Durable receipt replay before revision/capacity checks; changed requests conflict. Starts reserve the single process-wide slot before committing their snapshot, RUNNING attempt, review invalidation and receipt. Commit failure rolls back all changes and releases the slot. This internal start service has no provider or API worker attached in Gate II.
- Ownership-gated recovery marks interrupted investigations INCOMPLETE and draft attempts FAILED without reseeding, restoring approval, replacing saved results, or resetting automatic retry usage.
- Explicit fresh-copy CLI creation and one-worker loopback serving, strict version-1 API envelopes, safe errors/readiness, selected-copy discovery and case/source/history reads. Case views retain unknown amounts and expose unavailable commands truthfully.
- Read-only fixture previews and atomic confirmations bind exact catalogue version, copy/case/event, revision, evidence/anchors and clock transition. Old snapshots survive evidence arriving mid-run. A shared REFERENCE clock change invalidates affected case review scopes; REAL mode never accepts fixture clock control. Closed cases retain their lifecycle.
- Selected-copy deletion purges owned content while retaining content-free operation identities. Delayed creation retries after deletion cannot create replacement copies.

## Verification actually run

| Check | Result |
| --- | --- |
| Baseline `backend/.venv/Scripts/python.exe -m pytest -q` | 184 passed before implementation |
| Final `backend/.venv/Scripts/python.exe -m pytest -q` | 232 passed; one installed-dependency warning |
| `npm.cmd --prefix frontend run typecheck` | Passed |
| `npm.cmd --prefix frontend run build` | Passed |
| Isolated CLI and actual loopback HTTP smoke | Passed: two new copies, built static root, case read, exact preview/confirmation, receipt lookup, second-process exclusion and restart preservation |
| Independent read-only code review | Completed; findings fixed with failing-then-passing regression tests |

All automated application checks used fresh temporary SQLite files and blocked external network access. The CLI smoke used a separate new database and no provider credentials. No retained owner demonstration data was used for tests.

The integration/contract suite exercises failed commits, repeated and changed operations, concurrent same/different-case starts, concurrent replay, slot rollback, foreign-copy rejection, immutable anchors/history/snapshots, pre-update evidence scopes, stale/hash/target rejection, read-only discovery, every approved variant, unavailable ledger facts, case-bound receipt lookup, deletion/restart and retained results/reviews/retry counts. Future workflow rows are seeded directly in test utilities to verify storage/recovery; this does not claim that investigation generation or human review commands are implemented.

Recorded runtime: Python 3.12.15, SQLite 3.53.1, FastAPI 0.161.1, Pydantic 2.14.1, Uvicorn 0.54.0 and Vite 8.3.5. Frozen dependency lockfiles were unchanged. Starlette emits a warning that its installed httpx TestClient integration is deprecated; tests pass, and no dependency migration was attempted in this gate.

## Review findings and decisions

The independent reviewer reproduced delayed creation retry after deletion, numeric confirmation coercion, and malformed Host acceptance. Regression tests first failed, then passed after permanent hashed operation tombstones, explicit boolean confirmation and complete Host parsing checks. Numeric confirmation and malformed Host findings were treated as required contract fixes. An additional storage test showed retry identity could be changed or deleted; triggers now retain it for the life of the copy. There are no deferred code-review findings.

Case/source/history/scenario routes require an explicit `demonstration_id` query parameter. This resolves the selected-copy ownership mechanism left implicit in the contract; future clients must supply it. Work stayed in the existing feature checkout so the owner's local development environment remained available. The owner requested a local commit after approving the gate; publication and merging remain separate actions.

## Limits and next gate

The built root page remains the Gate I placeholder. Investigator execution, bounded worker/provider integration, browser discovery/selection and inspection UI belong to Gate III. Draft/edit/review/closure commands belong to Gate IV. Browser usability, live extraction, release fault/performance trials and owner evaluations are unexecuted. The schema foundations and synthetic workflow recovery tests do not establish those features' acceptance.

Constitution compliance: domain rules remain pure; financial truth and eligibility remain deterministic; evidence and uncertainty are preserved; no external business write, sending transport, additional application agent, or automatic closure was added. Ownership, durable command identity and recovery now have real SQLite/process evidence. Passing these checks does not authorize the next phase.

Gate II ends at T038. The owner subsequently approved this evidence and authorized Gate III, T039–T061. Gate IV requires a new explicit authorization after Gate III review.
