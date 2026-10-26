# Multi-page business UX and course-demo upload pack — design

Status: approved in conversation by the owner on 2026-10-25 (reconstructed 18:51:20Z), after reviewing browser mockups. Branch: existing `005-csv-reconciliation-demo` (dirty tree with prior uncommitted 005 work, which must be preserved).

## Intent

PromiseKeeper today is one long page: header, intake panel, demonstration picker, case list, a case workspace with tabs, morning review and agent trace all stacked together. The owner wants it to feel like a product an Indian MSME owner or small-business person would love and immediately understand, with no technical background required. It will be shown live in a **course demo on a laptop screen**. In the demo the owner will clean up, upload fresh files live, and run with **LIVE Nebius** agents enabled (the owner does this personally; agents building this work never make LIVE calls).

The demo has to show two things: (1) how the application solves the follow-up/collections problem for a business owner, and (2) how the multi-agent system works.

## Goals

1. Split the app into five pages with one job each, connected by top navigation:
   - **Dashboard**: "How is my money doing and what needs me today?"
   - **Upload records**: guided six-step flow.
   - **Cases**: list of cases, plus **one page per case**.
   - **Assistant at work**: the multi-agent process told as a story.
   - **Your approvals**: one queue of everything waiting for an owner decision.
2. Visual style "B · Bright fintech" (chosen by owner): indigo (#4a2fe0 / #7b4cf6) with a coral accent (#ff7a59), soft lavender-grey page background (#f4f5fb), white rounded cards (16–20px radius), a gradient hero card on the dashboard, pill-shaped top-nav tabs with count badges, a Plus Jakarta Sans-style geometric sans (self-hosted or system fallback; no runtime dependency on Google Fonts is required — builder's call), customer initials avatars, coloured status chips (red = promise missed / overdue, amber = check/verify, green = paid/close, indigo = wait/info).
3. Business language throughout headings and summaries ("Still to collect", "Promise missed", "Who to follow up today"); technical details (models, tokens, timings, hashes, IDs) stay available but behind disclosures.
4. A compact **course-demo upload pack**: a few synthetic files that together cover every recommendation outcome and show the agents at work, with a one-page demo script.
5. All regression suites green at the end (backend, frontend unit, typecheck/build, full serial Chrome).

## Non-goals

- Phone/tablet layouts (owner: laptop only for now). Narrow widths must still not overflow (existing accessibility tests at 390–400px and 200% text remain and must pass), but no dedicated mobile design.
- New backend features, endpoints or domain behaviour. This is a frontend restructuring plus data files. Backend changes are allowed only if a page truly cannot be built from existing APIs; any such change needs a regression test and must be called out.
- Changing any safety rule: nothing is ever sent; approval records a decision on the exact saved version; allocations, closure, reopening and deletion keep their explicit confirmations.
- LIVE qualification claims or LIVE runs beyond the one rehearsal below, real customer data, connectors, ElevenLabs, publication (commit/push/PR).
- Replacing the large existing synthetic pack (`docs/demo-import/synthetic-pack/`) or the evaluation datasets.

## Anti-goals (failure even if it "works")

- A business viewer can't tell what to do next on any page.
- Prettier screens that hide or weaken safety wording, confirmations, limitation notices or truthful failure states.
- Tests "fixed" by deleting assertions, loosening timeouts or removing safety checks. Test edits may only change *how a test navigates to* something, or update a deliberately renamed visible label; every behaviour previously asserted must still be asserted.
- Demo files that only work in STUB and fail confusingly with LIVE agents, without the demo script warning about it.
- Invented numbers on the dashboard. Every number is computed from real API data; unknowns are shown as unknown, never as zero.

## Constraints

- React 19 + Vite, no router dependency today. The backend serves `frontend/dist` with FastAPI `StaticFiles(html=True)`, so path URLs like `/cases/x` would 404 on refresh. **Decided: hash routing** (e.g. `#/dashboard`, `#/upload`, `#/cases`, `#/cases/<caseId>`, `#/assistant`, `#/approvals`), implemented in-house (small hook) or with a tiny dependency, builder's call. Default route = Dashboard. Browser back/forward must work. A case link must survive refresh.
- The current workspace ("demonstration copy") selection is kept in `localStorage` under the existing `selected_demonstration_id` key; existing tests set it via `addInitScript`. Keep this behaviour.
- Existing complex behaviour in `App.tsx` must be preserved: navigation-generation guards against stale responses, pending-operation reconciliation (`subscribeCommitted`), deletion handling, review-boundary timers for REAL clock, history paging, source viewer, comparison requests, focus management after opening a case. Moving code into pages must not drop these.
- Accessibility: keep landmarks, skip link, focus-visible outlines, labelled controls, `role=status/alert` live regions, and visible label = accessible name. Keep heading structure sensible per page (one h1 per page).
- Money: the UI shows rupees as `₹` with Indian grouping and two decimals (e.g. `₹2,35,000.75`) via the shared `money()` formatter. **My call** (owner chose INR/Indian look; not explicitly discussed): switch the formatter's prefix from `INR ` to `₹`, keep paise. Backend-authored texts (draft messages, briefings, quotes, refusal reasons) are not rewritten. Update test expectations accordingly. Unknown stays "Unknown".
- Dates keep the existing IST formatting.

## The pages (as agreed in the mockups)

Mockup HTML for reference is in the session scratchpad; the descriptions below are authoritative.

### Shell (all pages)
White top bar: logo mark (indigo→coral gradient square) + "PromiseKeeper"; pill tabs **Dashboard · Upload · Cases · Assistant · Approvals**, with count badges on Cases (open cases) and Approvals (items waiting); on the right a **workspace switcher** (current workspace name/ID, choose another saved workspace, create a demonstration copy from the catalogue, start a new imported workspace via Upload, delete the current workspace with the existing exact confirmation). The existing status banner (STUB/LIVE mode, clock mode, imported-workspace notice) stays visible, restyled as a slim strip; **LIVE vs STUB must remain clearly visible** because the demo runs LIVE. The agent roster currently in the header moves to the Assistant page (a small mode indicator may remain in the bar).

### 1. Dashboard (`#/dashboard`, default)
- Gradient hero: greeting ("Good morning"/"Namaste" — no personal name, none is known), one-line summary of how many cases need attention, the **Run morning check** button (existing Morning Review start/follow/retry behaviour), and the headline **Still to collect** total (sum of known open balances; if any open case's balance is unknown, say "plus N with unknown balance").
- Three KPI tiles computed from the case list: e.g. Follow-ups due (FOLLOW_UP), Payments to verify (VERIFY_PAYMENT), Waiting for you (approval-queue count). Builder may choose the exact three if better supported by data, but each must be derivable from real API data.
- **Follow up today**: the cases needing attention in existing `attentionOrder` (supervisor plan order), each a row with initials avatar, client · amount, one-line reason/status, and "Open →" to the case page.
- **Assistant's morning**: short plain-language summary of the latest morning review (briefing text if present, outcomes count, "Nothing sent") with a link to the Assistant page. The existing horizontally scrolling morning strip may live here or on the Assistant page; builder's call, but the morning review results must remain reachable and keep their existing information.
- Empty state for a brand-new install / empty workspace: a friendly "Start by uploading your records" card linking to Upload, and a secondary "or open a ready-made demonstration" option.

### 2. Upload records (`#/upload`)
- Page header "Bring in your records" + "Download sample files" (links to the course-demo pack files served from the built frontend, or instructions where they live — builder's call; files must be the real pack).
- Left: vertical **six-step stepper**: Customers → Invoices → Bank receipts → Customer messages → Match payments → Confirm & check. Steps show done/current/upcoming, with a short result line once done (e.g. "6 invoices · ₹3,15,000"). The existing "Existing allocations" import is an optional sub-option of Match payments.
- Right: the current step's content, built from the existing `IntakePanel` logic: file choice/drop area, kind selection preset by the step, sender review for messages, read-only preview table, explicit commit, original-file inspection, receipt allocation with explicit confirmation, ledger coverage confirmation, then **Start morning check** (or link to Dashboard). Back/Continue navigation between steps. Users may jump between steps freely; the stepper reflects real workspace state (what has been imported), not just clicks.
- All existing refusals, assumptions, limits and confirmations stay visible in plain language. "Looks like" match hints are labelled as hints.

### 3. Cases (`#/cases`) and case page (`#/cases/<id>`)
- List page: the existing urgent-first overview with "Show all N cases", rendered as cards/rows in the new style (avatar, client, invoice, amount, status chip, next review). Clicking opens the case page.
- Case page: breadcrumb (Cases › client · invoice); header strip with avatar, client, status chip, invoice/due/contact line and three money figures (Invoice · Received · Still to collect, using available financial facts; unknown → "Unknown").
- Sub-tabs: **Overview · Evidence (n) · History**, plus the existing comparison/"What changed" view where relevant.
- Overview, left column: **What happened** — a vertical story/timeline built from the existing timeline/evidence (invoice, payments, messages with highlighted quote and "View original" opening the existing source viewer, review dates); **Key facts** tiles. Right column: **Our suggestion** gradient card (action title, plain explanation, "why" bullets from the saved explanation/sources, the existing Accept/Reject recommendation controls); **Reminder draft** card (existing DraftReview with edit/save/approve/reject/copy, validation messages, "approving does not send anything"); case actions (closure/reopen) when relevant; the Investigate case control and investigation progress.
- Everything currently in FindingsView, WhatChanged, Timeline, CaseEvidence, CaseHistory, OwnerDecisions, ScenarioUpdate, AgentTrace disclosure and FeedbackButtons stays available on this page (in the appropriate tab/card).

### 4. Assistant at work (`#/assistant`)
- Header with latest morning check status/time and **Run morning check again**.
- **Your digital team**: a row of agent cards following the pipeline order (supervisor/planner, evidence intake, promise extractor, payment rules, client memory, communicator + safety check + tone reviewer, and "You"). Each card: icon, existing agent label, plain role line (existing `AGENT_ROLE`), whether it is AI or rule-based code, status from the latest activity, and provider/model from health configuration in a small muted line (this is what the demo uses to explain LIVE Nebius vs STUB).
- **Today's plan**: the supervisor's ordered plan with reasons (existing outcomes/priority/supervisor_reason).
- **Step by step** for a selected case: the existing agent activity rendered as a readable feed with AI/RULES tags; "Show technical details" disclosure reveals models, tokens, latency, cost (existing AgentTrace content).
- This page is the main multi-agent architecture explainer for the demo; it should read clearly to a non-technical audience.

### 5. Your approvals (`#/approvals`)
- One queue built from current cases: reminder drafts awaiting a decision, current recommendations awaiting accept/reject, closures ready for review, payments needing verification. Filters: All · Reminders · Closures · Payments (builder may adjust the categories to what the data supports).
- Left: queue items (avatar, title, amount/reason, type chip). Right: the selected item with key facts and the **same** existing decision component (DraftReview / OwnerDecisions), so behaviour, guards and wording are identical to the case page. Link "Open full case →".
- Approving still never sends; copy-to-clipboard remains the hand-off.
- Data: built from existing per-case views (imported workspaces have ≤6 invoices; demo copies have 6 cases), fetched in parallel; must handle loading, partial failure and refresh after a decision.

## Course-demo upload pack

Location: `docs/demo-import/course-demo/` (new). Fictional Indian MSME companies, contacts and bank references. Small: one customers file, one invoices file (≤6 invoices — the imported-workspace limit), one initial bank statement, a handful of customer messages (email and WhatsApp, including one Hinglish), one later bank statement, plus `START-HERE.md`.

The pack must, through the Upload flow and one morning check, produce each recommendation outcome at least once, each tied to a distinct customer so the demo story is easy to follow:
- **FOLLOW_UP** — a customer whose WhatsApp/email promise date has passed with no payment (include the Hinglish message here or in WAIT).
- **WAIT** — a customer with a future dated promise.
- **VERIFY_PAYMENT** — a customer claiming "already paid" with no matching bank receipt.
- **CLOSE** — a customer fully paid by a receipt the owner allocates.
- A **partial payment** allocated by the owner, leaving a remainder.
- A **later bank statement** that, after re-check, settles the VERIFY_PAYMENT customer so the demo can show re-investigation → CLOSE and the "What changed" comparison.
- One **deliberate safety refusal** (e.g. a conditional promise, or a message whose sender is not the customer) to show the system refusing to guess — optional but recommended.

`START-HERE.md`: a short presenter script — clean-up steps (delete old workspace / start fresh), the upload order, exactly which receipt to allocate to which invoice and the amounts, what each customer should show after the morning check, which page to show for the multi-agent explanation, and the re-check finale. It must state truthfully: expected outcomes are verified with STUB agents offline; with LIVE Nebius the AI steps (promise finding, planning, note writing, tone) can phrase or order things differently and LIVE behaviour on this pack has not been verified; deterministic money rules, refusals and approval gates do not depend on the model.

**Dating (owner decision).** An imported workspace's clock is the real upload time, and future-issued invoices are refused. So the pack is produced by a one-command generator that dates every file relative to an anchor day, defaulting to today. The owner runs it on the morning of the demo, and the checked-in copy is generated for the build day. Follow the existing pattern in `backend/src/promisekeeper/fixtures/synthetic_pack.py`. Suggested shape is a `course_demo_pack.py` fixture plus a CLI entry such as `uv run --project backend python -m promisekeeper.fixtures.course_demo_pack --as-of YYYY-MM-DD --out docs/demo-import/course-demo`; the builder may adjust it. The dates are chosen so that:
- invoices are issued weeks before the anchor day;
- the missed promise falls a few days before it;
- the future promise falls about a week after it;
- receipts land before it.

This keeps the outcomes stable when the demo starts any time on the anchor day. `START-HERE.md` gives the regenerate command first and is regenerated with the files. Tests generate the pack relative to a fixed anchor and also relative to "today".

**LIVE rehearsal (owner decision).** After every offline check passes, the agent runs the demo journey once with LIVE Nebius (credentials loaded only by trusted backend code, never displayed). It records exactly what the AI did per customer, any differences from the STUB expectations and provider errors, in `reports/course-demo-live-rehearsal.md`. This counts as one rehearsal, not a qualification. If LIVE behaviour differs, the demo script warns about it truthfully. The pack or product is changed only if the difference is a real bug, and then the offline suite is rerun.

Verification: a backend integration test uploads the pack through the existing intake API, applies the scripted allocations and coverage, runs the morning review in STUB, and asserts each customer's expected action and balance, plus the later-statement finale. A browser test runs the core journey through the new pages (upload steps → morning check → dashboard → case page → approvals approve + copy → assistant page).

## Testing and done

- New unit tests for the router, dashboard aggregations (including unknown balances), approval-queue assembly and stepper state.
- Existing unit and browser tests are migrated to the new navigation (e.g. go to `#/cases/<id>` or click the Cases tab before asserting) with no loss of asserted behaviour. Report which tests changed and why.
- Final, in this order, all must pass in one clean pass: backend full suite (1 intentional LIVE skip allowed), frontend unit, typecheck + production build, full serial Chrome (intentional LIVE skip allowed). If a flaky failure appears, report it truthfully, investigate the root cause and fix it; the owner asked that nothing fails at the end.
- Screenshots of each page at a 1440×900 laptop viewport inspected.
- One independent review agent reviews the complete change; findings are fixed with regression tests, then the full final pass is repeated.

## Decisions from the builder check (my calls unless marked)

- **Shared case-detail store.** No cross-case endpoint exists and none will be added. A shared frontend store loads the case list plus each case's `CaseView` in parallel (≤6 cases in both workspace kinds). It is invalidated on `refresh` and `subscribeCommitted`. The Approvals badge, Dashboard "Waiting for you" tile and Approvals page all read the same store. While the store is loading, the badge shows no number (never 0). A failed case fetch is listed as "couldn't load, retry" and is never silently dropped.
- **Approval queue membership.** An item is listed when it is open, has a *current* result (freshness CURRENT, no running attempt) and any of these apply:
  - (a) a valid draft whose review state is neither APPROVED nor REJECTED, giving a **Reminder** item;
  - (b) a CLOSE recommendation whose closure is allowed, giving a **Closure** item;
  - (c) a VERIFY_PAYMENT recommendation, giving a **Payment check** item, which shows the evidence and the accept/reject controls;
  - (d) no recorded disposition for the current result, giving a **Suggestion** item, folded into (a), (b) or (c) when one applies.

  Cases with no current result are not approvals. The Dashboard shows them as "Needs a fresh check".
- **Still to collect.** The sum of open-case balances labelled VERIFIED_REMAINDER or RECORDED_REMAINDER. When any recorded amount is included, the sub-line reads "₹X of this is recorded but not yet verified". UNKNOWN balances are excluded and noted as "plus N with unknown balance". Currencies other than INR, or null, are not summed. They are noted separately as "N in other currencies".
- **Money symbol.** `money()` shows `₹` only when the currency is INR and keeps the currency code otherwise. Tests that compare UI money to backend draft text are left alone, because draft text is untouched. The UI shows ₹ next to drafts that say "INR …". This is accepted and noted in the demo script.
- **Stepper state.** The stepper derives its state from `GET /demonstrations/{id}/intake` and the case list. Customers, Invoices and Receipts are done when records of that kind exist. Messages is done when at least one communication is attached and no sender review is pending; a pending sender review shows a "needs your review" state. Match payments is done when every receipt is either allocated or the owner has moved past it with Continue. A receipt left unallocated on purpose is shown as "left unallocated" and is never treated as an error. Confirm & check is done when ledger coverage is confirmed for the current as-of time and a morning review has completed after it. If the overview lacks a field, the builder may add it to the existing intake overview response, read-only, with a contract test. That is the only allowed backend change.
- **Workspace kinds.** When the selected workspace is an imported one, Upload continues it. When there is no selection, or the selection is a demonstration copy, step 1 (Customers) creates a new imported workspace, as today. The Dashboard empty state applies when no workspace is selected or the selected workspace has zero cases. The SENDER_REVIEW_REQUIRED notice stays prominent on the Dashboard and the case page.
- **Later statement finale.** This already works through the existing flow (`docs/demo-import/README.md` step 7): import a later receipts file into the same workspace, allocate, reconfirm coverage and investigate again. Evidence then changes, the old result becomes previous, and the comparison is available. No backend change is needed.
- **Agent cards.** `/health.configuration.agents[]` already lists the provider and model for each role (Supervisor, Extractor, Communicator, Tone Reviewer, Briefing, Memory). Cards show that data only where it exists. Rule-based steps (evidence intake, payment rules, safety check) are labelled "Rules (code)" and show no model.
- **Sample files.** The Upload page shows the pack's folder path and the step's suggested file name. The files are not copied into the build.
- **Test migration rule.** A test may change how it reaches a feature, which tab or page it visits, and labels that were deliberately renamed. A layout-specific assertion such as heading count or tab order may change only if the same user-facing property is re-asserted for the new structure (for example, exactly one h1 per page). Every change is listed in the final report.
- **LIVE visibility.** The existing running and progress states remain. During a running morning check, the Dashboard and Assistant pages both show progress and the mode (STUB/LIVE). Agents never run LIVE.

## Left to the builder

Component/file breakdown, CSS organisation (one stylesheet or per-page files), icon approach (emoji vs inline SVG), exact KPI choices within the stated data rules, exact category set for the approvals filter, where the morning strip lives, how sample files are offered for download, router implementation details.
