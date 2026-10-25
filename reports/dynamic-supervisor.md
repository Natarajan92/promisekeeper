# Planning supervisor, six cases and urgent-first overview

Branch `004-dynamic-supervisor`, from main `868701c`. Decision record: ADR-011 in `specs/001-payment-case-mvp/research.md`.

## What changed

- **Planning supervisor.** The morning review used to take due cases in a fixed loop. A supervisor agent now chooses one step at a time, investigating a pending case or finishing, and re-plans after every result. Code still decides which cases are due, closed or running, and validates every choice:
  - the chosen case must be waiting in this review
  - finishing is refused while a due case waits
  - the reply must match a strict schema with no extra fields
  - an invalid choice falls back to rule order for that step
  - an unavailable planner is switched off for the rest of the run, so an outage cannot stall the review
  - due cases are always investigated, and the planner may also re-check a case whose recommendation is still current
  - the planner sees structured facts only, never customer message text
- **Separate supervisor model.** `PK_SUPERVISOR_MODEL` sets the planner's model independently of the extractor. When it is empty, `PK_NEBIUS_MODEL` is used.
- **Six demo cases.** Three fictional cases were added:
  - PK-004 Saffron Foods: a Hinglish promise that expired, so the recommendation is a follow-up
  - PK-005 Lotus Interiors: a Hinglish payment claim with no ledger match, so the recommendation is to verify the payment
  - PK-006 Banyan Logistics: a fully settled ledger, so the recommendation is to close

  Migration `010_six_cases.sql` widens the case check for fresh and existing databases. Older saved copies keep their three cases. Release measurements and the reviewed evaluation inventories stay on PK-001 to PK-003.
- **Morning review strip.** Case cards sit in one sideways-scrolling row with previous/next controls.
  - **Same rule as the overview.** The strip and the case overview share one attention rule and one order: cases needing attention first, each group in the supervisor's latest plan order, then catalogue order.
  - **Current status, not a snapshot.** The strip shows each case's current status rather than the snapshot saved at review time, plus a "Needs attention" or "Can wait" badge.
  - **Investigation order shown separately.** The supervisor's own order appears as "Checked #N by your supervisor", along with its reason.
  - **Steps name each decision.** In "See what the supervisor did", each supervisor step says what it decided; fallbacks are marked "(rule order)".
- **Supervisor instructions (prompt `supervisor-2`).** Two problems came up in the owner's first LIVE run:
  - It ranked a fully paid case first as "missing balance details, needs urgent verification".
  - It wrote internal case codes in reasons meant for the owner.

  The instructions now say that INR 0.00 means nothing is owed (check it last), that a null balance or action only means the case is not yet investigated, and that reasons must name the client, not a case code. The supervisor suite now also reports `reason_clean`, the share of reasons without case codes.
- **Case overview.** Only cases that need attention are shown by default: not yet investigated, evidence changed, review date reached, a follow-up, or a payment check. A "Show all" toggle shows the rest. The open case stays visible.

## Model choice for the supervisor

The planner picks one of two moves from structured facts, under code validation. That makes a smaller, faster decision model a plausible fit. This has **not been measured**: no LIVE provider calls were made for this work. `evaluate --suite supervisor` scores each model on validity (passes the guardrails), accuracy (an owner-acceptable choice), errors, p50/p95 latency and mean tokens. It uses 10 scenarios covering:

- fresh cases
- a review-required case
- a payment claim versus a larger follow-up
- all cases current
- one due case left
- a review date that is close
- an instruction hidden in a client name
- a re-plan after a failure
- a due case with a zero balance
- a mixed mid-review re-plan

To compare models, run with LIVE credentials and owner approval:

```powershell
uv run --project backend python -m promisekeeper.cli evaluate --suite supervisor --catalogue release-0.1 --repeats 3 --models <current-model>,<smaller-model> --output reports/supervisor-evaluation-new.json
```

A suggested rule: choose the smallest model with validity 100% and accuracy at least that of the current model, then compare p95 latency. Whatever a model does, guardrail failures fall back to rule order, so a weak model makes the order less useful but never makes it unsafe.

## Verification (offline, STUB)

- Backend: full suite passes. New tests cover:
  - the risk-first order and its reasons
  - the planner never seeing customer text
  - re-planning with outcomes
  - an invalid case
  - finishing too early
  - an unavailable planner
  - re-checking a current case
  - the guardrail unit cases
  - the offline evaluation suite and CLI model-name validation
  - the separate supervisor model setting
- Frontend: unit tests pass, including the case filter and the supervisor strip. Typecheck and production build pass.
- Backend: 882 passed, 1 intentional LIVE skip.
- Frontend: 145 unit tests passed.
- Browser: final full Chrome run, 90 passed and 1 intentional LIVE skip. That run includes a new browser test for the Hinglish cases. An earlier full run had 3 failures, kept here for the record:
  - One test still assumed three cases; it was fixed.
  - A comparison check hit a transient "Connection unavailable" from the test server.
  - A closed-case reopening check hit a test timeout.

  All three then passed in isolated rechecks and in the final full run.
- Screenshots were inspected at 1440px and 390px wide. There is no sideways page scroll at 390px and no page errors.

## Not established

- No LIVE evaluation of the planning supervisor or of any smaller model.
- No human usability observation of the new strip or filter.
- Hinglish wording in PK-004 and PK-005 is fictional and STUB-extracted. LIVE Hinglish extraction is measured separately by `--suite hinglish`.
