# Read-only case journey: Gate III

The real Chrome/loopback API journeys passed on 24 October 2026 using fresh temporary SQLite databases and STUB mode. No investigation was required to inspect the starting evidence.

The browser required explicit creation for an empty copy list, preserved the sole copy across reload, offered selection for multiple retained copies, restored a valid saved selection, recovered from a missing/deleted selection, and preserved the preference on a simulated listing failure. Confirmed deletion did not create a replacement copy. A separate actual backend process was stopped and restarted; the browser selection and saved evidence survived.

All three cases exposed the exact original messages/invoices, availability, designated authority and payment verification labels. Claims remained visibly distinct from verified settlement. The read-only journey checked that each case still had no completed investigation and retained revision zero. Source links opened exact preserved versions; keyboard Escape closed the source dialog and restored focus to its source control.

Original invoice due dates are displayed separately from exclusive next-day overdue boundaries. At 400 px width with 200% text, required dates/status remained visible, the page had no horizontal document overflow, and financial amounts stayed within the workspace. Screenshots were inspected locally after fixing amount/wordmark clipping. This bounded automated check is not a complete human usability evaluation.

Executed checks: `npm.cmd --prefix frontend run test:e2e` (34 combined case/investigation journeys passed), frontend component tests, type checking and production build. Tests exercised a real application API and SQLite; only the deliberate listing-failure test replaced a browser response to simulate unavailability.

AC-01–AC-03 have this implementation evidence. Live extraction, complete release performance trials and five-owner evaluations are separate acceptance work; none is inferred from this read-only journey.
