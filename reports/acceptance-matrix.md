# Release acceptance evidence matrix

This maps every required identifier to actual test/report artifacts. It is not a blanket pass certificate. Final integrated execution and measurement reports are recorded in runtime-validation.md and phase-v.md; failed and unexecuted evidence retains that status. Every material financial/source/approval/history check requires 100% integrity; a correct action alone is insufficient. T060 now qualifies under the unchanged criteria with 152 correct returned results and one recorded provider availability gap across 153 attempts. The five-owner study remains UNEXECUTED.

Paths named below resolve under backend/tests/{domain,contract,integration}, tests/e2e or reports. No pass is inferred from task checkboxes.

## Functional requirements

| ID | Acceptance references | Evidence | Current qualification |
| --- | --- | --- | --- |
| FR-001 | AC-01, AC-16, AC-27 | case-review.spec.ts; test_cases_api.py; test_catalogue_seed.py | Automated checks PASS in the final suites |
| FR-002 | AC-02, AC-03 | case-review.spec.ts; test_cases_api.py; test_catalogue_seed.py | Automated checks PASS in the final suites |
| FR-003 | AC-04–AC-09, AC-24 | test_information_boundaries.py; test_attempt_transactions.py; deadline-recovery.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| FR-004 | AC-03–AC-08, AC-23 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| FR-005 | AC-04, AC-08, AC-17, AC-23, AC-27 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| FR-006 | AC-06, AC-08, AC-21–AC-23 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| FR-007 | AC-03–AC-09, AC-21–AC-23 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| FR-008 | AC-04–AC-09, AC-21, AC-22 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| FR-009 | AC-05, AC-09, AC-14, AC-23 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| FR-010 | AC-08, AC-18, AC-26 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| FR-011 | AC-10, AC-11 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| FR-012 | AC-10, AC-11, AC-15 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| FR-013 | AC-12, AC-14, AC-16 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| FR-014 | AC-13, AC-17, AC-18, AC-25 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| FR-015 | AC-03, AC-14, AC-20 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| FR-016 | AC-19, AC-20 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| FR-017 | AC-16, AC-18, AC-19, AC-25 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites; LIVE preservation PASS in all ten cycles |
| FR-018 | AC-05, AC-13, AC-17, AC-18, AC-23 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| FR-019 | AC-08, AC-13, AC-17, AC-18 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| FR-020 | AC-21–AC-24, AC-26 | test_information_boundaries.py; test_attempt_transactions.py; deadline-recovery.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| FR-021 | AC-24, AC-25 | test_information_boundaries.py; test_attempt_transactions.py; deadline-recovery.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| FR-022 | AC-09, AC-23, AC-27 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| FR-023 | AC-02, AC-08, AC-12, AC-16 | case-review.spec.ts; test_cases_api.py; test_catalogue_seed.py | Automated checks PASS in the final suites |
| FR-024 | AC-28 | P1 comparison summaries | DEFERRED by approved MVP scope |

## Acceptance criteria

| ID | Evidence | Qualification |
| --- | --- | --- |
| AC-01 | case-review.spec.ts; test_cases_api.py; test_catalogue_seed.py | Automated checks PASS in the final suites |
| AC-02 | case-review.spec.ts; test_cases_api.py; test_catalogue_seed.py | Automated checks PASS in the final suites |
| AC-03 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| AC-04 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-05 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-06 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-07 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-08 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-09 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-10 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| AC-11 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| AC-12 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| AC-13 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| AC-14 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| AC-15 | test_drafts.py; test_reviews_api.py; test_review_transactions.py; draft-review.spec.ts | Automated checks PASS in the final suites |
| AC-16 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| AC-17 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| AC-18 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| AC-19 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| AC-20 | test_case_history.py; test_closed_case_updates.py; test_case_lifecycle_api.py; test_workflow_races.py; history-lifecycle.spec.ts; restart-recovery.spec.ts | Automated checks PASS in the final suites |
| AC-21 | test_information_boundaries.py; test_attempt_transactions.py; deadline-recovery.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-22 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-23 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-24 | test_information_boundaries.py; test_attempt_transactions.py; deadline-recovery.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| AC-25 | test_information_boundaries.py; test_attempt_transactions.py; deadline-recovery.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites |
| AC-26 | test_information_boundaries.py; test_attempt_transactions.py; deadline-recovery.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-27 | test_money.py; test_dates.py; test_reconciliation.py; test_recommendations.py; test_derived_findings.py; investigation.spec.ts; fixture-evaluation.json | Automated checks PASS in the final suites; frozen LIVE batch qualified with one retained availability gap |
| AC-28 | P1 comparison summaries | DEFERRED |

## Registered failure variant groups

All 40 registered variants and their clock/update branches are the canonical 51-entry evaluation manifest. The fixture report names every branch separately, uses independent findings and financial expectations and remains STUB-only. A financial branch pass does not replace its additional workflow/race controls.

| Group | Evidence beyond canonical fixture rows | Qualification |
| --- | --- | --- |
| FV-01 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-02 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-03 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-04 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-05 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-06 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-07 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-08 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-09 | restart-recovery.spec.ts; deadline-recovery.spec.ts; real fault presets | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-10 | test_drafts.py; test_review_transactions.py; draft-review.spec.ts | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-11 | test_drafts.py; test_review_transactions.py; draft-review.spec.ts | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-12 | test_information_boundaries.py; test_investigator.py | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-13 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-14 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-15 | Domain, investigation API and independent findings/financial oracle | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-16 | test_reconciliation.py; test_review_regressions.py; investigation.spec.ts | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-17 | test_workflow_races.py; test_review_transactions.py; draft-review.spec.ts; restart-recovery.spec.ts | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |
| FV-18 | test_dates.py; investigation.spec.ts exact first/second clock boundaries | Scripted/fault checks PASS; fixture-evaluation.json and us5-recovery.md; frozen LIVE batch qualified with one retained availability gap |

## Non-functional requirements and outcomes

| ID | Evidence | Qualification |
| --- | --- | --- |
| NFR-001 | owner-evaluation-protocol.md; owner-observations.csv; owner-evaluation.md | UNEXECUTED; five actual owners required |
| NFR-002 | responsiveness-final.json; live-browser-responsiveness-final.json; deadline-recovery.spec.ts | PASS: HTTP 30/30 fast opens/starts; browser 30/30 fast opens, 29/30 fast starts; all terminal within 60 seconds. Earlier failures retained |
| NFR-003 | preservation.json; restart-recovery.spec.ts; operation-lifecycle.test.tsx | PASS: 10/10 LIVE cycles, exact saved rows and ordered prefixes, zero duplicates; separate unsaved-buffer regression PASS |
| NFR-004 | fixture-evaluation.json; live-final-reconciliation.json | Fixture 51/51 + four probes PASS; frozen LIVE qualified with one availability gap |
| NFR-005 | accessibility.spec.ts; accessibility.md | Three targeted checks PASS, including expanded keyboard journey; five screenshots inspected; final suite 75 PASS |
| NFR-006 | test_information_boundaries.py; test_common_api.py; runtime-validation.md | PASS in full backend/browser suites and executed frozen setup; see runtime-validation.md |
| NFR-007 | reviews/history/operation-lifecycle tests; deadline-recovery.spec.ts | Automated truthful-state checks PASS, including real failures and restart |
| NFR-008 | runtime-validation.md; CLI/configuration tests and fictional disclosures | Local one-owner demonstration only; no production-readiness claim |
| SC-001 | owner-evaluation.md | UNEXECUTED: first journey independent 4/5 within 300 seconds |
| SC-002 | owner-evaluation-protocol.md; owner-observations.csv | UNEXECUTED learning target: median decision-time reduction 30% |
| SC-003 | owner-evaluation.md | UNEXECUTED: source/claim understanding 4/5 |
| SC-004 | fixture-evaluation.json; live-final-reconciliation.json | Fixture 51/51 + four probes PASS; frozen LIVE qualified with one availability gap |
| SC-005 | draft/review/lifecycle/race/info-boundary tests | PASS in exercised domain/API/UI/race scenarios; no sending endpoint; final suites recorded in runtime-validation.md |
| SC-006 | preservation.json; restart-recovery.spec.ts | PASS: 10/10 LIVE leave/reload/reinvestigation/restart cycles; saved rows and immutable prefixes exact, zero duplicates |
| SC-007 | owner-evaluation.md | UNEXECUTED learning target: both clarity/control ratings 4/5 for 4/5 owners |
| SC-008 | responsiveness-final.json; live-browser-responsiveness-final.json; deadline-recovery.spec.ts | PASS: final HTTP/browser timings meet thresholds; real late-callback, retry and unreachable-server fault journeys pass |

## Constitutional gates

| Principle | Evidence and disposition |
| --- | --- |
| I | Written spec/plan/tasks predate implementation; new gates owner-authorized. |
| II | Bounded task groups and task reviews recorded in gate-v-implementation-ledger.md. |
| III | Domain, tool, orchestration, persistence and UI boundaries retained; verification runners reuse real services. |
| IV | One bounded Investigator remains; development review agents add no product agent roles. |
| V | Exact money/time rules stay deterministic; independent numeric oracle and coordinated-offset negative controls pass. |
| VI | Strict API/contracts and version/source/span tests; no arbitrary ingestion endpoints. |
| VII | Source versions, uncertainty and disputed claims retained; findings inventory and boundary tests. |
| VIII | Exact human draft review/closure remains explicit; no transmission routes. |
| IX | Actual commit-boundary restart and replay checks pass; final ten-cycle LIVE measurement recorded separately. |
| X | Baseline, variants, real-time failures and malformed/refusal cases; preserve unsuccessful attempts. |
| XI | Existing approved ADRs retained; test controls stay outside product startup. |
| XII | Evidence/Findings/Timeline/Review/History workspace plus keyboard and personal test guide. |
| XIII | Fictional-only data, synthetic redaction tests, protected local configuration; no real-data claims. |
| XIV | Deadline 26 October 2026 10:00 IST; no P0 waiver inferred to meet it. |
| XV | Gate IV explicitly approved/pushed; Gate V conditional approval cannot become acceptance while required evidence is missing. |
| XVI | Failed/partial LIVE report and unexecuted owner study explicitly retained; no invented participant or provider results. |

## Evidence scope

The complete literal invoice/paid/balance/currency/due oracle is STUB fixture evidence. The frozen LIVE evaluator separately checks raw extracted facts and source provenance, findings, action, balance and review time; it does not directly compare every numeric field in the fixture oracle. Its provider gap is an incomplete attempt, not a correct returned output. Automated accessibility inspection does not establish representative-owner usability. Technical evidence does not populate the five blank owner observations or validate willingness to pay.
