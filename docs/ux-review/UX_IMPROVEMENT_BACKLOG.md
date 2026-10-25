# PromiseKeeper: UX improvement backlog

**Date:** 25 October 2026. **Baseline:** `002-multi-agent-upgrade` / `1f13b86`. **Status:** proposed, unapproved backlog; no new application tasks have been activated.

## Prioritization method

Optimize for the owner's ability to make and explain a safe next decision, then the five-minute demonstration. Prefer reuse of current reads/components over a new API, persistence model, framework or agent. High visual impact alone is not sufficient. Effort estimates are engineering judgments for one engineer familiar with this repository, including focused regression work; they are not measured delivery times or commitments.

- **P0:** proposed submission scope/readiness; do first, reduce scope if review or verification time is threatened.
- **P1:** useful after P0 is verified and reviewed.
- **P2:** post-submission; intentionally excluded now.

These priorities do not alter original MVP priorities. In particular, comparison remains deferred AC-28/FR-024 until the owner explicitly approves promoting it for this increment.

## Ranked UX work

| Rank / ID | Scope and gap references | Priority | User value / demo impact | Effort | Regression risk | Architecture / reuse |
| --- | --- | --- | --- | --- | --- | --- |
| 1 · B-01 | Decision-first Findings: currentness, financial facts, reason/source and one appropriate action before expanded technical trace. Plain owner labels and separate advice/message/closure framing. UX-01/03/07. | P0 | High / high: the owner can explain the recommendation without agent vocabulary. | 1–2 h | Low–Medium: headings, currentness and action eligibility must remain accurate. | Frontend only; `FindingsView`, `FinancialSummary`, `OwnerDecisions`, existing labels and CSS. |
| 2 · B-02 | Explicit case-opening focus and compact completed briefing; keep current tabs and saved selection. Selected-case focus must also work when reopening the already-selected case. UX-04/12 subset. | P0 | High / high: a demo click actually reveals the case decision. | 0.5–1 h | Medium: keyboard focus, background refresh and cross-case state. | Frontend only; `App`, `MorningReview`, case-heading ref. |
| 3 · B-03 | Read-only What Changed for two completed saved investigations, source links and truthful limitations. UX-02. | P0, conditional on scope approval | High / very high: explains why a claim becomes verified settlement without rewriting history. | 3–5 h | Medium: historical pairing, pagination, null money, legacy profiles and response scoping. | Existing history/attempt/evidence reads; new presentation helper/component, no provider/API/schema changes. |
| 4 · B-04 | Compact truthful progress/saved/fallback states and locally saved feedback wording. UX-06/10. | P0 | High / medium: trustworthy execution rather than a decorative progress animation. | 1–2 h | Medium: incomplete versus complete/draft-ready distinctions and polling deadlines. | Existing activity/attempt fields; `AgentTrace`, controls, `FeedbackButtons`. No invented current node. |
| 5 · B-05 | Enriched promise/evidence timeline: business titles, amounts and saved commitment state; event versus arrival time. UX-05. | P1 | High / high, but comparison already tells the core change story. | 2–4 h | Medium: correct source/result context, unknown dates and supersession. | Existing `Timeline`, saved commitments and evidence. |
| 6 · B-06 | Evidence grouping and friendlier source names; keep exact versions and replaced records inspectable. UX-08. | P1 | High / medium. | 1–2 h | Medium: must not hide contradictory or superseded evidence. | Current evidence reads, source dialog and labels. |
| 7 · B-07 | Friendly named demo scenarios, setup guidance and consistent copy labels beyond the P0 terminology pass. UX-03 extension. | P1 | Medium / medium; valuable for a stranger cloning the project. | 1–2 h | Low–Medium: preserve exact copy identity and explicit creation/replay behavior. | Current catalogue/copy picker. No import flow. |
| 8 · B-08 | Human history summaries and correct pagination label; technical payloads under Developer details. UX-09. | P1 | Medium / medium. | 1–2 h | Low–Medium: historical links and ordered event loading. | Current `CaseHistory` and ascending sequence cursor. |
| 9 · B-09 | Separate loading/error regions and discoverable recovery of latest Morning Review. UX-11. | P1 | High / medium; larger state-handling surface than a wording fix. | 2–4 h | Medium: preserve pending writes and avoid stale result flashes. | Existing API errors/receipts and component state. |
| 10 · B-10 | Broader navigation consolidation or deep links after observing real use. | P2 | Unknown / low for the short demo. | Medium–High | High: selected copy/case/tab, pending buffers and history inspection. | Would change navigation/state architecture; no current justification for a router migration. |
| 11 · B-11 | Natural promised-day wording in customer templates. UX-13. | P2 | Medium / low–medium. | Medium | High relative to copy-only work: saved text, validation and deadline invariants. | Requires separate template/validator specification and owner approval; not frontend display substitution. |
| 12 · B-12 | Real-data intake, authentication/hosted SaaS, communication delivery, voice or more agents. | P2 / excluded | Future value unknown / distracts from current signature. | High | High: access, privacy, evidence authority, side effects and qualification. | Substantial new product/architecture scope; no implementation recommendation for this submission. |

B-01/B-02/B-04 form the first coherent “owner can find and trust the next action” increment. B-03 is a separate comparison increment. Do not combine every row into one branch-sized task.

## Readiness work, separate from UX feature estimates

| ID | Decision/evidence needed | Priority and gate |
| --- | --- | --- |
| R-01 | Reconcile publication versus formal release acceptance, current architecture versus constitution/specs, and explicit activation of deferred comparison. | P0 before dependent implementation; owner decision/document approval. No existing artifact is amended by this review. |
| R-02 | Decide what the demonstration may claim: honest STUB orchestration versus a separately authorized and measured LIVE run. | P0 before submission claims. Offline evidence is not real-model qualification. |
| R-03 | If LIVE morning review is selected, review/fix the source-verified start provenance mismatch and assess retained graph/optional-service risks in bounded technical work. | Conditional P0 for that LIVE path; separate engineering authorization. A UX label cannot correct persisted provenance. |
| R-04 | Rehearse the exact approved build serially; verify source/claim distinction, currentness, approvals, no-send and fallback. Measure the actual five-minute sequence. | P0 after the chosen UX phase(s), before recording. |
| R-05 | Actual five-owner observations and new-agent LIVE evaluations/calibration. | Required for the relevant acceptance/quality claims; unavailable evidence stays unexecuted. A competition prototype can be labelled honestly without manufacturing acceptance. |

## Recommended scope and tradeoff

**Preferred P0:** B-01, B-02, B-04, then B-03 after a separate review. Budget approximately **6–10 engineering hours**, plus **1–2 hours of whole-flow verification/rehearsal and owner review**. Scope uncertainty is highest in comparison pairing and safe progress handling; leave contingency rather than assuming the lower bound.

**Minimum fallback:** complete and review the decision-first increment, then demonstrate existing PK-003 reinvestigation with manual historical inspection. If comparison does not fit, mark it unbuilt and omit its UI claims. Do not trade immutable history, approval fences or verification for a deadline.

**Do not spend submission time on:** new agents, decorative animations, a six-screen rewrite, broad dependency changes, a new dashboard metrics layer, or integration work. Existing deterministic finance and evidence-linked decisions are the differentiator.

## Success checks for the proposed scope

These are future verification targets, not measured user results:

1. A reviewer can identify the selected invoice, current/historical state, labelled remainder and next responsible action without opening Developer insights.
2. A case opened from Morning Review reaches visible, keyboard-focused case context; polling never steals focus.
3. PK-003 comparison distinguishes the old contested INR 60,000 remainder from the new verified INR 0, links both saved investigations and the CR-T2 evidence, and leaves the case open until explicit closure.
4. An incomplete newer attempt does not replace completed comparison results; legacy/missing fields never become false “no change.”
5. The owner can approve/reject exact saved wording and copy only eligible approved text; the UI never calls that sending.
6. No fake progress, unsupported financial authority, automatic approval or new write path is introduced.

Acceptance details and per-phase checks are in [PHASED_IMPLEMENTATION_PLAN.md](PHASED_IMPLEMENTATION_PLAN.md).
