# Multi-page business UX and course-demo pack Implementation Plan

**Recovery status, 26 October 2026:** Tasks 1?9 are implemented and locally verified. Final backend 1,382 passed/one LIVE skip; frontend 226 passed; TypeScript/build passed; full serial Chrome 95 passed/one LIVE skip. See [completion report](../../../reports/multi-page-ux.md) for preserved failures, the browser-test-only rerun ruling, minor limitations and screenshots. The original session already consumed the single LIVE rehearsal before final offline verification; its timing deviation and Meera difference are reported truthfully, with no repeat or qualification claim. Work remains uncommitted/unpushed.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Turn the single-page PromiseKeeper UI into five business-friendly pages (style B), add a regenerable course-demo upload pack, fix end-to-end upload/parsing bugs in frontend and backend, and finish with every regression suite green plus one LIVE rehearsal.

**Architecture:** Hash-routed React shell (`#/dashboard`, `#/upload`, `#/cases`, `#/cases/<id>`, `#/assistant`, `#/approvals`). A shared workspace store (case list + all CaseViews + health + latest morning review) is owned by the shell and read by every page. Existing feature components (IntakePanel, MorningReview, DraftReview, OwnerDecisions, FindingsView, WhatChanged, AgentTrace…) are reused and restyled, not rewritten. Backend changes are limited to parser bugs and a pack generator.

**Tech Stack:** React 19, TypeScript, Vite, Vitest + Testing Library, Playwright (Chrome), FastAPI/Python 3.12, pytest.

**Spec:** `docs/superpowers/specs/2026-10-26-multi-page-ux-design.md` (read it fully; the "Decisions from the builder check" section is binding).

## Global Constraints

- **No git commits, pushes or PRs.** The tree already holds uncommitted 005 work. Never revert, reformat or delete files you did not create. Never run `git add`, `git stash`, `git checkout -- …` or `git clean`.
- Never open `.env` or print credentials. Agents never run LIVE (only the orchestrator does, in Task 9).
- Use the README environment from the repo root (PowerShell). Set `UV_CACHE_DIR`, `UV_PYTHON_INSTALL_DIR`, `npm_config_cache` and `PLAYWRIGHT_BROWSERS_PATH` under `.runtime\`.
- Run backend tests with `uv run --project backend pytest -p no:cacheprovider --basetemp=.runtime/pytest-<yourname>`. The default `.runtime/pytest-temp` is permission-locked; leave it alone.
- **Browser-test lock.** `npm run build` and `npm run test:e2e` share `frontend/dist` and port 19000, so run them only while holding the lock:
  - acquire with `New-Item -ItemType Directory .runtime\e2e.lock` (it fails if the lock exists; then wait and retry);
  - release with `Remove-Item .runtime\e2e.lock`, always, even when the run fails.
  - Run focused specs only (`npm.cmd --prefix frontend run test:e2e -- tests/e2e/<file>.spec.ts` resolves from `frontend`, so pass `../tests/e2e/<file>.spec.ts`).
  - `typecheck` and `test:unit` need no lock.
- **Visible text = accessible name.** Keep every existing control's accessible name unless this plan names a rename. No renames are planned. In particular keep: "Investigate case", "Start morning review", "Approve exact saved version", "Reject exact saved version", "Save unapproved version", "Copy approved message", "Accept recommendation", "Reject recommendation", "Review case closure", "Preview file", "Show all N cases", "View recommendation", "Review suggested message", "Inspect payment evidence".
- **Test-edit rule (from spec).** Tests may change only how they reach a feature (route/tab/step) and deliberately changed formatting (`INR ` → `₹` in UI money). Layout assertions may change only if the same property is re-asserted. Never delete assertions, raise timeouts or weaken checks. Keep a running list in `.runtime/ux-test-changes-<yourname>.md` (file, test, what changed, why).
- **Money.** `money()` renders INR as `₹` + Indian grouping + 2 decimals (e.g. `₹2,35,000.75`), and other currencies as `CODE 1,234.00`. `null` gives "Unknown". Backend text is untouched.
- **Style tokens (style B), defined once in `frontend/src/theme.css`:**

  | Token | Value |
  |---|---|
  | `--indigo` | `#4a2fe0` |
  | `--violet` | `#7b4cf6` |
  | `--coral` | `#ff7a59` |
  | `--bg` | `#f4f5fb` |
  | `--card` | `#fff` |
  | `--ink` | `#151a33` |
  | `--muted` | `#5a607a` |
  | `--line` | `#e6e8f2` |
  | `--red` | `#b23a17` / bg `#ffe4dc` |
  | `--amber` | `#8a5306` / bg `#fff3cf` |
  | `--green` | `#1e6a3b` / bg `#dcf5e5` |
  | `--lav` | `#ece9ff` |

  - Radius: cards 18px, pills 999px.
  - Font: `"Plus Jakarta Sans", "Segoe UI", system-ui, sans-serif`, self-hosting optional, no external CSS fetch required.
  - Laptop target 1440×900. No horizontal overflow at 390px / 200% text.
  - Focus outline `3px solid var(--indigo)`.
- One `<h1>` per page. Skip link targets `#main`. Footer "Fictional demonstration. No customer messages are sent." remains.

## Review Focus

1. **Refresh/back on a deep link** (`#/cases/<id>` for a case of a deleted/other workspace): show "This case isn't in the current workspace" with a link to Cases, never a blank page or a crash. Test in Task 3 (router + CasePage not-found).
2. **Store staleness after a decision made on Approvals**: approving there must refresh the Approvals badge, Dashboard tile and case page without reload. Test in Task 6 (queue recomputes after `refresh`).
3. **Unknown or mixed money on the Dashboard**: UNKNOWN balance or non-INR open cases are never summed into "Still to collect" and never shown as ₹0. Test in Task 4 (`collectTotals`).
4. **Upload step state for a demonstration-copy workspace**: when the selected workspace is a demo copy, Upload must start a new imported workspace, not try to import into the copy. Test in Task 5 (stepper state with `importedWorkspace=false`).
5. **Real emails with courtesy text/signatures** must parse; hedged or conditional closings must still be refused. Test in Task 1.

---

### Task 1: Backend — accept courtesy lines and short signatures in customer messages (baseline bug)

Baseline `tests/e2e/intake.spec.ts` fails because `docs/demo-import/customer-promise.eml` ("Thank you for your patience." + "Econ accounts") is refused by `SAFE_PROSE` in `backend/src/promisekeeper/domain/document_rules.py:17`, applied at `domain/document_extraction.py:114`.

**Files:**
- Modify: `backend/src/promisekeeper/domain/document_rules.py`
- Modify: `backend/src/promisekeeper/domain/document_extraction.py:113-115`
- Test: `backend/tests/domain/test_uploaded_documents.py` (append)

**Interfaces:**
- Produces: `SAFE_PROSE` (extended regex) and `is_signature_block(lines: list[str]) -> bool` in `document_rules.py`.

- [x] **Step 1: Write failing tests** `test_courtesy_and_signature_lines_do_not_block_a_direct_promise`. Build an email like `customer-promise.eml`, and assert that each body below yields exactly one COMMITMENT with amount `40000`:
  - "…by 30 October 2026.\nThank you for your patience.\n\nEcon accounts"
  - with "Warm regards,\nMeera Shah\nMeera Textiles"
  - with "Namaste," as the first line

  Then write `test_hedged_closings_are_still_refused` (parametrize), with each body raising `ValueError`:
  - closing "Thanks, subject to approval."
  - closing "Regards, will confirm later"
  - signature "Maybe next week"
  - a 6-word trailing line
  - a trailing line containing digits ("Ref 2")
  - a courtesy line *before* the promise containing "if"
- [x] **Step 2: Run** `uv run --project backend pytest backend/tests/domain/test_uploaded_documents.py -k "courtesy or hedged" -p no:cacheprovider --basetemp=.runtime/pytest-b1`. Expected: the first test FAILS, the second passes.
- [x] **Step 3: Implement.**
  - Extend `SAFE_PROSE` with these bounded courtesy forms:
    - thanks/thank you, optionally followed by `for your (patience|understanding|support|time|cooperation)`;
    - (warm|kind|best) regards, sincerely, namaste/hello/hi/dear `<≤3 words>` with optional comma;
    - "hope you are (doing )?well".
  - Add `is_signature_block`: true when the lines are the trailing lines after the last candidate/courtesy line, there are at most 3 of them, each has 1–5 tokens of letters/`&`/`.`/`'`/`-`, none contains a digit, and none matches `QUALIFIED`, `REPORTED`, `payment_language`, or the denylist `\b(?:maybe|later|confirm|only|except|partial|part|half|dispute|wrong|issue|problem|sorry|delay|delayed|cancel|hold|soon|next|week|month)\b`.
  - At line 114, a non-candidate line is allowed if it matches `SAFE_PROSE` or belongs to that trailing signature block.
- [x] **Step 4: Run** the same command, then `backend/tests/domain backend/tests/integration/test_eval_gap_fixes.py backend/tests/integration/test_synthetic_pack.py backend/tests/evaluations`. Expected: all pass. The system-eval harness expectations are unchanged; if a held-out case flips, stop and report it rather than editing the oracle.
- [x] **Step 5: Verify the browser baseline.** With the lock held, run build and then `../tests/e2e/intake.spec.ts`. Expected: pass.

### Task 2: Backend — regenerable course-demo pack, oracle test and presenter script

**Files:**
- Create: `backend/src/promisekeeper/fixtures/course_demo_pack.py`
- Create: `backend/tests/integration/test_course_demo_pack.py`
- Create (generated): `docs/demo-import/course-demo/*`, including `START-HERE.md` and `EXPECTED-RESULTS.json`

**Interfaces:**
- Consumes: Task 1's courtesy support (messages may include a closing and signature).
- Produces: `generate_course_demo(output: Path, as_of: date) -> dict` (the manifest: `files`, `customers`, `documents`, `allocations`, `expected`) and a CLI `python -m promisekeeper.fixtures.course_demo_pack --as-of YYYY-MM-DD --out DIR` (default today in IST, default out `docs/demo-import/course-demo`). It writes only named files and never deletes.

Content: six fictional Indian MSMEs, one invoice each, in INR, with Indian names/addresses. Use the CSV field sets and bank-profile columns from `synthetic_pack.py` and `docs/demo-import/README.md`. With D = as_of:

| Customer (suggested) | Invoice | Story | Expected after morning check |
|---|---|---|---|
| Meera Textiles | ₹60,000, issued D-40, due D-16 | ₹12,000 receipt D-23 (owner allocates); Hinglish WhatsApp from D-12 "hum ₹48000 D-8 ko payment kar denge" (FULL_PROMISE Hinglish form) | FOLLOW_UP, balance ₹48,000 |
| Arun Traders | ₹32,500, due D-10 | customer email "we paid INR 32500 on D-3. UTR: ARUN-T9." with no matching receipt | VERIFY_PAYMENT; finale: `payments-later.csv` ARUN-T9 → allocate → re-check → CLOSE, ₹0 |
| Sunrise Foods | ₹40,000, due D-5 | full receipt D-3, allocated | CLOSE, ₹0 |
| Kaveri Packaging | ₹75,000, due D-2 | email promise "we will pay INR 75000 by D+7", with courtesy and signature | WAIT, review at the promise boundary |
| Lotus Electricals | ₹80,000, due D-9 | no messages, no payment | FOLLOW_UP, ₹80,000 |
| Patel Hardware | ₹25,000, due D-12 | a bank credit "NEFT PATEL HW" without invoice ref (the owner matches it by hint) for ₹10,000 partial; plus a deliberately refused conditional WhatsApp "we will pay if the goods are replaced" (expected preview refusal; the presenter shows it, does not import it) | FOLLOW_UP, balance ₹15,000 |

Files:
- `01-customers.csv`, `02-invoices.csv`
- `03-bank-statement.csv` (bank profile `Date,Description,Credit,Debit,Reference,Balance` including one debit row that is skipped)
- `04-messages/…` (one file per message: `.eml` for email, `.txt` with `Sender:`/`Sent:` for WhatsApp)
- `05-later/payments-later.csv`
- `06-refused/patel-conditional.txt`
- `START-HERE.md`, `EXPECTED-RESULTS.json`

The builder may adjust the amounts or customers if a parser limit requires it. The table's *outcomes* (≥1 FOLLOW_UP, WAIT, VERIFY_PAYMENT, CLOSE, a partial, a refusal and the finale) are mandatory.

- [x] **Step 1: Write failing tests.**
  - `test_course_demo_generation_is_deterministic_and_relative`: same bytes for the same as_of; all issue dates < as_of; the WAIT promise > as_of; the FOLLOW_UP promise < as_of.
  - `test_course_demo_journey_produces_every_outcome`, for both as_of = `date(2026,10,26)` and today (IST): through `support.intake` helpers in a STUB app, commit customers → invoices → bank statement → each message (customer role) → the manifest allocations → coverage → start the morning review and poll until COMPLETE. Then assert, from `/demonstrations/{did}/cases`, each invoice's `recommended_action` and `balance` equal `EXPECTED-RESULTS.json`. Assert `06-refused` previews with an error and saves nothing.
  - `test_course_demo_finale_closes_after_later_statement`: import `payments-later.csv`, allocate ARUN-T9, reconfirm coverage, investigate Arun again; assert action CLOSE, balance 0, and that the earlier result is retained as previous (`latest_completed_result` vs history).
  - Reuse `setup`/`coverage`/`run` patterns from `backend/tests/integration/test_synthetic_pack.py`.
- [x] **Step 2: Run** them. They fail because the module is missing.
- [x] **Step 3: Implement the generator.**
  - Follow `synthetic_pack.py` conventions.
  - `START-HERE.md` contains:
    - the regenerate command first;
    - clean-up: workspace switcher → delete current workspace, then Upload step 1;
    - per-step file + kind + target invoice + sender role;
    - exact allocations (receipt → invoice → amount);
    - which page to show for each talking point (Dashboard, Case page story, Assistant page for the multi-agent architecture, Approvals approve + copy);
    - the finale;
    - the truthful STUB-verified / LIVE-unverified note from the spec;
    - the note that drafts say "INR …" while the UI shows ₹.
- [x] **Step 4: Run** the tests. They pass. Then generate the checked-in copy, `uv run --project backend python -m promisekeeper.fixtures.course_demo_pack --as-of <today IST>`.
- [x] **Step 5: Fix product bugs this surfaces** (backend or frontend) with a failing regression test first. Record each in `.runtime/ux-bugs-b1.md`.

### Task 3: Frontend foundation — router, theme, shell, workspace store, money

**Files:**
- Create: `frontend/src/routing.ts`, `frontend/src/theme.css`, `frontend/src/shell/AppShell.tsx`, `frontend/src/shell/WorkspaceSwitcher.tsx`, `frontend/src/store/useWorkspace.ts`
- Create placeholder pages: `frontend/src/pages/{DashboardPage,UploadPage,CasesPage,CasePage,AssistantPage,ApprovalsPage}.tsx`, each exporting `function XPage(props: PageProps)`
- Modify: `frontend/src/App.tsx` (becomes shell + route switch; move case-page state/effects into `CasePage`), `frontend/src/components/format.ts` (`money`), `frontend/src/main.tsx` (import theme.css), `frontend/src/components/StatusBanner.tsx` (restyle only)
- Test: `frontend/tests/routing.test.tsx`, `frontend/tests/workspaceStore.test.tsx`, `frontend/tests/presentation.test.tsx` (money)

**Interfaces (Produces):**
```ts
// routing.ts
export type Route = {page:'dashboard'}|{page:'upload';step?:number}|{page:'cases'}|{page:'case';caseId:string;section?:'overview'|'evidence'|'history'|'compare'}|{page:'assistant';caseId?:string}|{page:'approvals';itemId?:string};
export function parseRoute(hash:string):Route;          // unknown → dashboard
export function routeHref(route:Route):string;          // '#/cases/abc?section=evidence'
export function useRoute():[Route,(r:Route)=>void];      // hashchange-driven; navigate pushes history
// store/useWorkspace.ts
export interface CaseEntry {summary:CaseSummary; view:CaseView|null; error:string|null}
export interface Workspace {
  api:ApiClient; health:Health|null; catalogue:Catalogue|null;
  copies:Demonstration[]; selected:string|null; imported:boolean; discovering:boolean; discoveryError:string;
  list:CaseListResponse|null; evaluationAt:string|undefined; plan:Record<string,number>;
  cases:CaseEntry[]; detailsLoading:boolean; refreshTick:number;
  select(id:string|null):void; discover(created?:string):Promise<void>; refresh():void; setPlan(p:Record<string,number>):void;
}
export function useWorkspace(api:ApiClient):Workspace;   // owns everything App.tsx did for discovery, list, review-boundary timers, subscribeCommitted, deletion
export interface PageProps {ws:Workspace; route:Route; navigate:(r:Route)=>void}
```

- [x] **Step 1: Write failing tests.**
  - `parseRoute`: `''` → dashboard; `'#/cases/x%2Fy'` → `{page:'case',caseId:'x/y'}`; `'#/upload?step=3'` → step 3; `'#/nope'` → dashboard. `routeHref(parseRoute(h))` round-trips.
  - `useWorkspace`: with a fake ApiClient (pattern as in `frontend/tests/cases.test.tsx`), loads the list, then every CaseView. A failing `case()` gives that entry `error` set and the others are still loaded. `refresh()` refetches. A deletion commit via `subscribeCommitted` clears the selection.
  - `money({currency:'INR',minor_units:'23500075'})==='₹2,35,000.75'`; USD stays `USD 1,234.00`.
- [x] **Step 2: Run** `npm.cmd --prefix frontend run test:unit -- routing workspaceStore presentation`. Fail.
- [x] **Step 3: Implement.**
  - Move the App.tsx discovery/list/timer/subscription logic into `useWorkspace` unchanged in behaviour; keep `selectionKey` usage.
  - The AppShell renders:
    - the skip link and top bar (logo, pill tabs with `aria-current="page"`, Cases badge = open count, Approvals badge = Task 6 count or none while loading);
    - the WorkspaceSwitcher, which reuses `DemonstrationPicker` for choose/create, adds "New upload workspace" → `#/upload`, and offers delete through the existing deletion confirmation from `OwnerDecisions`, moved into a small reusable `DeleteWorkspace` component with identical labels;
    - the StatusBanner, then `<main id="main">`, then the footer.
  - The route switch renders the pages. CasePage receives the moved case logic (view fetch, source viewer, history paging, focus, comparison request, tabs) — all logic currently in App.tsx lines 28-131 that is case-scoped.
- [x] **Step 4: Run** unit tests, typecheck and build. All pass, except old unit tests that are expected to need navigation updates; list those and fix them per the test-edit rule (e.g. render `App`, then navigate to `#/cases/<id>`).
- [x] **Step 5:** With the lock, run e2e `ux-flow`, `case-review`, `accessibility`. Update their navigation (`page.goto('/#/cases')` or a tab click) until they pass.

### Task 4: Dashboard, Cases list and Case page

**Files:**
- Modify: `frontend/src/pages/DashboardPage.tsx`, `CasesPage.tsx`, `CasePage.tsx`
- Create: `frontend/src/dashboard/totals.ts`, `frontend/src/cases/CaseStory.tsx`, `frontend/src/components/Avatar.tsx`, `frontend/src/components/Chip.tsx`, `frontend/src/pages/pages.css`
- Modify (restyle/relocate only): `cases/CaseList.tsx`, `cases/CaseJourney.tsx`, `investigations/FindingsView.tsx`, `agents/MorningReview.tsx`
- Test: `frontend/tests/dashboard.test.tsx`, `frontend/tests/casePage.test.tsx`

**Interfaces:**
- Consumes: `Workspace`, `PageProps`, `routeHref`, the `ApprovalItem` count from Task 6 (`useApprovalQueue(ws).items.length`). Until Task 6 lands, use a stub returning `null`.
- Produces: `collectTotals(cases:CaseSummary[]):{inrMinor:bigint; recordedMinor:bigint; unknownCount:number; otherCurrencyCount:number}` (open cases only); `<Avatar name/>` (initials, deterministic colour); `<Chip tone="red|amber|green|indigo">`.

- [x] **Step 1: Write failing tests.**
  - `collectTotals`: VERIFIED 80,000 + RECORDED 12,000 gives inr 92,000 and recorded 12,000. UNKNOWN increments `unknownCount`. USD increments `otherCurrencyCount`. CLOSED is ignored.
  - Dashboard renders "₹92,000.00", "₹12,000.00 of this is recorded but not yet verified", "plus 1 with unknown balance".
  - An empty workspace shows "Start by uploading your records" with a link to `#/upload`.
  - The Follow up today rows link to `#/cases/<id>`.
  - CasePage with an unknown id shows "This case isn't in the current workspace".
- [x] **Step 2: Run.** Fail.
- [x] **Step 3: Implement per spec §1 and §3.**
  - The Dashboard hero hosts the existing `MorningReview` (its button keeps "Start morning review"). Its "Open case" goes to `#/cases/<id>?section=overview`.
  - The CasePage Overview combines:
    - left: CaseStory (from `view.evidence` + `current_result.timeline`; each message shows its quote, with "View original" opening the existing SourceViewer) and Key facts;
    - right: the suggestion card (FindingsView content restyled, with `OwnerDecisions contextual` + `FeedbackButtons`), the DraftReview card, the InvestigationControls and the CaseJourney.
  - Tabs: Evidence (CaseEvidence + Timeline), History (OwnerDecisions + ScenarioUpdate + CaseHistory), Compare (WhatChanged), each a `section` route value.
  - Keep "View recommendation" etc. working by mapping the old tab names `evidence|findings|timeline|review|history` onto the new sections.
- [x] **Step 4: Run** unit tests, typecheck and build. Then, with the lock, run e2e `ux-flow ux-completion case-review draft-review investigation history-lifecycle comparison deadline-recovery restart-recovery status-reads personas accessibility` and migrate navigation until green.
- [x] **Step 5: Screenshot** Dashboard and Case page at 1440×900 to `.runtime/ux-shots/`, and inspect them.

### Task 5: Upload page with six-step stepper

**Files:**
- Modify: `frontend/src/pages/UploadPage.tsx`, `frontend/src/intake/IntakePanel.tsx`
- Create: `frontend/src/intake/stepper.ts`, `frontend/src/intake/Stepper.tsx`, `frontend/src/intake/upload.css`
- Test: `frontend/tests/stepper.test.tsx`; update `frontend/tests/intake.test.tsx`

**Interfaces:**
- Consumes: `Workspace` (`selected`, `imported`, `refresh`, `select`, `discover`), the Route `{page:'upload';step}`.
- Produces: `type UploadStep = 1|2|3|4|5|6`; `stepStates(overview:IntakeOverview|null, cases:CaseSummary[], latestReviewDone:boolean):{step:UploadStep;label:string;state:'done'|'current'|'todo'|'attention';summary:string}[]`; `IntakePanel` gains the optional prop `step?: UploadStep`. When it is undefined, it renders exactly as today.

Step → panel mapping:
- Steps 1–4 show "Upload and preview", with the kind preset to customers / invoices / payments / (customer_email | whatsapp | remittance_email). The kind select stays available, labelled as today.
- Step 5 shows "Review receipts and invoice allocations", plus an optional "Existing allocations" upload.
- Step 6 shows "Review coverage and open a case", plus the `MorningReview` start control and the link to the Dashboard.

Labels:
- Step names: "Customers", "Invoices", "Bank receipts", "Customer messages", "Match payments", "Confirm & check".
- Header: "Bring in your records".
- Sample-files line: "Demo files: docs/demo-import/course-demo (see START-HERE.md)".

- [x] **Step 1: Write failing tests.**
  - `stepStates` with a null overview: step 1 is current, others todo.
  - With customers + invoices: summary "6 invoices · ₹3,15,000.00".
  - With sender review pending: step 4 is attention.
  - With `imported=false`: step 1 summary "Creates a new upload workspace".
  - UploadPage at step 3 presets kind `payments`.
  - Back/Continue change the route step.
- [x] **Step 2: Run.** Fail.
- [x] **Step 3: Implement.** No intake command or label changes; keep every confirmation and refusal message.
- [x] **Step 4: Run** unit tests, typecheck and build. With the lock, run e2e `intake`, `reviewed-intake`, `synthetic-pack` and migrate navigation (go to `#/upload?step=N` before each helper action) until green.
- [x] **Step 5: Screenshot** the Upload page at steps 3 and 5.

### Task 6: Assistant page and Approvals page

**Files:**
- Modify: `frontend/src/pages/AssistantPage.tsx`, `frontend/src/pages/ApprovalsPage.tsx`
- Create: `frontend/src/approvals/queue.ts`, `frontend/src/approvals/useApprovalQueue.ts`, `frontend/src/agents/AgentTeam.tsx`, `frontend/src/agents/assistant.css`
- Modify: `frontend/src/agents/AgentRoster.tsx` (reuse inside AgentTeam), `frontend/src/agents/agentLabels.ts` (add `AGENT_KIND: Record<AgentName,'AI'|'RULES'|'YOU'>` and `AGENT_ORDER`)
- Test: `frontend/tests/approvals.test.tsx`, `frontend/tests/assistant.test.tsx`

**Interfaces:**
- Consumes: `Workspace.cases` (CaseEntry with view), `Workspace.health`, `api.latestMorningReview`.
- Produces:
```ts
export type ApprovalKind='REMINDER'|'CLOSURE'|'PAYMENT_CHECK'|'SUGGESTION';
export interface ApprovalItem {id:string; caseId:string; kind:ApprovalKind; title:string; client:string; amount:Money|null; reason:string}
export function buildQueue(cases:CaseEntry[]):ApprovalItem[];   // rules exactly as spec "Approval queue membership"
export function useApprovalQueue(ws:Workspace):{items:ApprovalItem[]|null; failed:CaseEntry[]}; // null while ws.detailsLoading
```

- [x] **Step 1: Write failing tests.**
  - `buildQueue`:
    - a valid unapproved draft on a CURRENT FOLLOW_UP gives REMINDER;
    - an APPROVED draft gives nothing (unless no disposition, then SUGGESTION);
    - CLOSE with `allowed_commands.close.allowed` gives CLOSURE;
    - VERIFY_PAYMENT gives PAYMENT_CHECK;
    - a running attempt or freshness ≠ CURRENT gives nothing;
    - a closed case gives nothing;
    - no result gives nothing.
  - ApprovalsPage: clicking an item shows the same DraftReview (button "Approve exact saved version"); after the fake api records approval and `refresh()`, the item disappears and the badge count drops.
  - AssistantPage: renders one card per `AGENT_ORDER` with AI/Rules tags; shows provider/model only where `health.configuration.agents` has it; shows supervisor plan rows with `supervisor_reason`; "Show technical details" reveals tokens/latency.
- [x] **Step 2: Run.** Fail.
- [x] **Step 3: Implement per spec §4–§5.** The Approvals right pane embeds `DraftReview` / `OwnerDecisions contextual` / `CaseEvidence` for the item's CaseView, with "Open full case →". Approvals filters: All, Reminders, Closures, Payments, Suggestions (hide empty ones). Wire the Approvals badge in AppShell and the Dashboard tile to `useApprovalQueue`.
- [x] **Step 4: Run** unit tests, typecheck and build. With the lock, run e2e `agents`-related specs (`personas`, `ux-completion`, `investigation`) for regressions.
- [x] **Step 5: Screenshot** both pages.

### Task 7: New browser journey for the course-demo pack, and full test migration close-out

**Files:**
- Create: `tests/e2e/course-demo.spec.ts`
- Modify: any remaining e2e/unit tests still failing after Tasks 3–6, by the test-edit rule

- [x] **Step 1:** Write `course demo pack runs end to end through every page`.
  - Generate the pack into `.runtime/course-demo-e2e` for today via the CLI in the test setup.
  - On `#/upload`, upload each file through the stepper with real file selection, apply the START-HERE allocations, confirm coverage, then Start morning review.
  - On the Dashboard, assert "Still to collect" equals the EXPECTED-RESULTS sum, in ₹.
  - Open Meera's case: the story shows the Hinglish quote; "Our suggestion" says Follow up.
  - On Approvals, approve Meera's reminder and copy it; clipboard equals the saved exact text; "Nothing has been sent" is visible.
  - On the Assistant page, the agent team and the plan are visible.
  - Run the finale (later statement, allocate, coverage, re-check Arun) and assert Close.
  - Screenshot each page.
- [x] **Step 2: Run it with the lock.** Fix product bugs it finds (regression test first).
- [x] **Step 3: Run the full serial Chrome suite with the lock.** Every failure gets root-caused and fixed. A flaky timing failure gets fixed at its cause (wait for the right state), never by a raised timeout.

### Task 8: End-to-end upload robustness sweep (backend + frontend bug fixing)

Scope (owner): upload, parsing, conversion, normalization and reconciliation of invoices, payments, bank statements, messages and emails, tested end to end for all scenarios.

**Files:**
- Create: `backend/tests/integration/test_upload_robustness.py`
- Modify: product files only where a bug is proven

- [x] **Step 1:** Write a parametrized test over realistic variants, each with an expected outcome of either *supported with exact normalized values* or *refused with a specific plain message and nothing saved*. Variants:
  - BOM-prefixed UTF-8 CSV;
  - CRLF line endings;
  - trailing blank lines;
  - quoted fields with commas in addresses;
  - amounts `48000`, `48000.50`, `48,000`, `1,20,000.00`, `Rs. 48,000/-`, `₹48,000`;
  - dates `2026-10-20`, `20/10/2026`, `20-10-2026`, `20 Oct 2026`;
  - headers in different case/order;
  - an extra unknown column;
  - a bank statement with a Debit-only row and a missing Reference;
  - duplicate re-upload of the same file (no-op);
  - an invoice issued in the future (refused);
  - an email with a signature (Task 1);
  - WhatsApp with Hinglish;
  - an email with HTML only (refused);
  - a 7th invoice (refused by the limit).

  For the supported/refused decision, follow what the documented profiles in `docs/demo-import/README.md` promise. A crash, HTTP 500, wrong saved paise, silent drop or confusing message counts as a bug. An undocumented format that is refused clearly is acceptable — record it as a limitation.
- [x] **Step 2:** Run it. For each bug, write the minimal fix with the regression (frontend message-rendering fixes included).
- [x] **Step 3:** Run the backend full suite. It passes.

### Task 9: Review, final regression, LIVE rehearsal, reports (orchestrator)

- [x] **Step 1:** One independent review agent (most capable model) reviews the whole change against the spec, this plan and the Global Constraints. Fix Critical/Important findings with regressions; fix or record Minor ones.
- [x] **Step 2: Final clean pass, in order:**
  - backend full suite;
  - `test:unit`;
  - typecheck + build;
  - full serial Chrome.

  Every suite must pass (intentional LIVE skips only). If anything fails, fix it and rerun the whole pass.
- [x] **Step 3: LIVE rehearsal (owner-authorized, once).**
  - Start the app LIVE following the README's run instructions.
  - Generate the pack for today and run the START-HERE journey through the API or browser.
  - Record, per customer, the AI outputs vs the STUB expectations, provider errors and timings in `reports/course-demo-live-rehearsal.md`.
  - Do not retry beyond what the product itself retries.
- [x] **Step 4: Reports.**
  - `reports/multi-page-ux.md`: what changed, test counts, the test-migration list, bugs fixed, limitations, screenshots list.
  - Update the AGENTS.md current state and the local accounting marker status.
  - Regenerate the `docs/demo-import/course-demo` copy dated for the final day.
