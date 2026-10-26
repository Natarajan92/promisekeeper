# Course demo pack - anchored to 2026-10-26

All companies, people, addresses, emails and bank references are fictional.

**Load the full initial pack, then present only two customer stories.** Use
`TWO-SCENARIOS.md` after upload: Lotus Electricals is the end-to-end happy path;
Arun Traders is the claimed payment without matching bank evidence. The other
four customers provide background totals and coverage, not extra walkthroughs.

## 1. Regenerate first (on the demo morning)

From the repository root, regenerate the files so every date is relative to today:

    uv run --project backend python -m promisekeeper.fixtures.course_demo_pack --as-of YYYY-MM-DD

`--as-of` defaults to today in India (IST) and `--out` defaults to
`docs/demo-import/course-demo`. The generator overwrites only its own named files;
your own notes in this folder are kept. An imported workspace uses the real upload
time, and future-dated invoices are refused, so a pack generated for an older day
can show different outcomes (an old "next week" promise may already have passed).

## 2. Clean up

1. In the top bar choose **Workspace > New workspace**. This starts a separate
   upload workspace and keeps existing records available.
2. Begin at **step 1, Customers**. Delete old workspaces only if you separately
   want to remove their saved data; deletion is not required for this pack.

## 3. Upload, step by step

Each step: choose the file, press **Preview file**, read the preview, tick the
review confirmation and choose **Confirm import**.

Upload only the initial CSV files and all four files in `04-messages` now.
**Hold back both files in `05-later`** until their story reaches the payment
stage. Loading those receipts early removes the discrepancy or the follow-up
that you want to demonstrate. Files in `06-refused` are optional Q&A fixtures,
not part of the two-story presentation.

| Step | File | Kind | Target invoice | Sender role |
|---|---|---|---|---|
| 1 Customers | `01-customers.csv` | Customers | - | - |
| 2 Invoices | `02-invoices.csv` | Invoices | - (six invoices, ₹3,12,500.00 in total) | - |
| 3 Bank receipts | `03-bank-statement.csv` | Receipts / bank statement | - | - |
| 4 Customer messages | see the table below, one file at a time | | | |

Step 3 shows the bank-profile assumptions. The BESCOM electricity row is a debit and
is skipped on purpose. Credits are not allocated automatically.

| File | Kind | Target invoice | Sender role |
|---|---|---|---|
| `04-messages/meera-whatsapp-hinglish.txt` | WhatsApp message | MT-1001 · Meera Textiles | Customer (I checked the sender) |
| `04-messages/arun-payment-claim.eml` | Customer email | AT-1002 · Arun Traders | Customer (I checked the sender) |
| `04-messages/kaveri-promise.eml` | Customer email | KP-1004 · Kaveri Packaging | Customer (I checked the sender) |
| `04-messages/lotus-promise.eml` | Customer email | LE-1005 · Lotus Electricals | Customer (I checked the sender) |

Read the exact quote in each preview. The Kaveri email has a greeting, a thank-you
line and a signature; the promise line is still found. Meera's message is Hinglish.
Lotus has a direct English promise for the main happy path.

Choose the target invoice and **Customer (I checked the sender)** for each
message. Leave **Optional: supporting context only** off for these four payment
messages. If it was selected accidentally, choose **Review payment wording**,
review the fresh preview, then tick the confirmation and **Confirm import**.

**Optional Q&A refusal (do not include in the main presentation).** In step 4 preview
`06-refused/patel-conditional.txt` as WhatsApp message for PH-1006 · Patel Hardware,
sender Customer. Preview refuses it because "if the goods are replaced" is a
condition, not a firm promise. It cannot be confirmed and nothing is saved.

## 4. Match payments (step 5) - exact allocations

Allocate each receipt explicitly, one at a time, and confirm each:

| Bank credit (reference) | Invoice | Amount (INR) | Note |
|---|---|---:|---|
| UPI MEERA TEXTILES (`UPI-552104`) | MT-1001 · Meera Textiles | 12000 | Partial payment; INR 48,000 remains. |
| NEFT SUNRISE FOODS (`NEFT-883107`) | SF-1003 · Sunrise Foods | 40000 | Pays the invoice in full. |
| NEFT PATEL HW (`NEFT-304172`) | PH-1006 · Patel Hardware | 10000 | No invoice reference on the credit; match it by the Patel HW name hint. INR 15,000 remains. |

The "looks like" suggestions are hints from names only; you make the match.
Leave nothing else allocated. Skip the optional "Existing allocations" import.

## 5. Confirm and check (step 6)

Confirm ledger coverage for all six invoices through the displayed cutoff (your
assertion for these fictional records), then press **Start morning review**.

Expected after the morning check (verified offline with STUB agents):

| Customer | Invoice | Invoice value | Suggestion | Still to collect | Why |
|---|---|---:|---|---:|---|
| Meera Textiles | MT-1001 | ₹60,000.00 | Follow up | ₹48,000.00 | Hinglish promise for 18 October 2026 has passed; INR 48,000 still open after the INR 12,000 part payment. |
| Arun Traders | AT-1002 | ₹32,500.00 | Verify payment | ₹32,500.00 | Customer says it paid (UTR ARUN-T9) but no matching bank credit is allocated yet. |
| Sunrise Foods | SF-1003 | ₹40,000.00 | Close | ₹0.00 | Full INR 40,000 bank credit allocated by the owner; closure still needs the owner's confirmation. |
| Kaveri Packaging | KP-1004 | ₹75,000.00 | Wait | ₹75,000.00 | Promise to pay INR 75,000 by 2 November 2026; review again when that day ends. |
| Lotus Electricals | LE-1005 | ₹80,000.00 | Follow up | ₹80,000.00 | Clear customer promise for 24 October 2026 has passed; INR 80,000 remains. Review the supported reminder before using it. |
| Patel Hardware | PH-1006 | ₹25,000.00 | Follow up | ₹15,000.00 | INR 10,000 part payment matched by hint; INR 15,000 overdue. The conditional message is refused, not imported. |

Still to collect: ₹2,50,500.00 across the open invoices. Sunrise shows Close,
but stays open until you review and confirm the closure yourself.

## 6. Present exactly two scenarios

Open `TWO-SCENARIOS.md` for the click-by-click talk track.

| Order | Customer | What to explain |
|---|---|---|
| Scenario 1 | Lotus Electricals / LE-1005 | Proper source records, supported Follow up, Assistant trace, Approvals, exact-version approval/copy, later INR 80,000 receipt, explicit matching, zero remainder and owner-confirmed closure. |
| Scenario 2 | Arun Traders / AT-1002 | A payment claim with UTR ARUN-T9 has no matching imported receipt. The app shows Verify payment and INR 32,500 outstanding, keeps the evidence visible, and does not infer settlement. Optional matching evidence later resolves it. |

Show the Dashboard totals once for context. Do not open the other four customers
as separate stories. The six-case table above is preparation/reference material.

Drafts and briefings are written by the backend and say "INR ...", for example
"INR 80,000.00"; the screens show the same money as "₹" with Indian grouping,
for example "₹80,000.00".

## 7. Optional resolution within scenario 2 - the claimed payment arrives

1. Upload `05-later/payments-later.csv` in step 3 (Receipts / bank statement). It has the
   NEFT ARUN TRADERS credit with reference ARUN-T9 dated 23 October 2026.
2. In step 5 allocate ARUN-T9 to AT-1002 · Arun Traders for INR 32500.
3. In step 6 confirm coverage again (every new import makes the earlier
   coverage and approvals stale).
4. Open the Arun Traders case and press **Investigate case**. Expected: **Close**,
   still to collect ₹0.00, and the claim is now supported by the bank
   reference. The earlier Verify payment result stays in the case history; use
   "What changed" to compare it. The case stays open until you review closure.

## Truthful limits

Expected outcomes use STUB agents for offline verification. This revised
two-story pack, including the new Lotus promise and staged receipt, has not had
a LIVE rehearsal. The historical one-run evidence for the older pack remains in
`reports/course-demo-live-rehearsal.md`; it reported five of six matching initial
actions (Meera differed) and all six matching balances. That evidence is not a
qualification of this revised dataset. No new LIVE run is authorized here.

LIVE wording, ordering and findings can differ. Inspect actual results; do not
claim a preset action or hide uncertainty. Money rules, source refusals and
approval gates remain code-enforced. Nothing is ever sent to a customer.
