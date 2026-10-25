# Feature specification: owner experience Phase 1

**Branch:** `003-owner-experience` (baseline `1f13b86`). **Date:** 2026-10-25.
**Authorization:** owner instruction, “Improve the ux as per plan.”
**Designated reviewer:** project owner. **Status:** Phase 1 accepted by the owner on 2026-10-25. Phase 2 is authorized in [phase2-spec.md](phase2-spec.md).

## User story and scope

As a small-business owner, I can open a saved payment case, understand its financial
basis and responsible next action, and distinguish saved results from work still in
progress without reading agent configuration.

Implement B-01/B-02/B-04 and UX-AC-01–07 from
[the reviewed roadmap](../../docs/ux-review/PHASED_IMPLEMENTATION_PLAN.md).
Use the existing casebook, five tabs, exact evidence, backend reads/commands and
server-owned eligibility. No new framework, provider, API, agent, financial rule,
sending capability or dependency. No LIVE calls, commit, push or merge is authorized.

Comparison AC-28/FR-024 was deferred during Phase 1. The owner's subsequent acceptance
and Phase 2 instruction activate it only under the separate bounded Phase 2 specification.

## Acceptance scenarios

- **UX-AC-01:** Current Findings puts certainty-labelled money, supported reason,
  relevant sources and action before optional developer events. Explicit case opening
  reveals that decision context at 1280×800 without traversing the trace.
- **UX-AC-02:** Technical execution details/provenance remain accessible through
  labelled disclosures. No model IDs or internal revision vocabulary are required
  for ordinary decisions; no prompts or hidden reasoning are exposed.
- **UX-AC-03:** An explicit case selection focuses its heading and reveals the case,
  including a Morning Review click on the already-selected case. Background refresh
  never steals focus. Switching cases/copies preserves the existing pending-work and
  stale-response protections. Narrow/200% text layouts retain reachable controls.
- **UX-AC-04:** FOLLOW_UP, WAIT, VERIFY_PAYMENT and CLOSE expose appropriate actions.
  Advice disposition, message approval and case closure remain distinct. Historical,
  limited, running and unknown-balance states retain their actual meaning.
- **UX-AC-05:** Distinguish a saved recommendation with preparing/failed drafting
  from an incomplete investigation. Describe only confirmed progress; quiet or missing
  events do not become an invented current agent. Preserve existing polling budgets,
  case watchdog and safe unknown-outcome reconciliation.
- **UX-AC-06:** A false feedback-forwarding flag says the feedback was saved locally,
  without claiming a service is unconfigured or an agent has learned. Confirmed
  forwarding may appear in optional delivery details.
- **UX-AC-07:** Existing exact draft save/review/copy and closure behavior, payloads,
  stale/pending/changed-head blocks and source/history integrity remain unchanged.
  Layout, navigation and disclosures add no application mutation.

## Failure and uncertainty

Keep saved evidence/results inspectable on unavailable reads. An unknown write outcome
requires existing operation reconciliation, not a new operation ID. A recommendation
saved before draft failure remains saved. Missing trace data is an explanatory gap,
not proof of success or a reason to fabricate stages. No comparison is implied by
reordered history or new wording.

## Governance and release boundary

Constitution IV is synchronized with the previously owner-approved ADR-010 roles; no
role is added by this feature. Original financial/approval/history requirements remain
in `specs/001-payment-case-mvp`. Historical qualification, new-agent LIVE qualification,
fictional-build publication and the missing owner study are separate claims.
The deadline remains 26 October 2026, 10:00 IST and does not waive review or safety.

## Verification and exit

Observe failing behavior tests before implementation. Run focused component tests per
task, complete frontend tests/typecheck/build and offline browser journeys serially;
retain financial/approval/recovery regressions. Inspect desktop/mobile screenshots.
Run an independent whole-change review. Record actual outcomes, skips and failures.
Stop after Phase 1 for owner review before comparison implementation or publication.
