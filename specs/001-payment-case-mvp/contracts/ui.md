# User Interface Contract v1

The application is a fictional, single-owner case workspace. It must disclose STUB/LIVE and REFERENCE/REAL modes and the lack of authentication. It must not solicit real banking/customer details or imply a customer message was sent.

## Views and transitions

| View | Required content | Actions and state behavior |
| --- | --- | --- |
| Demonstration selection | Existing nondeleted copies from GET /demonstrations, catalogue/variant/clock labels, explicit create action | Restore a valid saved selection; otherwise open the sole copy, show a chooser for multiple copies, or show explicit creation for none. Listing failure is a recoverable error. Never seed/reset on navigation or restart. |
| Case list | Exactly three fictional cases, client/invoice/currency/due date, prior investigation, lifecycle/review-required indicator | Open case directly; fresh demo/registered variant creates another isolated copy. No reset-on-refresh. |
| Case evidence | Invoice, raw messages, ledger status, claims, commitments, missing/unavailable records, stable source links | Inspect without investigation; separate verified transactions from claims and invoice allocation from promise attribution. |
| Timeline | Event time/source ordering, distinct undated group, arrival time separately | Source links open exact preserved versions, including corrections/reversals and original wording. |
| Investigation | Acknowledgement, running/complete/limited/incomplete status, evaluation time/snapshot, one action and concrete step | Start explicitly; show previous completed result during running/failure; block duplicate start while active. Reach visible terminal/connection limitation by 60 seconds. |
| Findings/recommendation | Balance certainty, explicit attribution/fulfillment, contradictions, unresolved facts, evidence-backed reasons | VERIFY_PAYMENT never becomes a demand. WAIT shows applicable due/promise dates and the earliest future review boundary; at equality mark review required, without contact. Reinvestigation may still WAIT on another condition. CLOSE offers owner confirmation. |
| Draft review | Exact recipient/invoice/text/version, source-backed financial clauses, validation reasons and review history | Save edit, approve/reject exact version. Edits create unapproved versions. No Send button or sent status. Explain safe wording alternatives for blocked unsupported clauses. |
| Owner decisions/history | Saved dispositions, drafts/reviews, starts/failures, approvals/invalidation, closure/reopening, evidence arrivals | Failed saves remain visibly unsaved. Unknown outcomes reconcile by operation ID; no optimistic saved/approved/closed claim. |
| Fixture update preview | Registered version/event, exact copy/case target/revision, source/clock changes and case-bound hash, explicit fictional label | Fetch the case/event preview and apply only after owner confirms those exact changes; revision/hash conflicts require a new preview and confirmation. Preserve prior results as historical. Never expose a manual Verify payment toggle. |

Case navigation, evidence, result, draft and history must be directly accessible without reconstructing chat. P1 comparison summaries and optional chat are deferred.

Persist selected_demonstration_id as a browser preference and revalidate it against the server list on root load. Explicit creation selects its returned ID. Clear a deleted/missing selection and apply the discovery rules again. A server/listing failure does not clear the preference or imply that no copies exist. Keep pending operations, unsaved text and receipt reconciliation scoped to their originating copy when switching; never retarget them to the new selection.

## Critical review behaviors

- Starting another investigation invalidates approval immediately after persisted start. While it runs, approval/closure is blocked. A failed start that never committed cannot invalidate a saved approval.
- If rerun ends INCOMPLETE with unchanged current evidence/time, enable a **new explicit review** of the eligible earlier draft; do not show its historical approval as current. If evidence changed or a newer successful result superseded it, keep approval blocked. FV-17 covers these paths.
- FV-16 linked partial promise: display INR 30,000 remainder, fulfilled INR 20,000 promise, FOLLOW_UP despite future promise date. Unlinked: same known balance, unresolved attribution, VERIFY_PAYMENT and no demand.
- FV-18: both future-date orderings initially review at 25 October 00:00 IST; reinvestigation at that boundary still WAITs until 27 October 00:00. At the latter boundary FOLLOW_UP is eligible. Expiry marks the earlier result for review without initiating contact.
- Show WAIT/CLOSE and internal ledger-review reasons for no customer draft. Customer clarification drafts request missing evidence neutrally. Draft failure leaves the saved recommendation and a failed-step retry option.
- CLOSE recommendation alone changes no lifecycle. Explicit eligible closure confirmation shows invoice/result and settlement references. Contradictory evidence on a closed case flags review; only explicit reopening changes lifecycle.

## Error, empty, loading and access behavior

Saved evidence remains inspectable during model failure. Empty ledger results distinguish explicitly complete/no entries from unavailable retrieval. Running attempts include readable status and retry limits, not endless progress. Missing records and unknown amounts remain labeled. Conflicts show both originals without accusing the customer.

Every P0 task must work by keyboard with visible focus and descriptive control labels. Announce async status/errors without moving focus unexpectedly. Use text/icons in addition to color; preserve readability at 200% text enlargement. Disable ineligible actions with a visible reason; server-side checks remain authoritative after a concurrent update. Restore pending operation reconciliation after refresh, preserving text that was not saved.

## Acceptance references

Case/evidence: AC-01–AC-03. Investigation/action: AC-04–AC-09, AC-21–AC-27. Draft/review: AC-10–AC-15, FV-10/FV-11/FV-17. History/closure: AC-16–AC-20, AC-25. Accessibility/performance/truthful labels: NFR-001–NFR-008. All measurements in the spec remain targets, not results of this design.
