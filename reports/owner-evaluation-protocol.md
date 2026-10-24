# Five-owner evaluation protocol

Status: prepared; no participants recruited or observations collected by the implementation agent. The project owner facilitates five representative small-agency owners. Use fictional records only and participant labels P01-P05; no names, customer data or credentials are needed in the report.

## Preparation

Use the setup in [the user testing guide](../docs/user-testing/README.md), a fresh REFERENCE Baseline copy per owner and the same declared mode, machine and browser. Record STUB or LIVE explicitly. STUB can assess this scripted workflow's usability, not LIVE quality or latency. For each manual condition provide a separate copy of [the manual input packet](../docs/user-testing/manual-review-packet.md), without the answer key. Use equivalent canonical records for the assisted condition. Keep answer keys hidden until both conditions finish.

Do not train participants on the solution or walk them through controls. Say: “Review Northstar's records, decide what to do next and why, check the original evidence, and review the suggested message. You decide whether to approve or reject the saved draft. Nothing is sent.” Answer setup questions before timing; record any help during the task as an intervention.

Use the blank [observation CSV](owner-observations.csv). Rotated order: P01 manual then assisted; P02 assisted then manual; P03 manual then assisted; P04 assisted then manual; P05 manual then assisted. The records are equivalent fictional copies, so recall remains possible; record this limitation and the order rather than claiming a controlled causal study.

## Observe each owner

1. **Manual decision:** Start a stopwatch when the owner receives Northstar's packet. Stop when they state a defensible next action, amount, reason and supporting source. Record elapsed seconds and correctness before giving feedback.
2. **Assisted decision and first journey:** Start timing when they start selecting Northstar's case in the ready app. Record a split when they state a defensible next-action decision, then continue until investigation, original-source inspection and an explicit saved draft decision are complete. Record both elapsed times, correctness and every facilitator intervention. A finish with intervention is not independent success.
3. **Disputed-payment understanding:** Ask the owner to investigate Cedar without the staged settlement. Ask: “What did the customer say? What payment is actually verified? Which original source supports the next step? What remains unresolved?” Record separate scores for claim-versus-verification, supporting source and unresolved question. Do not count repeating VERIFY_PAYMENT alone as understanding.
4. **Clarity and control:** After both scenarios, ask two independent 1-5 ratings: “How clear was the explanation?” and “How much control did you have over the next step?” Record the reason, especially for ratings below 4. Also record confusion, unsupported assumptions and unwanted actions.
5. Save the fictional copy ID, mode, timing method and environment. Preserve incomplete attempts and negative observations. Missing values stay blank/UNEXECUTED, never zero. Do not replace a struggling participant with an easier one without reporting the change.

## Scoring

Use [the test answer key](../docs/user-testing/test-cases.md) after the tasks. Northstar requires FOLLOW_UP for verified80,000 remainder, supported by invoice 120,000, verified 40,000 and the expired80,000 promise. Cedar requires VERIFY_PAYMENT because CR-T2 is only claimed, while only 30,000 is verified against 90,000. The unresolved question is whether the claimed60,000 payment settled and belongs to this invoice.

- SC-001/NFR-001: at least 4/5 independent first assisted journeys finish in at most300seconds, including source and draft decision. Report correctness as well as speed.
- SC-003: at least 4/5 correctly distinguish claim/verified payment, cite the supporting original source and identify the unresolved question.
- SC-002 learning target: report the five raw paired timings and compute `100 * (median_manual_seconds - median_assisted_seconds) / median_manual_seconds`. Target reduction in median decision time is at least 30%. Also report the median of individual paired percentage improvements as a secondary measure; do not silently switch formulas or remove unsuccessful pairs. Undefined/incomplete pairs prevent a complete result. Report recall/order limitations.
- SC-007 learning target: at least 4/5 rate both clarity and control at least 4/5. Preserve reasons for lower scores.

T095 remains unexecuted until the five actual records exist and are checked. Unexecuted required P0 usability evidence blocks acceptance; learning-target misses are disclosed and do not replace safety or P0 checks. One owner's personal walkthrough does not count as five observations. No invitation, recruitment or external message is sent by this protocol.
