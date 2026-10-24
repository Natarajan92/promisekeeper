# Persona walkthroughs (simulated)

**Method.** On 24 October 2026 the agent ran six persona journeys in a real browser (Chrome, Playwright) against the offline STUB server with fictional data, captured screenshots, reviewed them for usability gaps, fixed the important gaps with failing tests first, and re-ran the journeys. These are **simulated walkthroughs, not a user study**. They do not replace the five-owner evaluation, which remains unexecuted.

The journeys are automated in [tests/e2e/personas.spec.ts](../tests/e2e/personas.spec.ts) and pass (6 of 6).

## Personas and what each must be able to do

| # | Persona | Must be able to | Result |
|---|---|---|---|
| P1 | Busy agency owner, not technical | Start one morning review, read the briefing, open the case with a ready draft, see how the AI team worked | Passes |
| P2 | Relationship-protective owner (client says "already paid") | See VERIFY_PAYMENT with no demand wording | Passes |
| P3 | Returning owner after new evidence | See the old result as historical; the supervisor re-investigates only that case | Passes |
| P4 | Bookkeeper | After the settlement record, see a closure recommendation, inspect exact sources, and find the case still open until confirmation | Passes after fix G2 |
| P5 | Sceptical owner testing AI safety | Give feedback; see agent hand-offs; have an unsafe edit (fee and amount in the note) blocked | Passes |
| P6 | Small screen, keyboard only, 200% text, FV-12 injection message | Reach "Start morning review" by keyboard; no sideways scrolling; readable header | Passes after fix G1 |

## Gaps found and what happened

| ID | Gap (what the person experienced) | Persona | Severity | Status |
|---|---|---|---|---|
| G1 | At phone width with 200% text, the hidden "Skip to case workspace" link showed at the top and the PromiseKeeper wordmark broke mid-word | P6 | Important | Fixed (skip link hidden until focus; header wraps; wordmark scales). Pinned in P6. |
| G2 | Source buttons said "Inspect exact source version" but their accessible name was "Open source …", so voice-control users could not say what they saw (WCAG 2.5.3) | P4, P6 | Important | Fixed (name now starts with the visible label). Pinned in P4, the accessibility suite and unit tests. |
| G3 | Blocked drafts listed raw codes ("note has digits", "unsupported clause") | P5 | Important | Fixed (plain guidance for every draft-safety reason). Unit test. |
| G4 | After the supervisor had already investigated, the case still led with a primary "Investigate case" button, inviting a pointless re-run | P1, P2 | Important | Fixed (button is secondary when a current recommendation exists, with "Investigate again only if something has changed"). Unit test. |
| G5 | The AI team trace sat at the very bottom of Findings, below case actions | P1, P5 | Important | Fixed (trace follows the next step). Unit test. |
| G6 | The Payment rules step showed "FOLLOW_UP: VERIFIED_OVERDUE_BALANCE" | P1, P5 | Important | Fixed ("Follow up: verified overdue balance."). Backend test. |
| G7 | System jargon: "Balance certainty: KNOWN", "Designated source authority", "Non-authoritative source", "revision N", copy labels with REFERENCE and IDs | P1, P4 | Minor | Partly fixed ("Balance confirmed by verified records."). Remaining labels deferred because reviewed browser tests pin them. |
| G8 | "Was this draft useful?" was asked before the draft was shown | P5 | Minor | Fixed (asked after the review actions). Unit test. |
| G9 | The template states "Your earlier payment promise reached its deadline at 21 October 2026, 00:00 IST" for a promise "by 20 October" | P1 | Minor | Deferred: template-owned wording covered by reviewed draft-validation tests; change needs owner sign-off. |

## Screenshots

Saved locally under `.runtime/personas/` (ignored by Git): first run, briefing, findings with trace, review, verify-payment, stale result, history, source dialog, blocked edit, and phone width at 200% text.
