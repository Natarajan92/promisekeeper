# Course demo pack - anchored to 2026-10-26

All companies, people, addresses, emails and bank references are fictional.

## 1. Regenerate first (on the demo morning)

From the repository root, regenerate the files so every date is relative to today:

    uv run --project backend python -m promisekeeper.fixtures.course_demo_pack --as-of YYYY-MM-DD

`--as-of` defaults to today in India (IST) and `--out` defaults to
`docs/demo-import/course-demo`. The generator overwrites only its own named files;
your own notes in this folder are kept. An imported workspace uses the real upload
time, and future-dated invoices are refused, so a pack generated for an older day
can show different outcomes (an old "next week" promise may already have passed).

## 2. Clean up

1. In the top bar open the **workspace switcher** and **delete the current
   workspace** (confirm the exact deletion prompt). Repeat for any older demo
   workspace you do not want to show.
2. Open **Upload** and begin at **step 1, Customers**. This starts a new imported
   workspace. If a demonstration copy is selected, Upload still starts a new one.

## 3. Upload, step by step

Each step: choose the file, press **Preview file**, read the preview, then confirm.

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

Read the exact quote in each preview. The Kaveri email has a greeting, a thank-you
line and a signature; the promise line is still found. Meera's message is Hinglish.

**Safety refusal (show, do not import).** In step 4 preview
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
assertion for these fictional records), then press **Start morning check**.

Expected after the morning check (verified offline with STUB agents):

| Customer | Invoice | Invoice value | Suggestion | Still to collect | Why |
|---|---|---:|---|---:|---|
| Meera Textiles | MT-1001 | ₹60,000.00 | Follow up | ₹48,000.00 | Hinglish promise for 18 October 2026 has passed; INR 48,000 still open after the INR 12,000 part payment. |
| Arun Traders | AT-1002 | ₹32,500.00 | Verify payment | ₹32,500.00 | Customer says it paid (UTR ARUN-T9) but no matching bank credit is allocated yet. |
| Sunrise Foods | SF-1003 | ₹40,000.00 | Close | ₹0.00 | Full INR 40,000 bank credit allocated by the owner; closure still needs the owner's confirmation. |
| Kaveri Packaging | KP-1004 | ₹75,000.00 | Wait | ₹75,000.00 | Promise to pay INR 75,000 by 2 November 2026; review again when that day ends. |
| Lotus Electricals | LE-1005 | ₹80,000.00 | Follow up | ₹80,000.00 | Overdue, no payment and no message. |
| Patel Hardware | PH-1006 | ₹25,000.00 | Follow up | ₹15,000.00 | INR 10,000 part payment matched by hint; INR 15,000 overdue. The conditional message is refused, not imported. |

Still to collect: ₹2,50,500.00 across the open invoices. Sunrise shows Close,
but stays open until you review and confirm the closure yourself.

## 6. What to show

- **Dashboard** - "Still to collect", the follow-ups due and payments to verify
  tiles, and the **Follow up today** list in the assistant's plan order.
- **Case page story** - open Meera Textiles: the invoice, the part payment, the
  Hinglish promise with "View original", the missed promise date and **Our
  suggestion**. Open Kaveri Packaging to show **Wait** and its review date.
- **Assistant page** - the multi-agent architecture: **Your digital team** cards
  (planner/supervisor, evidence intake, promise extractor, payment rules, client
  memory, communicator with safety check and tone reviewer, and You), **Today's
  plan** with reasons, and **Step by step** for a case with AI vs RULES tags.
  "Show technical details" reveals models, tokens and timings.
- **Approvals** - open Lotus Electricals' reminder, **Approve exact saved
  version**, then **Copy approved message**. Approving sends nothing; copying is
  the hand-off to your own WhatsApp or email.

Drafts and briefings are written by the backend and say "INR ...", for example
"INR 80,000.00"; the screens show the same money as "₹" with Indian grouping,
for example "₹80,000.00".

## 7. Finale - the claimed payment arrives

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

Expected outcomes are verified with STUB agents offline. One LIVE Nebius API
rehearsal on 26 October 2026 completed the morning check and Arun's zero-balance
Close finale. Five of six initial suggestions matched; Meera showed Verify
payment with unresolved clarification claims instead of the expected Follow up.
All six balances matched. Use Lotus or Patel for the LIVE follow-up example and
Lotus for approval/copy. See reports/course-demo-live-rehearsal.md for the saved
observations and differences.

That rehearsal ran before the final frontend/full-regression pass and did not
exercise browser navigation, the refusal preview, approval/copy or the history
and comparison assertions. It is not qualification; no second rehearsal is
authorized. Future LIVE runs can differ in wording, order and findings. Money
rules, refusals and approval gates are enforced by code. Nothing is ever sent
to a customer. This is a fictional demonstration, not production use.
