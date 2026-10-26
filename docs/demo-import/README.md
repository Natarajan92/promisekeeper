# File-driven owner walkthrough

For the compact six-customer course demonstration, use
[course-demo/START-HERE.md](course-demo/START-HERE.md). It includes the command to
regenerate dates, all four recommendations, explicit allocations, the later
statement finale and the observed LIVE rehearsal caveat.

For the larger end-user rehearsal, extract [synthetic-demo-pack.zip](synthetic-demo-pack.zip)
and follow [START-HERE](synthetic-pack/START-HERE.md). It contains six invoices,
nine distinct receipts, paise/split allocations, separate communication, 36 deliberate
rejection challenges and three interpretation/context scenarios. See the
[observed results](../../reports/synthetic-end-user-pack.md). The simple walkthrough
below remains useful for a short introduction.

All companies, email addresses, invoices, messages and bank references here are
fictional. No source connection or provider call is needed. Use the local STUB app.
This is a local demonstration without authentication; do not upload customer data.

1. Open **Upload**, step 1 **Customers**, and upload `customers.csv`.
   Preview, inspect the records and explicitly confirm a new imported workspace.
2. In step 2 upload `invoices.csv` as Invoices into that workspace. It creates three actual
   invoice cases with the original September issue dates and October due dates.
3. In step 3 upload `payments-initial.csv` as Receipts / bank statement. Nothing is allocated
   automatically. Econcity / Econ / ECONC and KR / KR PURAM remain differences.
4. Open step 5 **Match payments**. If the accounting export already has allocations, upload `allocations.csv` as
   Existing allocations and explicitly confirm the settled-record assertion. This
   links only ACME-T1 to AD-201. For Econ, select EC-101 for ECON-T1 and allocate
   INR 25,000; select EC-101 for ECON-T2 and allocate INR 15,000. The allocated
   remainder is INR 60,000. You can allocate only part of a receipt and then assign
   its remaining amount to another invoice, or leave it unallocated.
5. In step 4 **Customer messages**, upload each communication independently, with the corresponding file type and
   target invoice. Review the exact quote, source date and extracted fields:
   - `remittance-email.eml` -> Remittance email / EC-101 (a claim, not bank proof).
   - `customer-promise.eml` -> Customer email / EC-102 (a future promise).
   - `customer-payment-claim.eml` -> Customer email / EC-101 (ECON-T3 missing initially).
   - `whatsapp-promise.txt` -> WhatsApp / AD-201 (expired promise).
   - `whatsapp-paid.txt` -> WhatsApp / EC-101 (the same unverified ECON-T3 claim).
6. In step 6 **Confirm & check**, confirm ledger coverage for the invoices through the displayed as-of cutoff.
   This is an owner assertion for the fictional records, not bank authentication.
   Choose **Start morning review**. EC-101 should ask for payment verification,
   EC-102 should wait until its promise boundary at the 25 October 2026 rehearsal date, and AD-201 should offer a follow-up
   for the INR 80,000 verified remainder. Open the exact source quotes and Review.
   Edit/save if needed and approve the exact saved draft; copy to the usual tool.
   Nothing is sent by this app.
7. Keep EC-101's first result. Import `payments-later.csv`, allocate ECON-T3's
   INR 60,000 to EC-101, and reconfirm coverage after the new import. Reinvestigate:
   zero remains, the claims are supported by the original bank reference and the
   recommendation can be CLOSE. Compare the historical original; explicitly confirm
   closure in Case actions. Refresh/restart preserves the separate files/history.

Each import is previewed and confirmed. Exact duplicates in the same workspace are
no-ops; conflicting IDs reject the whole import. Imported workspaces accept up to
six invoices and files up to 256 KiB/100 CSV rows. Document sources must fit 8,000
characters. INR and documented CSV profiles are demo limits; XLSX/PDF/OCR and
arbitrary column mapping are not implemented. Column names match without case or
surrounding spaces, in any order; an unknown column is refused by name. UTF-8 with or
without BOM, CRLF and empty spreadsheet rows (`,,,`, not counted toward the 100-row
limit) are accepted. CSV amounts are
plain numbers with international or Indian grouping (`48,000.50`, `1,20,000.00`; quote
cells that contain commas), optionally prefixed `INR`, `Rs.` or `₹` and suffixed `/-`.
CSV invoice/receipt dates are `YYYY-MM-DD` or ISO date-times with a timezone; emails
must be UTF-8 text/plain without base64/quoted-printable re-encoding of the payment
wording. Receipts also accept a bank profile:
`Date,Description,Credit` with optional `Debit,Reference,Currency,Balance`. Preview
shows ISO/day-first date and missing-currency assumptions. A lone `-` in a bank
Debit, Credit or Reference cell means empty; other values starting with `-` are
refused. Debit-only rows are explicitly skipped. Missing Reference creates a labeled BANK- source fingerprint,
not a UTR; identical real deposits need distinct bank references. Settlement remains
UNKNOWN until explicitly reviewed, and no invoice is allocated automatically.
If the same deposit appears once with a generated fingerprint and again with a
real reference, the overlapping import is rejected for review instead of adding
funds twice. Keep a consistent receipt export; use the already imported receipt
or rebuild the fictional workspace using stable bank references.
The offline text parser recognizes
explicit payment/promise wording; unsupported wording must be reviewed as context
and is not claimed to have been understood by a model. All data uses a visible
as-of clock, advanced by new imports; coverage must be reviewed again after updates.

Documents mentioning multiple invoices, more than 30 claims/promises, negative or
conditional payment wording, and payment questions are rejected during preview.
Choose who sent each communication before preview. Only a reviewed customer role
can supply a claim/promise; owner/third-party/unverified text can be supporting
context. Role review is an owner assertion, not authenticated identity. Use an
individual unambiguous source message. Currency tokens remain verbatim;
reviewed message notation `INR`, `Rs.` and `₹` is interpreted as INR in preview.
`next <weekday>` uses the strictly next occurrence after the source's local date
(same weekday means seven days later); review the displayed date before confirming.
Unsupported context remains
limited under the existing missing-extraction checks. A shared city or generic
company suffix alone does not suggest an unrelated customer.

Invoice `amount` is the original full invoice value, before the separately imported
allocations. Do not use an already-net outstanding balance as that face value.
Dates without a time in CSV use IST midnight. If a WhatsApp source has no Sent
header, the optional message-date field is explicitly in IST.

Supported promises include direct first-person English, explicit passive future
payments and bounded first-person Hinglish (for example `Hum INR 1000 2026-11-04
ko pay kar denge`). Conditions, reported speech and payment requests need
clarification. This is bounded offline parsing, not general message understanding.
Promise documents must contain supported direct statements and simple neutral
surrounding text. Conditional subjects, quoted history and unsupported prose are
refused; they are not silently dropped. Supported email subject titles are
`Invoice <id>`, `Promise`, `Payment`, or `Remittance`, with the latter three also
allowing `for invoice <id>`. Blank subjects are allowed. Split out the individual
unambiguous message when preview asks for clarification.

Workspaces created before sender review retain their originals and history, but
older unreviewed communication invalidates advice/approval. Create a new imported
workspace from those originals and review each sender. Future-issued outstanding
invoices and due dates before issue dates are rejected.
