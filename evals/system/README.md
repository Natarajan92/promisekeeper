# PromiseKeeper system evals

This versioned set translates the owner's invoice questions into 65 fictional
scenarios with intent, inputs, literal expectations and automatic failure modes.
It complements the existing catalogue/synthetic-pack regression tests. Inputs are
newly authored but the author inspected the implementation; this is not a blind
statistical holdout, real-world distribution estimate or LIVE model qualification.

Run from the repository root with the existing backend development environment:

```powershell
backend/.venv/Scripts/python.exe scripts/evaluate_system.py --output reports/system-evaluation/my-new-run
```

Use a new output directory each time. The runner exits **1 when any case fails or
errors**. A failing result can be the correct outcome of an evaluation: do not
change expected answers to make the application pass. `results.json` records each
case, expected/actual/checks, business day, status, runtime, source fingerprints
and dataset hash. `results.md` is the scan-friendly table; `dataset.json` preserves
the exact input version. Intermediate results retain UNEXECUTED rows if interrupted.

The dev-only runner needs the already declared httpx dependency. It creates a fresh
SQLite database per scenario, starts the actual FastAPI application with explicit
STUB settings, exercises preview/commit and saved multi-agent investigation via
HTTP, then removes its temporary database. It never loads configuration files or
credentials. External DNS/TCP and tracing are blocked. TestClient HTTP is in-process;
the separately run Chrome suite exercises the real browser/server path.

| Track | Cases | Meaning of passing |
|---|---:|---|
| contract | 51 | Exact supported import, money, allocation and owner workflow invariants |
| safety | 7 | Ambiguous/conditional/quoted/owner-side wording cannot create unsupported confident advice |
| capability | 7 | Desired everyday wording/formats/date validation; safe refusal still exposes missing usefulness |

All supported deterministic and safety cases are required to pass. There is no
aggregate score that overrides an unsafe advice or financial/authority failure.
Monetary oracles use literal paise, independently authored from application helpers.
Each message/allocation observation also checks OPEN lifecycle and zero owner
reviews before any owner approval. Preview rejection must be atomic. UNKNOWN bank
status can be overridden only by explicit owner settlement attestation; PENDING
and REVERSED remain blocked. The suite does not independently establish that the
owner's attestation is true.

Scenario timing includes setup and persistence; it is not model or browser latency.
No SLO is imported from the attached image's illustrative RAG example. No messaging
transport exists; this evaluation does not qualify a future sending integration.

The first exploratory baseline exposed harness defects as well as product gaps:
M24's currency symbol was corrupted by shell encoding, W07 retained context that
correctly prevented closure, and A06 initially ignored the explicit owner settlement
attestation. Version 1.1 corrects those inputs/oracles, adds a no-attestation case
and strengthens atomicity checks. A terminal INCOMPLETE investigation is graded
as an observed application failure, rather than waiting until a harness timeout.
Original runs are preserved and are not the acceptance denominator.
Version 1.2 also checks saved currency and approval state directly; safety cases
allow either safe refusal or conservative accepted VERIFY_PAYMENT. Those grader
corrections came from independent review and retain their RED/GREEN evidence.

Version 1.3 supplies the new explicit owner-reviewed sender role for every message
(M32 is OWNER; the other messages are CUSTOMER). This changes the input contract,
not sender authentication. Version 1.4 deliberately changes **M21** from accepting
mixed instruction/promise prose with WAIT to refusing that unsupported document.
The prior WAIT expectation is stored in `previous_contract_expected`; all prior
reports remain intact. This is a capability restriction: report the other 64
unchanged action expectations separately from M21's new conservative contract.
Monetary and owner-control checks remain required throughout.

The expanded set adds 25 authored challenges, for 90 total. It covers sender-role
hash changes, additional conditions/attribution, currency/language variants, bank
row validation and overlap between generated and actual bank references. Run it
with a fresh output directory:

```powershell
backend/.venv/Scripts/python.exe scripts/evaluate_system.py --dataset evals/system/extended-cases.json --output reports/system-evaluation/my-new-expanded-run
```

See [the original findings](../../reports/system-evaluation.md) and
[the fix verification report](../../reports/system-eval-fixes.md) for candidate
fingerprints, regression/browser evidence, remaining limits and unmeasured areas.
