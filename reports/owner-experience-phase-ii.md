# Owner experience Phase 2

Date: 25 October 2026. Branch: `003-owner-experience`, based on `1f13b86` plus
the owner-accepted, uncommitted Phase 1. Scope: [specification](../specs/003-owner-experience/phase2-spec.md),
[plan](../specs/003-owner-experience/phase2-plan.md) and [tasks](../specs/003-owner-experience/phase2-tasks.md).
Owner accepted Phase 1 and explicitly authorized Cedar guidance and Phase 2.
Local implementation and engineering verification are complete; the owner approved the phase and authorized Phase 3 on 25 October 2026. The complete browser run was not green; its failures and unchanged isolated rechecks are recorded separately below.

## Result

Findings offers What changed on demand, and completed History records link to a
named comparison. Two completed saved investigations show their recorded action,
reason, status, certainty-labelled money, due/review/evaluation times and identities.
Both originals remain inspectable with their exact hashes and source-linked findings.
No balance, recommendation or past eligibility is recalculated.

Differences distinguish action, evidence, other saved findings, evaluation-only and
identical comparable results. Sources are matched by stable ID plus exact version;
new, absent and replaced versions remain distinct. Evidence event time and arrival
are displayed separately. Saved commitment identity governs comparability; missing
or duplicate identities and unsupported/legacy/different profiles have explicit limits.
Unknown amounts remain unknown, and formatting retains arbitrary-precision integers.

Automatic history discovery reads at most three default 50-event pages. Server
completion sequence orders the pair. Partial history never claims the latest pair;
the owner can load another page or select two ordered records. Newer running or
incomplete attempts remain separate. A changed completed head makes the selection
historical. Copy/case navigation discards late reads; errors leave saved Findings
available. Comparison, source inspection and original inspection use only GETs.

Cedar guidance now tells the owner to check the bank statement or accounting records
outside PromiseKeeper. It explains the fictional settlement update and reinvestigation
route without claiming a bank integration. The customer's original statement and
all saved next-step/result/source text and hashes remain unchanged.

## Verification record

- Accepted Phase 1 frontend baseline: 111 passed.
- Pure helper RED: eight observed failures against empty implementations; GREEN: eight passed.
- Initial panel RED: 13 failed, one existing navigation safeguard passed. The completed
  panel and helper checks passed; History link and focus/missing-record refinements
  each had observed RED failures before their implementations.
- Test setup corrections retained: new tests initially assumed a rupee glyph where
  the existing formatter uses INR, and needed selector/hash queries scoped to one side.
  Fixture type annotations were narrowed to the deterministic profile; typecheck passed.
- One independent read-only reviewer found no Critical/Important and two Minor issues.
  Both were treated as material by the executor: duplicated current/historical heading
  labels misidentified the original for screen readers, and empty selector state could
  prevent choosing a visibly valid first record after pagination. Three regressions
  failed before the single fix pass; per-instance IDs and explicit empty options fix them.
  No declined behaviors and no deferred findings. Full frontend after fixes: 138 passed;
  production build/typecheck passed. Reviewer did not run tests or accept the product.
- Initial focused Chrome attempt failed at the existing ten-second isolated-server
  readiness budget. An unchanged retry ran two tests against the previous dist and
  failed on missing new controls. Rebuilding corrected that test setup; the next
  attempt again hit readiness. A separate unmodified STUB server diagnostic became
  ready in 10,062ms, just beyond the existing budget. No readiness or product deadline
  was changed. These failed attempts remain retained; an unchanged warmed recheck passed both new journeys (2/2). A full-suite attempt then failed at the same global readiness limit before tests started.
- Screenshot verification found the initial new large-text test had not overridden the
  root font rule. A computed-size assertion failed at 16px instead of the required
  32px; the test now uses an explicit override and retains that assertion. Desktop,
  390px and actual 200% (32px root size) screenshots were inspected; all amounts and
  controls remain readable without sideways page overflow. Both new Chrome journeys
  passed again inside the full suite after this test correction.
- Full backend regression: 868 passed, one intentional LIVE skip, exit 0 in 592.80 seconds. LIVE was explicitly disabled.

- Complete serial offline Chrome run: **85 passed, 3 failed, 1 intentional LIVE skip**,
  exit 1 in 10.2 minutes. The new Phase 2 journeys both passed, including actual 32px
  text and the Cedar no-write/immutable-history/explicit-closure assertions.
  The keyboard journey encountered a transient storage-read error leaving its view
  at the prior running revision; exact preview correctly refused that stale revision.
  Saved-selection restart and literal-legacy-byte tests hit the unchanged ten-second
  backend readiness budget, before their affected browser assertions.
- Unchanged isolated three-test recheck: **2 passed, 1 failed**. Keyboard-only journey
  passed in 31.0s; legacy byte preservation passed in 25.7s. Saved-selection restart
  again hit readiness. Its subsequent unchanged isolated recheck **passed** in 11.7s
  (19.7s including setup). All three original failures remain failures in their full
  run; isolated outcomes do not turn that run green. Together these runs cover all
  88 offline checks successfully at least once. No readiness, product deadline,
  money, source-byte or approval assertion was weakened. No backend/harness source
  change was made for the startup variability.
- `git diff --check` and all twelve scoped specification/report file links passed.
  Local product evidence and traces are retained in ignored `.runtime/owner-ux-phase2`
  and `.runtime/e2e`; initial failures, old-dist run, text-scale RED and rechecks are
  retained. No human study, LIVE qualification or owner exit acceptance is inferred.

## Owner review route

1. Open Cedar in a fresh Baseline STUB copy, investigate, and read the payment-check
   guidance in Findings. Check the original customer message and verified ledger.
2. In History, preview `PK-003-U1`, inspect the exact settlement, confirm the update,
   then investigate again. This is fictional evidence, not a real bank import.
3. In Findings choose Compare saved investigations. Check Verify payment to Review
   case closure, contested recorded INR 60,000 to verified INR 0, and the exact new
   `PK-003-L2` ledger version. Its settlement predates its arrival in this case.
4. Inspect both saved originals and an exact source; check keyboard focus return.
   Return to History and use Compare this investigation to open a named pair.
5. Confirm that the case stays open throughout comparison. Closing still requires
   the existing separate Review case closure and explicit confirmation. Check the
   comparison at desktop, 390px and 200% text sizes.

## Boundaries

No backend, schema, API, dependency, financial or approval rule changed. No LIVE calls,
commit, push, merge, real-data import or customer sending. Phase 3, publication and
formal release acceptance remain separate owner decisions. New agents remain
unqualified on LIVE models, and the five-owner study remains unexecuted. Required
human observations are not supplied by this engineering verification.
