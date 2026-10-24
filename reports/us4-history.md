# History and lifecycle journey evidence

Gate IV, US4, T073-T083. These are executed deterministic/scripted journeys against real Chrome, local HTTP and fresh temporary SQLite copies. T060 LIVE qualification remains outstanding. No release acceptance is inferred.

Five browser journeys passed:

1. PK-003 initially VERIFY_PAYMENT: exact U1 preview/confirmation invalidated the old result; explicit reinvestigation returned CLOSE with verified zero. Accepting advice retained OPEN. Exact closure confirmation recorded CLOSED; reload and explicit reopening preserved both results and one closure/reopening event each.
2. A wrong closure hash was rejected; repeating the exact committed closure returned its original response once, including GET operation lookup. A closed case could not start investigation.
3. A saved draft/rejection and exact event list survived a real backend process restart. Direct historical draft/result/source inspection retained exact original text, result and source versions.
4. Confirmed selected-copy deletion removed that copy and cleared its browser selection while another retained copy stayed intact.
5. Fixed test-only later conflicting invoice evidence used the production preview/confirmation service. The case stayed CLOSED/review-required with the settled result preserved. Only explicit reopening enabled reinvestigation; the new result was VERIFY_PAYMENT with unknown balance, retaining closure history.

Twenty-two new US4 backend checks plus thirty-four relevant regressions passed. A real concurrent-deletion regression proved history ownership and events now use one SQLite read snapshot. Closure also follows the existing domain exception for an unresolved invoice date when exact verified zero makes that date immaterial; every other settlement conflict remains blocking.

Thirteen history component checks passed, including checked-confirmation identity changes, delayed preview recovery, exact review/source inspection, pending-deletion receipt recovery and copy isolation. The full UI suite passed forty-nine checks; typecheck/build passed.

The production catalogue/live manifest is unchanged. The conflicting invoice extension is fixed test harness data installed only by the isolated test server, not an application import/update feature. Full Gate IV integrated results and final independent review are recorded in phase-iv.md. Gate V fault/performance/human release evaluations remain unexecuted.

Final Gate IV browser suite passed all 54 journeys. Two additional US4 response-after-navigation cases verify confirmed deletion while viewing Findings and while another copy is selected; both pass, bringing US4 to seven browser journeys. Shared outcome coordination passed six new App checks and scoped independent re-review; final full UI suite passed 55 checks serially with typecheck/build.
