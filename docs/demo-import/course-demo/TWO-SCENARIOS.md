# Two customer stories - 2026-10-26

Prepare with `START-HERE.md`, load all six customers/invoices, the initial bank
statement and all four messages, match the three initial credits and confirm
coverage. Run **Start morning review**. Then narrate only the two stories below.

Keep `05-later/lotus-payment.csv` and `05-later/payments-later.csv` out of the initial upload.
They are separate later credit extracts; they do not assert a running bank balance.

## Opening - 20 seconds

On **Dashboard**, say: "We uploaded the accounting records, bank receipts and
customer messages. The application builds an evidence trail and suggests the next
action. We will look at just two customers."

Initial reference total: INR 2,50,500.00 still to collect across six open invoices.
The other four customers remain background data. Do not expand their cases during
the main explanation.

## Scenario 1 - happy path: Lotus Electricals / LE-1005

**Story:** valid, unambiguous records lead from a supported follow-up through
owner review to a verified payment and explicit closure. Every step has usable
evidence and the collection is resolved correctly.

1. In **Cases**, open **Lotus Electricals**. In **Overview**, point to the
   INR 80,000 invoice, its due date 17 October 2026, and the direct customer promise:
   "For invoice LE-1005, we will pay INR 80000 by 24 October 2026."
   The promise day passed and no receipt is allocated: **Follow up**, INR 80,000.00.
2. Explain **What happened**, the quoted source and **Our suggestion**:
   "The next step is supported by the invoice, bank records and exact customer
   wording. The system has not invented a payment or sent a reminder."
3. On **Assistant**, select Lotus under **Case to follow**. Briefly show the
   extractor, payment rules, writing/safety steps and saved result. Return to
   **Approvals** and select Lotus's reminder.
4. Read the exact saved message. Choose **Approve exact saved version**, then
   **Copy approved message**. Say: "Approval applies to this exact version.
   Copying hands it to our communication tool; PromiseKeeper has sent nothing."
5. Introduce the later bank evidence: go to **Upload > step 3** and import
   `05-later/lotus-payment.csv`. It contains a settled INR 80,000 credit dated 26 October 2026
   with reference **LOTUS-T9**. This supplied receipt represents the next input;
   do not claim that copying a message automatically caused a payment.
6. In **step 5**, match LOTUS-T9 to **LE-1005** for **80000** and confirm the
   settled receipt/allocation. Suggestions alone never allocate money.
7. In **step 6**, reconfirm coverage for every invoice through the new cutoff.
   Reopen Lotus and choose **Investigate case**. Expected **Close**, INR 0.00
   still to collect. The lifecycle is still **OPEN** until you choose closure.
8. Choose **Review case closure**, check **Confirm closure of invoice LE-1005**,
   then **Confirm case closure**. Show **CLOSED**. In **History/Compare**, the
   earlier Follow up result and original approval remain inspectable.

One-line takeaway: "Correct evidence becomes a reviewed action, a reconciled
receipt and a traceable closed case, with owner confirmation at each decision."

## Scenario 2 - problematic payment evidence: Arun Traders / AT-1002

**Story:** Arun says it paid INR 32,500 on 23 October 2026 and provides **ARUN-T9**.
The initial statement contains no matching credit. The application highlights
this evidence gap for verification.

1. Open **Arun Traders**. Because the Lotus import refreshed the workspace,
   choose **Investigate case** again to show a current result, rather than
   presenting the earlier saved result as current.
2. Show the customer's original email, the invoice and the available bank
   evidence in **What happened/Evidence**. Point out that LOTUS-T9 belongs to
   Lotus and cannot substantiate Arun's ARUN-T9 claim.
3. Expected **Verify payment**, INR 32,500.00 recorded remainder awaiting
   verification. Read the unresolved
   claim/next-step explanation. Say: "A customer statement is not a verified
   bank receipt. The system flags the mismatch for investigation; it does not
   record settlement, demand a duplicate payment or close the case."
4. Show the guarded case action: closure is unavailable while this evidence
   remains unresolved. The evidence and earlier findings remain visible.
5. Optional resolution, still part of this same scenario: import
   `05-later/payments-later.csv` at **step 3**, explicitly allocate **ARUN-T9** to
   **AT-1002** for **32500** at **step 5**, reconfirm coverage at **step 6**,
   then investigate Arun again. Expected **Close**, INR 0.00, with the claim
   resolved. The case remains open until its separate owner-confirmed closure.
6. Use **History/Compare** to show **Verify payment -> Close**, including the
   new bank evidence. The older verification result is preserved. Lotus stays
   closed; Arun's new receipt does not reopen it automatically.

One-line takeaway: "When evidence disagrees, the application exposes the gap and
keeps money and closure guarded until matching proof is supplied."

## Presenter reference

| Checkpoint | Lotus remainder | Arun remainder | Overall still to collect |
|---|---:|---:|---:|
| Initial upload and reviewed allocations | INR 80,000.00 | INR 32,500.00 | INR 2,50,500.00 |
| After LOTUS-T9 is allocated and coverage reviewed | INR 0.00 | INR 32,500.00 | INR 1,70,500.00 |
| After optional ARUN-T9 allocation and coverage review | INR 0.00 | INR 0.00 | INR 1,38,000.00 |

Arun's initial INR 32,500 is a recorded remainder contested by the payment claim.
The Dashboard includes it with its disclosure for recorded, unverified amounts.

These are fictional offline/STUB expectations. No new LIVE qualification or human
acceptance is implied. The revised Lotus evidence is not covered by the older
LIVE rehearsal. If a LIVE run reports uncertainty, show the actual finding and
its source limitations. No customer message is sent by the application.
