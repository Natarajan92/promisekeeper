# Synthetic owner demo pack - 2026-10-25

Everything is fictional. Use the local STUB application. Extract the ZIP first;
upload individual CSV/EML/TXT files, never this README or EXPECTED-RESULTS.json.
That JSON is an independent test oracle, not an application import file.

Begin in a NEW imported workspace. If an imported copy is already selected, open
Import separate files and check Create a new imported workspace instead BEFORE
uploading 01-customers.csv. Existing copies and their records stay saved.

1. Import 01-customers.csv (UTF-8 BOM included), then 02-invoices.csv.
2. Import 03-receipts-initial.csv. Ten rows produce nine receipts, one duplicate.
   Even exact invoice hints do not allocate automatically. Compare Econcity/econ
   with Econ/ECONC and KR/KR PURAM; suggestions require an owner decision.
3. Import 03a-existing-allocations.csv after confirming settled allocations.
   The repeated KITE row is a duplicate. LOTUS is fully paid, KITE partly paid.
4. Manually confirm these allocations, one at a time:
   ECON-T1 -> ECON-101: 25000; ECON-T2 -> ECON-101: 15000;
   NOVA-T1 -> NOVA-401: 30000.10, then another 10000.15;
   NOVA-T1 -> NOVA-402: 5000.25. NOVA-T1 still has 20000 unallocated.
   Alternatively import 03b-owner-reviewed-allocations.csv after reviewing it.
   Use one method; both are not needed. Pending/reversed/unknown/unassigned
   receipts never reduce an invoice without a valid settled allocation.
5. Attach all six files from 04-messages to the invoice named in each filename/body.
   EML remittances use Remittance email, the future promise uses Customer email,
   TXT files use WhatsApp message. Read each exact quote before confirming.
6. Confirm ledger coverage through the displayed cutoff for all six invoices.
   This is your assertion for fictional records, not independent bank verification.
   The expected table assumes you have reviewed the unassigned deposits and ruled
   out further relevant allocations. If a deposit might belong to an invoice,
   leave coverage unchecked and investigate: the remainder stays unconfirmed and
   verification is required. The app cannot infer that missing relationship.
   Close the import panel and Start morning review.

| Invoice | Expected remainder (INR) | Action |
|---|---:|---|
| ECON-101 | 60,000.00 | Verify payment: ECON-T3 is missing |
| ECON-102 | 40,000.00 | Wait: promise due 1 November 2026 |
| KITE-201 | 80,000.00 | Follow up: promise expired 20 October 2026 |
| LOTUS-301 | 0.00 | Close recommendation; still OPEN until you confirm |
| NOVA-401 | 50,000.50 | Follow up; two pieces support the INR 40,000.25 claim |
| NOVA-402 | 5,000.25 | Follow up; INR 5,000.25 partial payment supported |

The total invoice remainder is INR 235,000.75. Original face values total
INR 410,001.25; allocations total INR 175,000.50. A large or excess bank receipt
alone must not lower that remainder. Re-uploading the same files changes nothing.
Open KITE's recommendation, edit/save if needed, approve its exact draft and copy.
Nothing is sent. Inspect LOTUS's closure evidence before explicitly closing it.

7. Import 05-later/receipts-later.csv, then explicitly allocate ECON-T3's 60000
   to ECON-101 (or review/import allocation-later.csv). Prior coverage/approval
   becomes stale. Reconfirm coverage and investigate ECON-101: zero/CLOSE, claims
   resolved, lifecycle still OPEN. The first VERIFY result stays in history.

## Challenge files

06-reject contains 36 deliberate failures. Preview one at a time in the
same six-invoice workspace. Expect an error, no Confirm import, no changed data.
It includes bad CSV, fractional paise, foreign currency, future receipts, duplicate
conflicts, too many rows/invoices, pending/reversed/over allocations, ambiguous
messages, deductions, HTML-only email and missing dates. Do not repair a challenge
file during the demo: its rejection is the intended successful outcome.

07-explore contains unsupported/unsafe evidence for separate disposable workspaces.
Create a fresh copy using customers/invoices before EACH exploration. Attach to
ECON-102; only supporting-context requires the explicit context-only checkbox.
Choose the reviewed customer sender role before previewing each communication.
Confirm coverage and investigate. Review the explicit INR interpretation and the
source-relative next-weekday date in preview. Active supported promises yield WAIT;
an expired source-relative promise yields FOLLOW_UP. Original words remain visible.
Supporting-context extraction must be LIMITED. Untrusted instructions must never change
money or close/approve/send anything. Read the observed-test report for results.

Dates are anchored to 2026-10-25. Regenerate on the actual demo day:

    backend/.venv/Scripts/python.exe -m promisekeeper.fixtures.synthetic_pack --output docs/demo-import/synthetic-pack --zip docs/demo-import/synthetic-demo-pack.zip

No real data, connections, credentials, provider calls, automatic sending or
production readiness are demonstrated. The application supports six invoices,
fixed INR CSV headers, 100 rows/file and bounded plain-text extraction.
