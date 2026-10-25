# Owner experience Phase 2: compare saved investigations

Owner authorization: 25 October 2026, following Phase 1 acceptance. Baseline: existing
Phase 1 work on `003-owner-experience`, based on `1f13b86`. Reviewer: project owner.

## Scope and contract

Activate original US6 / AC-28 / FR-024 for this bounded increment; original MVP
reports retain their historical deferred status. Implement B-03 / UX-AC-08–14 in
the [approved roadmap](../../docs/ux-review/PHASED_IMPLEMENTATION_PLAN.md) and its
[comparison contract](../../docs/ux-review/PROPOSED_USER_JOURNEY.md#proposed-comparison-contract).

An owner can open What changed from Findings or History, compare two completed
COMPLETE/LIMITED investigations in the same copy/case, and inspect both originals
and exact source versions. Saved actions, status, reason, money/certainty, review
and evaluation times are shown without recalculation. Source differences use stable
ID and version; commitments use saved stable identity. Claims, questions, issues,
contradictions and limitations remain source-linked in the saved originals.

The latest pair is selected by completion-event sequence only after history is
exhausted. Automatic discovery is limited to three 50-event pages; partial history
is explicit and permits one more page per owner click or explicit pair selection.
Incomplete/running attempts remain separate. A later completed head makes a loaded
pair historical. Late responses after navigation are discarded; read errors leave
Findings inspectable. Missing records, unsupported/legacy/different profiles and
unresolved commitment identity produce limitations, never guessed equivalence.

Summaries distinguish action changes, same-action evidence changes, other saved
finding changes, time-only changes and identical comparable results. They state
observations without inferring causality. Unknown money stays unknown; event time
and source arrival are distinct. Cedar before/after U1 must show VERIFY_PAYMENT to
CLOSE, contested recorded INR 60,000 to verified INR 0, and added CR-T2 evidence.
Both hashes remain intact and the case stays open until explicit closure.

Also clarify VERIFY_PAYMENT guidance: check payment in bank/accounting records
outside this app; the demo's staged settlement update represents verified evidence.
No bank integration or import is implied. Do not rewrite saved next-step text or
the customer's Cedar statement.

## Boundaries and verification

Read-only frontend implementation using existing history/attempt/evidence GETs.
No backend/schema/dependency/provider/financial/approval changes, new mutation,
LIVE evaluation, publication or Phase 3. Existing source dialog and historical
Findings preserve exact provenance and recorded-advice labels. Keep the Phase 1
visual language and optional technical disclosures; comparison uses responsive
before/after rows and explicit state labels.

Verify helper and component behavior RED/GREEN, including partial pagination,
scoping, delayed navigation, missing records, head changes and no-write behavior.
Run full frontend, typecheck/build, backend regression and serial offline Chrome
suites. Exercise actual Cedar update/reinvestigation/comparison/explicit closure,
inspect desktop/mobile/200% screenshots, and obtain one independent code review.
Stop with a local reviewable diff for owner acceptance; studies remain unexecuted.
