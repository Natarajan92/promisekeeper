# Course-demo LIVE rehearsal — saved-artifact recovery

The single owner-authorized LIVE rehearsal ran to completion on 26 October 2026. The saved API run recorded a complete six-case morning review and the Arun Traders later-statement finale, then exited with code 0. Five of six initial recommendations matched the independent STUB pack expectations; all six balances matched. Meera Textiles differed: the expected missed-promise `FOLLOW_UP` became `VERIFY_PAYMENT` with unresolved customer-clarification claims. This is one fictional rehearsal, not LIVE qualification, a human acceptance study or evidence that every presenter step was exercised. The planning supervisor and other newly introduced agents remain unqualified; historical single-extractor qualification is separate.

This report was reconstructed offline from the saved `.runtime/live-rehearsal/rehearse.py`, `observations.json`, `run.log` and generated pack, checked against `backend/src/promisekeeper/fixtures/course_demo_pack.py` and `backend/tests/integration/test_course_demo_pack.py`. Recovery did not run the script, contact the app/provider, inspect credentials or read the raw server log. The original artifacts were preserved.

The design and implementation plan required every offline check to pass before LIVE. The contemporaneous work record instead says the rehearsal started after backend Tasks 1/2/8 passed 1,243 checks, while frontend Task 4 was still running and Tasks 7/9 remained. Therefore this rehearsal predates the final frontend/full-regression pass and final review. Later offline results cannot retroactively satisfy that ordering or establish LIVE behavior of later changes. The one rehearsal allowance has been consumed; this recovery does not authorize another run.

## What ran

The script used the existing local API in `LIVE` mode and an isolated fictional imported workspace. Health reported Nebius `Qwen/Qwen3-235B-A22B-Instruct-2507` for Supervisor, Extractor, Communicator, Tone Reviewer and Briefing, with Memory local. This is the reported configuration; the saved observations do not contain every individual agent response or attempt.

The pack was generated for **2026-10-26 IST**. The script previewed and committed customers, six invoices, the initial bank statement and three customer messages; applied the three explicit scripted allocations; confirmed coverage for all cases; started one morning review; and saved each case's recommendation, balance, commitments, claims and draft. It then imported the later Arun statement, allocated `ARUN-T9` to `AT-1002` for INR 32,500, reconfirmed coverage and started one further investigation of Arun. The helpers assert successful preview/commit/allocation/coverage responses. Reaching the recorded finale and exit 0 shows those assertions completed.

| Saved checkpoint | Elapsed from script start |
|---|---:|
| LIVE health recorded | 0.1 s |
| Initial uploads, allocations and coverage completed | 1.0 s |
| Morning review returned `COMPLETE` | 83.4 s |
| Six case snapshots saved | 83.5 s |
| Arun finale snapshot saved | 89.9 s |

The wall timestamps are **06:10:28.705570–06:11:58.557160 IST** (**00:40:28.705570–00:41:58.557160 UTC**), approximately 89.85 seconds. These are automated API-script timings, including polling and client work; they are not browser, provider-only or human presentation timings.

## Initial customer results

Expected values below come from the generated manifest's independent oracle, not from the observed recommendations. All six observed balances matched it, totaling **INR 2,50,500.00** still to collect.

| Customer · invoice | STUB expected | LIVE observed | Observed balance | Saved findings and draft |
|---|---|---|---:|---|
| Meera Textiles · `MT-1001` | `FOLLOW_UP` | **`VERIFY_PAYMENT` — differs** | INR 48,000.00 | One expired INR 48,000 commitment, with `fulfillment_unresolved=true`, plus three unresolved claims marked `customer_clarification=true`, all citing the uploaded Meera source. A `VALID` draft asks for a missing payment reference or receipt. |
| Arun Traders · `AT-1002` | `VERIFY_PAYMENT` | `VERIFY_PAYMENT` | INR 32,500.00 | One unresolved claim, `customer_clarification=false`; no commitment. No draft: `INTERNAL_VERIFICATION_NO_CUSTOMER_DRAFT`. |
| Sunrise Foods · `SF-1003` | `CLOSE` | `CLOSE` | INR 0.00 | No commitments or claims. Explanation says verified settlement supports explicit owner review of closure. No draft: `CLOSE_NO_CUSTOMER_DRAFT`. |
| Kaveri Packaging · `KP-1004` | `WAIT` | `WAIT` | INR 75,000.00 | One unfulfilled promise, no claims or unresolved fulfillment. Review boundary is **3 November 2026, 00:00 IST**, after the promised 2 November day. No draft: `WAIT_NO_CUSTOMER_DRAFT`. |
| Lotus Electricals · `LE-1005` | `FOLLOW_UP` | `FOLLOW_UP` | INR 80,000.00 | No commitments or claims. A `VALID` draft states the verified overdue balance and asks for a payment update. |
| Patel Hardware · `PH-1006` | `FOLLOW_UP` | `FOLLOW_UP` | INR 15,000.00 | No commitments or claims. A `VALID` draft states the verified overdue remainder and asks for a payment update. The conditional message was not imported or previewed by this script. |

Meera's fictional message was sent on 14 October and says: “Hum ₹48000 18 October 2026 ko payment kar denge.” The initial INR 12,000 receipt predates it; the expected story is an expired promise for the remaining INR 48,000. The saved result instead says the recorded remainder is contested and requires reviewing unresolved payment facts. Its draft includes “Could you please share the missing payment reference or receipt?” This changes the customer story and proposed next step, beyond a phrasing or planning-order difference. The saved snapshot establishes the discrepancy, but contains no raw extractor response or claim text sufficient to identify which message span caused each clarification claim; no more specific root cause is claimed here.

Lotus and Patel's drafts also contain relationship-oriented opening paragraphs before the verified amount and payment-update request. Their recorded validation status is `VALID`; that status is not independent tone or factual qualification. No draft was approved, copied or sent during this script.

The supervisor investigated in this order: **Lotus → Kaveri → Meera → Arun → Sunrise → Patel**. Its saved reasons prioritized the larger balances first, then required the remaining cases to be investigated. All six outcomes are `INVESTIGATED`. The saved investigation activity durations, in that order, are 10,952 / 12,391 / 20,655 / 8,797 / 2,906 / 5,375 ms. These are the reported activity durations, not separate measurements of each underlying model call.

The briefing source was `AGENT`. It reflected the observed recommendations: follow up Lotus and Patel; verify Meera and Arun; wait on Kaveri until 3 November; Sunrise marked for closure. Its saved activity outcome is `SUCCEEDED`, with the note “Every number matches your case facts.” That note does not resolve the Meera recommendation discrepancy or replace the separate owner closure review.

## Finale, errors and evidence limits

The finale is **completed in the saved evidence**, not interrupted by the later session limit. After the later statement and explicit allocation, Arun's re-investigation recorded `CLOSE` with INR 0.00, matching the manifest. The script then wrote its `finished` timestamp; `run.log` records the output-write message and `exit 0`.

The finale checkpoint saves only action, balance and expected action. It does **not** save the final claim-resolution flags, lifecycle, investigation IDs, case history or comparison response. Therefore LIVE claim resolution, preserved-history/“What changed” behavior and the case remaining open are not independently verified by this artifact. Those are asserted more fully by the separate STUB integration test. No closure command exists in the rehearsal script, so a `CLOSE` recommendation must not be presented as an owner-approved closed case.

The morning review recorded `status=COMPLETE`, `failure=null`, and all saved supervisor/briefing activity outcomes are `SUCCEEDED`. No provider error is visible in these saved observations or the short script log. The JSON's `errors` array is empty, but the script initializes it and never appends to it; it is not a comprehensive provider-error collector. Internal retries, fallback behavior or per-agent errors absent from this snapshot cannot be ruled out. No provider call count, usage total or cost is inferred.

This API rehearsal did not preview the deliberate conditional-message refusal, approve/copy a draft, exercise browser navigation or inspect the rendered pages. It did not perform the presenter's cleanup/deletion steps. Its complete API execution is narrower than the complete `START-HERE.md` presentation. Future demos should warn that Meera produced verification rather than follow-up in this single LIVE run; use Lotus or Patel for the follow-up example and Lotus for the approval/copy example. The deterministic balances and Arun's recorded zero-balance finale matched expectations, while LIVE behavior remains unqualified.
