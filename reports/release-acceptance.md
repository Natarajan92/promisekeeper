# Release acceptance decision

Current decision: **NOT ACCEPTED / formal Gate V incomplete**. Engineering implementation and technical checks are complete, but the five-owner study required by T095 / NFR-001 / SC-001 / SC-003 is UNEXECUTED. The project owner confirmed five live users are unavailable. SC-002 time improvement and SC-007 clarity/control remain unmeasured; no times, correctness scores, ratings, willingness to pay or purchase commitment are invented.

The owner conditionally authorized approving and publishing Gate V after completion. That condition does not supply the missing study. Gate III and Gate IV are separately approved and pushed as `078c4db` and `0454551`. At 2026-10-24T15:39:52.044Z the owner selected: "Push fictional test build; keep formal acceptance pending". This explicitly authorizes publishing the completed engineering work as a **fictional test build**, retaining the acceptance block and the unexecuted study. Publication is not a completed-release, human-usability or production-readiness claim. No study waiver is inferred.

## Technical evidence available for review

- Backend: 748 passed and one intentional LIVE skip in the full run; 29 focused runner tests passed after the subsequent measurement-only SQLite cleanup correction, including two new cleanup regressions.
- Frontend: 57 unit/component tests, typecheck and production build passed. The complete Chrome/API/SQLite suite passed 75 tests with one intentional LIVE skip.
- Fixtures: all 51 canonical branches and four failure presets passed independent financial/findings checks.
- Frozen LIVE qualification: 152 correct returned results from 153 attempts, one retained provider gap and zero unexecuted. Unchanged criteria return PASS_WITH_AVAILABILITY_GAPS.
- Timing: HTTP 30/30 fast opens and acknowledgements; browser 30/30 fast opens and 29/30 fast acknowledgements. All terminal outcomes met 60 seconds; the browser's slowest completed result was 10.414 seconds. The one 3.237-second start remains recorded.
- Preservation: all ten LIVE cycles passed exact saved-row/history comparisons with zero duplicates. Actual process-death, late-callback, race and unsaved-buffer regressions also passed.
- Independent whole-change and scoped reviews cleared all Critical/Important findings. Earlier failed and partial reports remain preserved.

See `acceptance-matrix.md`, `runtime-validation.md`, `phase-v.md`, `fixture-evaluation.json`, `live-evaluation-gate-v.json`, `responsiveness-final.json`, `live-browser-responsiveness-final.json` and `preservation.json`. The complete financial oracle is STUB evidence; the frozen LIVE evaluator's exact scope is disclosed in the matrix and summary. Deadline 26 October 2026, 10:00 IST does not waive required evidence or human control.

## Personal testing and the missing observations

The [hands-on guide](../docs/user-testing/README.md), [14 test cases](../docs/user-testing/test-cases.md), [sample data](../docs/user-testing/sample-data.json) and [blank results sheet](../docs/user-testing/results-template.csv) are ready. The walkthrough uses STUB/REFERENCE and needs no API key. The [business-owner explanation](../docs/user-testing/small-business-pitch.md) gives a short pitch, five-minute demonstration and honest answers about the prototype's limits.

A personal test can collect useful feedback before acceptance. It does not replace five representative owners. Use `owner-evaluation-protocol.md` and the five blank rows in `owner-observations.csv` when participants become available, then reassess the affected requirements and obtain the owner release decision. Real-data ingestion, authentication, customer delivery and production deployment remain outside this fictional build.
