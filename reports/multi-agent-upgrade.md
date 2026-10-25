# Multi-agent upgrade report

Branch `002-multi-agent-upgrade`, based on main `5748d7c`. Plan: [2026-10-24-multi-agent-upgrade.md](../docs/superpowers/plans/2026-10-24-multi-agent-upgrade.md). Decision record: [ADR-010](../specs/001-payment-case-mvp/research.md#adr-010-multi-agent-orchestration-with-langgraph).

## What was built

| Plan task | Outcome | Notes |
|---|---|---|
| 1 Settings, tracing, agent activity log | Done | Fireworks, mem0, LangSmith, token-rate and autonomy settings; keys never leave the backend. |
| 2 Personal-note slot | Done | One paragraph after the greeting; numbers, currency, fees, payment claims, instructions and placeholders are blocked. |
| 3 Communicator, Tone Reviewer, Briefing (strict schemas) | Done | Strict JSON-schema outputs, usage capture, failure classification; offline stand-ins for every agent. |
| 4 LangGraph case graph with owner pause/resume | Done | Existing persisted steps run as graph nodes; approval resumes the paused run, also after a restart. |
| 5 Agent trace with time, tokens, cost | Done | Live trace while investigating; cost only when the owner configures rates. |
| 6 Owner feedback and draft-edit learning | Done | Saved locally; sent to the LangSmith run when configured. |
| 7 Evaluations, tone judge, injection and Hinglish sets | Done (offline) | Offline runs prove the harness only. |
| 8 Morning Review supervisor and briefing | Done | Picks cases that need work, never starts running or closed cases, checks briefing numbers. |
| 9 Client payment memory | Done | SQLite by default; mem0 REST adapter verified only with a mocked transport. |
| 11 Six persona walkthroughs and UX fixes | Done | [Simulated walkthroughs](persona-walkthroughs.md); 6 of 9 gaps fixed, 1 partly fixed, 2 deferred. |
| 12 Multi-agent hardening | Done | Typed hand-off protocol, read-only AI agents, untrusted-text screening, per-model circuit breaker, opt-in autonomous reviews. |
| 10 Docs and verification | Done | README, ADR-010, test cases UT-15 to UT-20, this report. |
| Real-data import | Removed by the owner | Demo with fictional data and no real connectors. |
| ElevenLabs voice briefing | Deferred by the owner | Not started. |

Also fixed: a bug already on `main`. The findings inventory pin was computed from a Windows (CRLF) copy while Git stores LF, so a fresh clone failed 73 evaluation checks. Pins now cover line-ending-normalised content.

## Verification actually run

Final run on the committed branch, one suite after another on the owner's Windows machine, offline (STUB), with no provider calls:

| Check | Result |
|---|---|
| Backend (pytest) | 868 passed, 1 skipped |
| Frontend typecheck | Passed |
| Frontend unit (Vitest) | 104 passed |
| Frontend build | Passed |
| Browser (Playwright, Chrome), including the six persona journeys | 86 passed, 1 skipped (the LIVE timing test, skipped by default) |

Earlier runs that overlapped with other test suites produced load-related timeouts (an isolated server starting too slowly); each of those tests passed when re-run alone. One real timing issue was found: a browser-test helper treated an investigation as finished before its draft was saved, so a follow-up update hit the deliberate revision-conflict check. The helper now waits for drafting to settle.

## Independent review

A fresh reviewer (a separate AI model instance with no access to this build session's context) reviewed the whole branch and found 0 Critical, 5 Important and 9 Minor issues. All 5 Important issues were fixed, each with a test that failed first:

1. The personal-note check only blocked listed words, yet the trace called the note "safety checked". The note is now warmth only: payment, money, date, contact, cancellation and legal words are blocked; a tone-review error drops the note; the trace wording is accurate.
2. A Morning Review interrupted by a restart blocked every later review of that copy. Restart recovery now fails it, and the panel follows a running review or offers Check again.
3. A graph fault after the result was saved could leave a draft attempt running. It is now marked failed and can be retried.
4. Client memory was shared across demonstration copies. It is now scoped per copy (migration 009).
5. The briefing check accepted spelled-out amounts and numbers attached to the wrong client, while the UI said every number was checked. Both are now rejected, and the UI states exactly what is checked.

## Evaluation status (honest)

- The offline agent suite (`reports/agent-evaluation-offline.json`) and the offline Hinglish suite (`reports/hinglish-evaluation-offline.json`) used scripted stand-ins. Their perfect scores prove only that the harness, the safety check and the fallback plumbing work. **They say nothing about model quality.**
- **No LIVE provider calls were made for this upgrade.** The Communicator, Tone Reviewer, Briefing agent, Fireworks reviewer and mem0 memory are unmeasured on real models.
- The Release 0.1 extraction qualification (152 of 153) covers the unchanged extractor only.
- The judge calibration sheet `reports/agent-judge-calibration.csv` is blank; it needs about five of the owner's own tone ratings.

## LIVE commands for the owner

Set `PK_AGENT_MODE=LIVE` and the keys in `.env` (see `.env.example`). Each command makes real provider calls.

```powershell
uv run --project backend python -m promisekeeper.cli evaluate --suite agents --catalogue release-0.1 --repeats 3 --output reports/agent-evaluation-live-1.json
uv run --project backend python -m promisekeeper.cli evaluate --suite hinglish --catalogue release-0.1 --output reports/hinglish-evaluation-live-1.json
```

With `LANGSMITH_TRACING=true` and `LANGSMITH_API_KEY` set, the results are also uploaded as LangSmith datasets, and serving the app sends each investigation's graph trace and the owner's feedback to LangSmith.

## Known limits and deferred items

- Some system wording remains in the UI ("Designated source authority", "Non-authoritative source", "revision N", copy labels with REFERENCE and IDs), because reviewed browser tests pin it.
- The draft template says a promise "by 20 October" reached its deadline at "21 October 2026, 00:00 IST". This is correct, but reads oddly to a customer. The template is owner-reviewed.
- Paused review threads are not removed from the graph checkpoint store when a demonstration copy is deleted (fictional data only).
- Autonomous reviews are off by default; in LIVE mode they spend model credits without a click.

## Deferred minor findings (from the independent review)

- morning-review investigations recorded with STUB provenance in LIVE (start_investigation without agent_mode/model)
- resume should require next == ('owner_review',) to avoid replaying drafting nodes from an older checkpoint
- drafting overlaps next investigation on the shared provider lock; template save can time out behind extraction (FAILED, retryable)
- mem0 calls not bounded by the investigation deadline; mem0 memories not deleted with their copy
- LangSmith feedback call is synchronous; UI says "not configured" when configured but failed
- feedback replay ignores copy/case/payload mismatch
- autonomy has no backoff for repeatedly failing cases; owner Investigate gets INVESTIGATOR_BUSY without a hint during a pass
- delete_demonstration does not refuse during a running morning review; graph checkpoints keep packets after copy deletion
- AgentActivityView.morning_review_id typed str instead of Id

## Decisions made overnight (rulings)

Each ruling records what was decided, why, and what it costs if wrong.

- **Task 1:** fixed pre-existing main bug (findings inventory pin = CRLF hash; repo stores LF => 73 failures on any fresh clone) by pinning LF-normalised bytes — required for a green verifiable branch and for judges cloning — cost if wrong: pin semantics changed from raw bytes to EOL-normalised content (content changes still fail).
- **Task 1:** agent_activity.demonstration_id has no cascade; delete_demonstration deletes its rows explicitly (soft-deleted copies) — cost if wrong: none.
- **Task 2:** draft-test helpers copied to backend/tests/support/drafts.py (test_drafts.py untouched) — avoids editing reviewed tests — cost if wrong: small duplication.
- **Task 2:** note_reasons also flags INR/₹ as UNSUPPORTED_CURRENCY (notes never carry currency) — stricter than plan — cost if wrong: none.
- **Task 3:** briefing number check compares normalised number tokens (commas removed, trailing .00 dropped) instead of substring match — stricter, avoids '8' matching '80000' — cost if wrong: a briefing that rounds may fall back to deterministic text.
- **Task 3:** build_agents takes optional usage_sink so the LIVE extractor keeps recording provider usage — cost if wrong: none.
- **Task 4:** legacy investigate() without an AgentSet keeps template-only drafts (communicator/reviewer None => SKIPPED) — preserves reviewed behaviour for direct callers; the API passes build_agents(settings) — cost if wrong: none.
- **Task 4:** added guarded drafting nodes + save_draft failure marking (found by existing test_draft_failure_... and new tests): unexpected drafting faults => template or FAILED attempt, never RUNNING forever — cost if wrong: none.
- **Task 4:** tone reviewer provider error keeps the safety-checked note (FAILED row explains); only rejection/time shortage drops it — owner reviews anyway — cost if wrong: unreviewed-tone note reaches owner review.
- **Task 4:** investigate() returns True iff an investigation_results row exists (robust to post-commit graph faults) — cost if wrong: none.
- **Task 5:** drafting trace in Review is a collapsed disclosure that loads on open (existing review test shares one fake fetch; also less clutter) — cost if wrong: one extra click to see drafting steps.
- **Task 5:** live trace rendered inside InvestigationControls while running; full trace under the recommendation — cost if wrong: none.
- **Task 6:** feedback idempotency via UNIQUE operation_id on owner_feedback (not operation_receipts) — feedback is advisory, not a case command, and must not bump case_revision — cost if wrong: none.
- **Task 6:** draft edit diff stored locally only (not sent to LangSmith) — avoids sending draft text off-machine by default — cost if wrong: weaker remote dataset.
- **Task 7:** eval drafting loop re-implements the graph's 2-attempt policy with note_reasons (plan-independent) instead of driving the DB graph — keeps evals provider-only and fast — cost if wrong: eval can drift from graph policy (both use MAX_NOTE_ATTEMPTS=2).
- **Task 7:** Hinglish eval uses a simple classifier prompt (not the anchored production extractor) and is labelled as language-coverage research — cost if wrong: does not prove production extraction on Hinglish.
- **Task 7:** injection 'steered' = final note contains a case steer term or any digit — cost if wrong: misses paraphrased steering (LLM judge partially covers).
- **Task 8:** vitest fileParallelism=false — whole-app tests use the 1s default wait and became timing-dependent with three more test files; serial run 94/94 twice in ~21s — cost if wrong: slower unit runs.
- **Task 8:** e2e 78/80 with 2 'isolated backend readiness timed out' during concurrent unit runs; both pass alone — final verification runs suites sequentially — cost if wrong: none.
- **Task 9:** mem0 via its REST API with httpx (no mem0ai SDK) — avoids a heavy dependency; verified only with a mocked transport, so LIVE mem0 is unverified — cost if wrong: mem0 errors fall back to no memory (FAILED row), never break a case.
- **Task 9:** memory keyed by client name across copies in one DB, deleted with its copy — cost if wrong: two copies share a client's history.
- **Task 12:** autonomy is opt-in (PK_AUTONOMOUS_REVIEW_MINUTES, default 0) — LIVE autonomous runs spend credits and act without a click — cost if wrong: judges must enable it to see autonomy.
- **Task 12:** injection screening hides instruction-like sentences only from writing agents; extractor keeps exact evidence (qualified path unchanged) — cost if wrong: extractor still sees attacks (validated by spans + deterministic rules).
- **Task 12:** circuit breaker applies to new agents' chat_structured only, not the qualified NebiusInvestigator — avoids changing the qualified extraction path — cost if wrong: extractor keeps its own 1-retry policy during outages.
- **Task 12:** Communicator→Owner removed from protocol; failed/skipped Communicator hands nothing on (owner gets code template) — cost if wrong: none.
- **Task 11:** source-button accessible name changed to start with its visible label (WCAG 2.5.3); two existing tests pinned the old name ("Open source …") and were updated deliberately — cost if wrong: none.
- **Task 11:** G4 keeps the "Investigate case" label (many tests/scripts depend on it) and only demotes its styling plus helper text when a current recommendation exists — cost if wrong: weaker visual cue than a relabel.
- **Task 11:** G7 remaining jargon and G9 template deadline wording deferred (reviewed browser/draft tests pin them; template change needs owner sign-off) — cost if wrong: owners see some system terms.
- **Final:** I1 tone-review error now drops the note (reverses Task 4 ruling); reviewer-not-configured still keeps the deterministically checked note per plan Review Focus 4 — cost if wrong: unreviewed warm note when owner chose no reviewer.
- **Final:** briefing number-word list includes two..nineteen, so an LLM briefing saying "two cases" falls back to the deterministic summary — conservative — cost if wrong: more plain briefings.
- **Final:** I1/I5 judged Important (not Minor) by effect — owner was told unverifiable money text was "checked" — cost if wrong: none.
