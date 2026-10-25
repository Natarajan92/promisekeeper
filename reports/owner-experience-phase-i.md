# Owner experience Phase 1

Date: 25 October 2026. Branch: `003-owner-experience`, based on `1f13b86`.
Scope: [approved feature](../specs/003-owner-experience/spec.md) and
[implementation plan](../specs/003-owner-experience/plan.md). Local implementation;
owner accepted this increment on 25 October 2026 and authorized [Phase 2](../specs/003-owner-experience/phase2-spec.md). The verification below is the retained Phase 1 checkpoint.

## Result

Findings now puts the saved recommendation's financial basis, certainty, reason,
exact source links and next action before optional developer insights. Preparing
or failed message generation stays distinct from a saved recommendation. Live
progress describes only confirmed state and activity, including a quiet stream or
an exhausted activity polling budget.

Explicit case opening focuses and reveals its heading, including the same case
opened from Morning Review. Background refresh leaves focus alone. Completed
Morning Review keeps case choices visible and puts its full briefing behind a
disclosure. Feedback confirms its local save without inferring service configuration
or agent learning; confirmed forwarding has optional delivery details.

Case identifiers, exact source versions, money calculations, advice disposition,
message approval/copy, closure and pending-operation recovery use the existing
contracts. No backend, dependency or lockfile change; no provider evaluation or
sending capability was introduced. The constitution records the prior owner-approved
ADR-010 role exception, and README separates fictional-build publication from
outstanding formal acceptance.

## Verification

- Fresh frontend baseline: 104 tests passed. Observed intended RED failures for
  decision hierarchy, lazy trace, saved/draft distinction, explicit focus, collapsed
  briefing and feedback wording before implementing them. Quiet progress, polling
  budget and background-focus guards are covered; current component run: 111 passed.
- Production build and TypeScript checks passed.
- Initial targeted Chrome run: 10 passed, 1 failed. The first Morning Review detail
  read returned `503 STORAGE_UNAVAILABLE`; its completed-review assertion timed out.
  The unchanged-code isolated recheck passed, including case focus and the entire
  financial summary and review button within a 1280×800 viewport. The failed run
  remains a failure; the isolated result does not replace it.
- Full backend regression run: 868 passed, 1 intentional opt-in LIVE skip, exit 0.
- First full serial Chrome run: 85 passed, 1 intentional LIVE skip, 1 timeout in
  the existing literal-legacy-byte restart test. An unchanged isolated recheck
  also timed out. Its three backend startups each took roughly seven seconds,
  leaving insufficient time in the default 30-second total harness budget for
  fixture inspections and browser assertions. A read-only fixture optimization
  did not resolve it and was reverted completely.
- The legacy test now uses the existing restart tests' 60-second overall harness
  budget. Application deadlines, polling limits and every byte/data assertion are
  unchanged. The focused recheck passed in 37.2 seconds, confirming the previous
  budget was insufficient here. Final complete Chrome run: 86 passed, 1 intentional
  opt-in LIVE skip, exit 0 in 11.1 minutes. Earlier failed runs remain above.
- Desktop viewport screenshot inspected: decision context is readable without the
  technical trace. 390px/200% money viewport screenshot inspected: labels and full amounts wrap
  vertically, with no sideways overflow; case-heading focus and all-tab large-text
  accessibility checks passed in Chrome.
- One fresh independent whole-change code review found no Critical, Important or
  Minor issues. The later harness-budget correction was verified by its original
  failing test and the complete browser suite. Reviewer did not run tests or accept
  the product for the owner. No deferred Minor findings.

## Review steps

1. In a fictional STUB copy, start Morning Review and choose Northstar Analytics.
   The case heading should receive focus, and Findings should show the invoice,
   verified payments, remainder, reason, sources and review action before developer
   details. Reopen the same case and check its heading again.
2. Open Developer insights, then inspect an exact source and close the source dialog.
   Focus should return to the source link. Disclosure opening must send no POST.
3. Review a suggested message. Copy becomes available only after approving its exact
   saved version; editing it blocks copying. Advice acceptance does not approve a
   message, and a closure recommendation does not close the case.
4. Check WAIT, VERIFY_PAYMENT, limited/unknown and historical cases. Their existing
   dates, uncertainty and eligibility blocks should remain explicit. Preparing or
   failed message generation should point to Review without claiming a ready draft.
5. Submit feedback and check the save confirmation. At 390–400px and 200% text, check
   that case opening, money and controls remain reachable without sideways scrolling.

## Boundaries

No commit, push, merge or LIVE run was performed for this increment. Actual owner
usability acceptance, the five-owner study and new-agent LIVE qualification remain
separate evidence obligations. The owner subsequently supplied Phase 1 acceptance and Phase 2 authorization; publication remains separately gated.
