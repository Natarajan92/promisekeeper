# UX Phase 1 implementation

The owner requested implementation of the five recommendations from the simulated persona review. This is a new UX iteration, distinct from original Gate I. Simulated perspectives are design hypotheses; no actual owner observations, ratings or formal acceptance results have been added.

## Implemented behavior

- Case cards show reconciled balances, conservatively labelled recorded/verified/unknown remainders, current saved recommendations and next review times. Changed evidence, expired waiting advice and running investigations suppress current recommendations. REAL-time overview review dates trigger a refresh even when another case is selected.
- A three-step case journey links evidence, recommendation and the action appropriate to the result. Previous results are labelled previous. Follow-up/neutral-draft cases link to message review; internal verification links to payment evidence; waiting does not imply a reminder; settlement still requires explicit closure.
- Friendly action/reason labels and IST formatting replace internal action codes and embedded UTC instants in the main explanation. Exact source versions, saved results, draft text and hashes remain unchanged. Technical identifiers remain inspectable.
- Current recommendation decisions and eligible settlement actions appear with the financial summary in Findings. History retains its existing historical decision and administration workflows. Current decisions are blocked beside stale Findings without changing backend historical-recording rules.
- Copy approved message writes only the current exact saved approved text. Unsaved wording, pending requests, changed approval context, invalid validation, a different draft head or a running investigation block copying. Clipboard failure exposes read-only exact text for manual copying. Completion explicitly states that nothing has been sent. Windows clipboard reads normalize native line endings; application tests check the exact string supplied to the clipboard API.
- Sample setup/mode wording explains scripted answers and the fixed demo date. Narrow case cards scroll within the overview rather than stacking every case above the selected workspace.

## Scope and verification

No new dependencies, real-data intake, authentication, messaging, model/prompt changes or LIVE provider calls. Formal Gate V acceptance and the unexecuted five-owner study remain unchanged. The owner subsequently authorized committing, pushing and merging this work into `main` on 24 October 2026.

Baseline: 57 frontend component checks and 14 case API checks passed. New regression checks were observed failing before implementation, including summary freshness/unknown balances, current decisions, cross-case wait-date refresh, and exact approved-copy eligibility. Existing action-title assertions were updated to the intentional friendly labels while API action assertions remain unchanged.

Independent review found no Critical issues, one Important clipboard freshness issue and one Minor overview-boundary issue. Both are fixed with regression coverage. Clipboard handoff now subscribes to unresolved same-case investigation starts and retains a persisted receipt revision fence until the displayed case reaches that revision, including after a failed refresh or component remount. Already-expired overview advice is suppressed while one bounded refresh is requested. A timeout-message race discovered by the full browser suite is fixed: a late poll error cannot replace the sixty-second unknown-outcome notice.

## Implementation verification

| Check | Actual outcome |
| --- | --- |
| Complete backend suite, serial rerun | 753 passed, one intentional opt-in LIVE skip; existing Starlette/httpx deprecation warning |
| Complete component suite | 81 passed |
| TypeScript and production build | Passed; no new dependencies |
| Final complete offline Chrome attempt | 78 passed, one intentional LIVE skip, two unsuccessful checks described below |
| Fresh isolated rechecks on unchanged final code | Both unsuccessful checks passed: late-provider/real-deadline preservation and pending-save navigation |
| Distinct offline browser coverage | All 80 offline checks have passing executions across the final complete attempt and the isolated rechecks; this is not a claim of one uninterrupted green run |
| Responsive and keyboard evidence | Desktop and 400px/200% text screenshots inspected; keyboard/focus and non-color journeys passed |
| Independent review | No Critical findings; the Important clipboard freshness issue and Minor overview-boundary issue are fixed with regression coverage |
| Git hygiene | Changes remain local and uncommitted; accounting and instruction files remain excluded |

The first concurrent full run had 752 backend passes, one intentional LIVE skip and a system thread-allocation failure in an existing race test. A component attempt separately encountered system memory exhaustion. The first complete browser run had 74 passes, one intentional LIVE skip, three assertions requiring updates for the deliberate display changes, and the timeout-message race. Those runs remain failed, not regraded.

In the final complete Chrome attempt, a late-provider test worker stopped progressing after its isolated server had exited; the unresponsive test worker was explicitly terminated to resume the remaining checks. Another test's investigation setup remained RUNNING beyond its existing ten-second helper deadline. Both checks passed in a fresh bounded isolated run without code, timing-criteria or expectation changes. The interruption and setup timeout remain preserved in the original run. The isolated late-provider test took 59.6 seconds end-to-end; its original internal timing assertions passed.

The initial focused browser run also exposed native Windows clipboard line-ending normalization and the distinction between historical-recording eligibility and the new current-decision surface. Both were addressed without changing saved records or financial rules. These automated checks do not replace the actual five-owner study or grant formal release acceptance.

## Publication verification, 24 October 2026

The owner explicitly requested pushing the code to GitHub and merging it into `main`. Fresh verification of the publication tree produced:

| Check | Actual outcome |
| --- | --- |
| Complete backend suite | 753 passed, one intentional opt-in LIVE skip; existing Starlette/httpx deprecation warning |
| Production build and TypeScript | Passed |
| Complete component suite, serial execution after backend completion | 81 passed |
| Complete offline Chrome attempt | 79 passed, one intentional LIVE skip, one isolated-backend startup timeout |
| Isolated restart-check recheck | Passed on unchanged application/test code with the original ten-second startup limit |
| Distinct offline browser coverage | All 80 checks have passing executions across the complete attempt and isolated recheck; the complete attempt remains a failed run |

The initial component attempt ran alongside the backend suite and timed out finding the initial case heading: 80 passed and one failed. The complete serial rerun passed without application, test or timing changes. The Chrome failure occurred at initial isolated-server readiness, before the process-kill scenario began. Its unchanged-code isolated recheck passed the complete restart and preservation journey in 16.5 seconds. These startup/timing failures remain recorded rather than being regraded. Publication retains the fictional-test-build designation and pending five-owner study; it does not establish formal Gate V or Release 0.1 acceptance.
