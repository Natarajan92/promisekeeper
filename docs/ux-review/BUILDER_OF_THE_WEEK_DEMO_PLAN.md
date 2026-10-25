# PromiseKeeper: five-minute demonstration proposal

**Date:** 25 October 2026. **Audited branch:** `002-multi-agent-upgrade` / `1f13b86`. **Status:** planned, not rehearsed or executed by this audit.

**Implementation update:** the owner subsequently accepted UX Phases 1 and 2 and
authorized Phase 3. The integrated comparison and an automated STUB rehearsal of
this route are now implemented; see the [Phase 3 report](../../reports/owner-experience-phase-iii.md).
The original audit and target narration below are retained. Automated UI timing
does not measure a human presenter or qualify the new agents for LIVE use.

The user's seven evaluation considerations are working quality criteria, not a verified official competition rubric. Official submission rules, judging weights and LIVE requirements are unknown. The route below uses implemented product capabilities; the comparison enhancement is explicitly conditional.

## Signature feature

**“The customer says paid. Should I chase them—or check the evidence?”**

Use Cedar Retail Labs / invoice CR-312 to show a customer claim becoming a verified settlement only when designated ledger evidence arrives. The original VERIFY_PAYMENT investigation remains intact, a new investigation recommends CLOSE, and the case stays open until the owner explicitly confirms closure.

This is stronger differentiation than an AI-written reminder: it shows why the product sometimes prevents a reminder, how agents stay within financial boundaries, and why changing evidence changes advice.

## What the product can show

| Demonstration element | Classification | Verified basis / limit |
| --- | --- | --- |
| Realistic overdue case | Already implemented | Northstar: INR 120,000 invoice, INR 40,000 verified paid, INR 80,000 remainder and an expired promise. Fictional catalogue, not a connected customer. |
| Payment evidence investigation | Already implemented | Exact message/ledger sources, source-validated extraction, deterministic reconciliation and source links. |
| Conflicting payment information | Already implemented | Cedar: INR 90,000 invoice, INR 30,000 verified paid and a claim for the remaining INR 60,000 / reference CR-T2. Recorded remainder is contested; VERIFY_PAYMENT is appropriate. |
| Justified next action | Already implemented | FOLLOW_UP / WAIT / VERIFY_PAYMENT / CLOSE plus saved reason, uncertainty and review date. |
| Human review or rejection | Already implemented | Exact saved draft decisions, save/edit validation, eligible approved copying; no sending. |
| Re-evaluate new evidence | Already implemented | `PK-003-U1` adds verified CR-T2 ledger payment of INR 60,000; fresh investigation yields verified zero remainder and CLOSE. |
| Explain the difference manually | Possible using existing capabilities | History opens the two saved investigations and source versions. Presenter narrates their recorded differences; no comparison panel exists yet. |
| Integrated What Changed panel | Requires small, bounded changes | Frontend read-only comparison over existing history/attempt/evidence reads, Medium complexity; original AC-28 activation needs approval. |
| Execution trace and owner pause | Already implemented, with limits | Real observed activity records, constrained drafting loop and persisted owner interrupt for a prepared draft. Activity/resume are best-effort; do not promise complete telemetry or a pause on no-draft paths. |
| Morning review | Already implemented | Deterministic supervisor selects due/changed/uninvestigated cases, invokes their graphs sequentially and generates a checked briefing/fallback. |
| Reliable new-agent LIVE performance | Unknown / evaluation required | STUB tests do not qualify Communicator, reviewer, briefing or optional services. Historical extractor qualification has narrower scope. |
| Real inbox/bank intake, hosted SaaS or delivery | Requires substantial changes / excluded | Not part of this demonstration or recommended P0. |

Source of exact names/amounts/events: [baseline.json](../../backend/src/promisekeeper/fixtures/baseline.json). Existing manual paths: [user test cases](../user-testing/test-cases.md), [scenario confirmation](../../frontend/src/history/ScenarioUpdate.tsx), [case history](../../frontend/src/history/CaseHistory.tsx).

## Honest mode choice

**Reproducible default:** STUB with the fixed REFERENCE date. Say: “These are fictional cases. This run uses offline stand-ins through the implemented workflow; code decides money and I approve messages.” Never describe scripted text or activity as a fresh model response. Keep the app's mode/date/no-authentication/no-send disclosure visible.

**LIVE option:** only after separate owner authorization, actual new-agent evaluation and a successful rehearsal on the exact configuration. The source-verified morning-start provenance mismatch must be reviewed before claiming accurate LIVE provenance. Preserve measured failures and fallbacks. Optional remote memory, tracing, alternative-provider review and autonomy are unnecessary dependencies for the signature story.

Offline reliability and LIVE model quality are different evidence. If competition rules require LIVE operation, obtain those rules and the required authorized evaluation rather than implying STUB satisfies them.

## Preparation checklist for the owner, not actions executed here

- Select the exact reviewed branch/build; resolve governance/acceptance wording before publication. Current review documents do not authorize merge or push.
- Use the existing setup guide and installed dependencies. Build/rehearse serially; no package change is needed for this plan.
- Explicitly create **one new Standard payment examples / Fixed sample date copy**. Initial business evaluation is **23 October 2026, 10:00 IST**, even if the recording occurs later. Preserve previous copies; do not reset a retained database.
- Keep autonomous reviews off for the scripted route so they cannot pre-investigate or change the timing of manual actions. Actual configuration has not been inspected by this audit.
- Leave optional hosted memory/tracing outside the critical route unless separately tested and approved. Use default local memory.
- Make the morning-review, Northstar review and Cedar scenario controls easy to locate. Know where History and exact-source inspection are before recording.
- Rehearse with a clock and record actual duration. Keep a separately prepared saved fictional demonstration as a labelled fallback; opening a saved result is not rerunning a model.
- Verify that `PK-003-U1` is unapplied in the fresh recording copy and that Cedar is still open. Use existing preview/hash/confirmation controls, not direct database edits.
- Capture a short backup of the verified run if permitted by the organizer; no failure should be edited into a misleading LIVE-success claim.

## Five-minute route

Times below are a **target script**, not measured performance. Morning-review latency is unmeasured on the new LIVE path; trim narration or inspect a labelled saved run if necessary.

| Time | Presenter action in the existing application | Business point / observable proof |
| --- | --- | --- |
| 0:00–0:25 | Show the three fictional cases and mode/date disclosure. State: “An agency owner needs to know whether to follow up, wait or verify before damaging a client relationship.” | Clear problem, audience and honest demonstration scope. |
| 0:25–0:55 | Start Morning Review. Open the Northstar outcome once the actual briefing/result is ready. If it is still running, explain the actual state rather than inventing progress. | Supervisor selects cases and coordinates work; no conversation or technical configuration required. |
| 0:55–1:35 | On Northstar, inspect invoice/ledger/promise sources and the saved INR 80,000 verified remainder. Open Review and explicitly approve the exact saved message. Copy only if eligible, while saying nothing was sent. | Evidence-grounded FOLLOW_UP, constrained drafting and human control. No need to demonstrate every editing feature. |
| 1:35–2:20 | Open Cedar. Read its “paid the remaining INR 60,000” statement and verified INR 30,000 ledger record. Show VERIFY_PAYMENT and reference CR-T2. | A customer claim is not settlement. The contested INR 60,000 is not a justified demand; internal verification can mean no customer draft. |
| 2:20–3:05 | In History, choose `PK-003-U1`, preview the exact fictional verified ledger addition, tick the explicit confirmation and apply it. Show the old result is historical before reinvestigating. | Evidence arrival is a deliberate recorded event, not a fabricated model discovery or an automatic bank connector. |
| 3:05–4:00 | Reinvestigate Cedar; show the new saved CLOSE recommendation and verified zero remainder. If the approved What Changed increment exists, inspect its before/after and evidence links. Otherwise open the prior investigation in History and narrate the two saved results manually. | Signature moment: new verified CR-T2 evidence changes advice while preserving both investigations. Do not present an unbuilt panel. |
| 4:00–4:30 | Confirm Cedar is still open, then use Review case closure and the separate explicit confirmation. Show the original history is retained. | AI recommends; the owner controls consequential case decisions. CLOSE is not automatic closure. |
| 4:30–5:00 | Briefly expand the observed execution trace/optional Developer insights. Explain: extractor reads, code decides finance, Communicator drafts a note, safety code checks, reviewer critiques, owner decides. Close on “fewer unjustified reminders, with evidence you can inspect.” | Appropriate multi-agent boundaries and a concrete user outcome rather than agent-count theatre. |

**Shortening rule:** omit copying or detailed provider narration before omitting Cedar's claim/proof distinction, the evidence update, preserved history or explicit owner control. Do not start a second unrelated scenario to fill time.

## What Changed feasibility for the signature moment

The exact baseline story is supported by fixtures:

| Saved aspect | First Cedar investigation | After `PK-003-U1` and reinvestigation |
| --- | --- | --- |
| Invoice | INR 90,000 | INR 90,000 |
| Verified paid | INR 30,000 | INR 90,000 |
| Remainder label/value | Recorded/contested INR 60,000 | Verified INR 0 |
| Recommendation | VERIFY_PAYMENT | CLOSE |
| Relevant new source | No CR-T2 ledger record | `PK-003-L2`, verified CR-T2 for INR 60,000 |
| Human lifecycle decision | Case open | Still open until explicit closure |

CR-T2's source payment event is 22 October, 14:00 IST; its arrival is recorded on 23 October. “Newly arrived evidence” is accurate; “payment made during the demo” is not. The comparison must also show each result's own evaluation time. These are expected fixture outcomes, not an execution report from this audit.

## Failure and recovery narration

| Situation | Responsible response |
| --- | --- |
| Provider unavailable / standard-template fallback | Show the actual limitation or recorded fallback. Explain that saved financial advice is separate from drafting; never imply an LLM generated a code template. |
| Morning review or one case still running | Keep sources available; use Check again / saved status. Do not start competing investigations or fabricate completion for the recording. |
| Start/save outcome unknown | Use the existing operation lookup/original-request retry. Do not create a fresh operation ID to “make it work.” |
| Draft invalid or approval unavailable | Show the reason and saved exact version. A short optional backup is an unsupported fee being blocked, but do not add it to the core five-minute path. |
| Comparison unfinished / unavailable | Inspect both saved results through History. Explicitly state comparison convenience is planned or unavailable. |
| Fresh run misses the time target | Inspect a clearly labelled pre-saved fictional run or use an organizer-permitted recording. Disclose the limitation; no fabricated latency, model or trace claims. |

## Submission claims and evidence boundaries

- **Supported differentiator:** source-linked payment-commitment intelligence with deterministic finance, preserved changed advice and exact human control.
- **Supported architecture claim:** two implemented LangGraphs, bounded language-agent roles and deterministic selection/safety/rules; STUB uses offline adapters. The morning supervisor's selection is code, not an LLM planner.
- **Retained engineering evidence:** the [upgrade report](../../reports/multi-agent-upgrade.md) reports offline verification and simulated personas. None of those tests were rerun for this audit.
- **Unproven:** new-agent LIVE quality, general Hinglish production extraction, user time savings, willingness to pay, production readiness and full accessibility conformance.
- **Still pending:** actual five-owner study and formal release acceptance. Do not turn a fictional-test-build publication into a passed study or accepted release.

**Recommended P0 demo improvement:** make the existing decision easy to reach, then add the approved read-only comparison if time permits. The core signature can already be demonstrated manually; the proposal must earn its extra implementation risk.
