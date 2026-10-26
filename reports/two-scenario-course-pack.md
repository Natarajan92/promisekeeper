# Two-scenario course upload pack

Publication authorization, 26 October 2026: the owner subsequently requested pushing the required 007 code, tests, fixtures and product documentation and merging to `main`, while excluding submission documents/folders and personal records. Local/uncommitted statements below describe the original verification checkpoint. Fresh publication checks are recorded in [the publication report](product-007-publication.md); LIVE and human-acceptance limits remain unchanged.

26 October 2026. Local fixture/documentation continuation on `007-product-verification-ux`; existing application changes are preserved. No product interface was changed for this task.

The owner requested a full initial upload followed by only two narrated scenarios, and selected a customer payment claim without matching bank evidence as the problematic case.

The pack retains six customers, six invoices totalling INR 3,12,500, all three initial receipts/allocations and the original message/refusal cases. It adds a direct English Lotus promise, a separate later Lotus receipt and `TWO-SCENARIOS.md`. The generator writes 13 named files, regenerates dates relative to its anchor, and preserves unrelated presenter notes. Preparation instructions distinguish seven initial upload files from the two staged credit extracts. The four other customers remain background data.

| Story | Case | Independently checked path |
|---|---|---|
| Happy path | Lotus Electricals / LE-1005 | INR 80,000 overdue with a clear expired promise; Follow up, exact-version approval/copy, import LOTUS-T9, explicit allocation/coverage, Close at zero, owner-confirmed CLOSED |
| Payment discrepancy | Arun Traders / AT-1002 | Claimed INR 32,500 / ARUN-T9 absent from initial bank evidence; Verify payment and recorded remainder awaiting verification; optional matching receipt/allocation resolves the claim and recommends Close at zero |

Lotus's receipt alone never reduces its invoice balance before allocation, and never resolves Arun's unrelated claim. Later receipts invalidate earlier reviews. Coverage is reconfirmed, the cases are investigated again, and closure remains an explicit owner decision. Arun's later evidence does not reopen the already closed Lotus case. Earlier results and exact approvals remain inspectable. Copying a draft sends no message and is not presented as causing a payment.

Independent totals: initially INR 2,50,500 still to collect; INR 1,70,500 after Lotus's allocation; INR 1,38,000 after Arun's optional resolution. Arun's initial remainder is recorded and unverified, rather than an assertion that the customer's claim is false. Running balances are omitted from the separate later credit extracts.

Verification:

- Two new API/generator checks failed before implementation: no two-story metadata and no Lotus promise. All **eight** course-pack integration checks subsequently passed, then passed again with the independent aggregate balance assertions.
- The updated existing full upload/browser journey passed. The new two-story browser journey initially failed because its exact Dashboard button selector omitted the decorative star. The selector was corrected without changing product code, assertions or timeouts; its focused recheck passed. Both browser journeys have passing evidence; the original failure/trace is preserved.
- The new browser journey exercises all initial records, Lotus source evidence and Assistant trace, exact approval and clipboard contents, staged receipt matching, explicit closure, Arun's unresolved claim/closure guard, optional resolution and comparison of saved findings. Five story screenshots were visually inspected.
- A final generation check covers deterministic output, the exact two-story metadata and byte-for-byte consistency of the checked-in pack.
- One independent read-only review found no Critical, Important or Minor issues in the scoped generator, pack, instructions and tests.

All application checks used fictional records and STUB agents. This revised Lotus evidence and two-story sequence have not had a LIVE rehearsal. The older LIVE report remains historical and is not qualification of the revised pack. No real customer data, customer sending, human usability acceptance, commit, push or merge is implied.
