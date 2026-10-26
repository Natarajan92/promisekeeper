"""Generate the compact course-demo upload pack and its independent expected results.

Six fictional Indian MSMEs, one INR invoice each, dated relative to an anchor day so
the owner can regenerate on the demo morning. No model, network, database or
credentials. Writes only the named files and never deletes anything.
"""
import argparse
import csv
from datetime import date, datetime, time, timedelta
from email.utils import format_datetime
import io
import json
from pathlib import Path
from zoneinfo import ZoneInfo

IST = ZoneInfo('Asia/Kolkata')
CUSTOMER_FIELDS = ['customer_id', 'customer_name', 'customer_alias', 'address']
INVOICE_FIELDS = ['invoice_id', 'customer_id', 'customer_name', 'customer_alias', 'address', 'amount', 'currency', 'issued_at', 'due_at']
BANK_FIELDS = ['Date', 'Description', 'Credit', 'Debit', 'Reference', 'Balance']
MONTHS = 'January February March April May June July August September October November December'.split()
DEFAULT_OUT = Path('docs/demo-import/course-demo')
KIND_LABEL = dict(whatsapp='WhatsApp message', customer_email='Customer email')
ACTION_LABEL = dict(FOLLOW_UP='Follow up', WAIT='Wait', VERIFY_PAYMENT='Verify payment', CLOSE='Close')


def rupees(minor):
    """Indian digit grouping for the presenter script, e.g. 2,50,500.00."""
    whole, paise = divmod(int(minor), 100)
    text = str(whole)
    if len(text) > 3:
        head, tail = text[:-3], text[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:]);head = head[:-2]
        text = ','.join([head, *groups, tail]) if head else ','.join([*groups, tail])
    return f'₹{text}.{paise:02d}'


def generate_course_demo(output: Path, as_of: date) -> dict:
    output = Path(output);files = {}

    def day(delta): return as_of + timedelta(days=delta)
    def iso(delta): return day(delta).isoformat()
    def long(delta):
        d = day(delta);return f'{d.day} {MONTHS[d.month - 1]} {d.year}'
    def stamp(delta, hour, minute=0): return datetime.combine(day(delta), time(hour, minute), IST)
    def table(path, fields, rows):
        stream = io.StringIO(newline='');writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(fields);writer.writerows(rows);files[path] = stream.getvalue()
    def whatsapp(path, sender, sent, lines):
        files[path] = f'Sender: {sender}\nSent: {sent.isoformat()}\n\n' + '\n'.join(lines) + '\n'
    def email(path, sender, sent, subject, lines):
        files[path] = (f'From: {sender}\nTo: owner@shreeganesh-prints.example\nDate: {format_datetime(sent)}\n'
                       f'Subject: {subject}\nContent-Type: text/plain; charset=utf-8\n\n' + '\n'.join(lines) + '\n')

    customers = [
        ['MEERA', 'Meera Textiles', 'Meera Tex', '14, Avinashi Road, Peelamedu, Coimbatore 641004'],
        ['ARUN', 'Arun Traders', 'Arun', '7, Netaji Subhash Road, Kolkata 700001'],
        ['SUNRISE', 'Sunrise Foods', 'Sunrise', '22, MIDC Industrial Area, Andheri East, Mumbai 400093'],
        ['KAVERI', 'Kaveri Packaging', 'Kaveri Pack', '5, Hebbal Industrial Area, Mysuru 570016'],
        ['LOTUS', 'Lotus Electricals', 'Lotus Elec', '31, Relief Road, Ahmedabad 380001'],
        ['PATEL', 'Patel Hardware', 'Patel HW', '9, Station Road, Vadodara 390002'],
    ]
    table('01-customers.csv', CUSTOMER_FIELDS, customers)
    names = {row[0]: row[1] for row in customers}
    invoices = [  # invoice, customer, face value (INR), issued, due
        ('MT-1001', 'MEERA', 60000, -40, -16),
        ('AT-1002', 'ARUN', 32500, -30, -10),
        ('SF-1003', 'SUNRISE', 40000, -25, -5),
        ('KP-1004', 'KAVERI', 75000, -32, -2),
        ('LE-1005', 'LOTUS', 80000, -39, -9),
        ('PH-1006', 'PATEL', 25000, -42, -12),
    ]
    table('02-invoices.csv', INVOICE_FIELDS,
          [[inv, cust, '', '', '', str(amount), 'INR', iso(issued), iso(due)] for inv, cust, amount, issued, due in invoices])

    # Bank profile: one debit row is skipped; no row names an invoice.
    opening = 150000
    bank = [  # delta, description, credit, debit, reference
        (-23, 'UPI MEERA TEXTILES', 12000, 0, 'UPI-552104'),
        (-15, 'BESCOM ELECTRICITY BILL', 0, 4500, 'DD-771020'),
        (-6, 'NEFT PATEL HW', 10000, 0, 'NEFT-304172'),
        (-3, 'NEFT SUNRISE FOODS', 40000, 0, 'NEFT-883107'),
    ]
    rows = [];balance = opening
    for delta, description, credit, debit, reference in bank:
        balance += credit - debit
        rows.append([iso(delta), description, f'{credit}.00' if credit else '', f'{debit}.00' if debit else '', reference, f'{balance}.00'])
    table('03-bank-statement.csv', BANK_FIELDS, rows)
    allocations = [
        dict(transaction_ref='UPI-552104', bank_description='UPI MEERA TEXTILES', invoice_id='MT-1001', amount='12000', hint_required=True,
             note='Partial payment; INR 48,000 remains.'),
        dict(transaction_ref='NEFT-883107', bank_description='NEFT SUNRISE FOODS', invoice_id='SF-1003', amount='40000', hint_required=True,
             note='Pays the invoice in full.'),
        dict(transaction_ref='NEFT-304172', bank_description='NEFT PATEL HW', invoice_id='PH-1006', amount='10000', hint_required=True,
             note='No invoice reference on the credit; match it by the Patel HW name hint. INR 15,000 remains.'),
    ]

    documents = [
        dict(path='04-messages/meera-whatsapp-hinglish.txt', kind='whatsapp', invoice_id='MT-1001', sender_role='CUSTOMER',
             story='Hinglish WhatsApp promise of INR 48,000 that has already passed.'),
        dict(path='04-messages/arun-payment-claim.eml', kind='customer_email', invoice_id='AT-1002', sender_role='CUSTOMER',
             story='Claims INR 32,500 was paid (UTR ARUN-T9); no matching bank credit yet.'),
        dict(path='04-messages/kaveri-promise.eml', kind='customer_email', invoice_id='KP-1004', sender_role='CUSTOMER',
             story='Polite email promising INR 75,000 next week, with greeting and signature.'),
        dict(path='04-messages/lotus-promise.eml', kind='customer_email', invoice_id='LE-1005', sender_role='CUSTOMER',
             story='Clear customer promise for INR 80,000; its date has passed. Main happy-path case for review, approval and later payment.'),
    ]
    whatsapp(documents[0]['path'], 'Meera Textiles accounts', stamp(-12, 10, 30),
             ['Namaste,', 'Invoice: MT-1001', f'Hum ₹48000 {long(-8)} ko payment kar denge.', 'Thank you,', 'Suresh Mehta', 'Meera Textiles'])
    email(documents[1]['path'], 'Arun Kumar <accounts@arun-traders.example>', stamp(-2, 11, 15), 'Payment for invoice AT-1002',
          ['Dear Sir,', '', f'For invoice AT-1002, we paid INR 32500 on {long(-3)}. UTR: ARUN-T9.', '',
           'Regards,', 'Arun Kumar', 'Arun Traders'])
    email(documents[2]['path'], 'Lakshmi Rao <accounts@kaveri-packaging.example>', stamp(-1, 16, 40), 'Invoice KP-1004',
          ['Dear Sir,', '', 'Hope you are doing well.', '', f'For invoice KP-1004, we will pay INR 75000 by {long(7)}.', '',
           'Thank you for your patience.', '', 'Warm regards,', 'Lakshmi Rao', 'Kaveri Packaging'])
    email(documents[3]['path'], 'Dev Shah <accounts@lotus-electricals.example>', stamp(-5, 14, 20), 'Payment for invoice LE-1005',
          ['Namaste,', '', f'For invoice LE-1005, we will pay INR 80000 by {long(-2)}.', '',
           'Thank you,', 'Dev Shah', 'Lotus Electricals'])
    refused = [dict(path='06-refused/patel-conditional.txt', kind='whatsapp', invoice_id='PH-1006', sender_role='CUSTOMER',
                    reason='Conditional wording ("if the goods are replaced") is not a firm promise; preview refuses it and nothing is saved.')]
    whatsapp(refused[0]['path'], 'Patel Hardware accounts', stamp(-4, 12), ['Hi,', 'Invoice: PH-1006', 'We will pay INR 15000 if the goods are replaced.'])

    # Independent credit extracts: omit running balances so either receipt can be
    # introduced later without claiming that it is a complete bank statement.
    table('05-later/payments-later.csv', BANK_FIELDS[:-1], [[iso(-3), 'NEFT ARUN TRADERS', '32500.00', '', 'ARUN-T9']])
    finale = dict(path='05-later/payments-later.csv', kind='payments', invoice_id='AT-1002', action='CLOSE', balance_minor='0',
                  allocations=[dict(transaction_ref='ARUN-T9', bank_description='NEFT ARUN TRADERS', invoice_id='AT-1002', amount='32500', hint_required=True,
                                    note='The claimed UTR now appears in the bank statement.')])
    table('05-later/lotus-payment.csv', BANK_FIELDS[:-1], [[iso(0), 'NEFT LOTUS ELECTRICALS', '80000.00', '', 'LOTUS-T9']])
    happy_path_finale=dict(path='05-later/lotus-payment.csv',kind='payments',invoice_id='LE-1005',action='CLOSE',balance_minor='0',
        allocations=[dict(transaction_ref='LOTUS-T9',bank_description='NEFT LOTUS ELECTRICALS',invoice_id='LE-1005',amount='80000',hint_required=True,
                          note='Later settled credit completes the happy path after owner-confirmed allocation.')])

    expected = [
        dict(invoice_id='MT-1001', customer_name=names['MEERA'], action='FOLLOW_UP', balance_minor='4800000',
             why=f'Hinglish promise for {long(-8)} has passed; INR 48,000 still open after the INR 12,000 part payment.'),
        dict(invoice_id='AT-1002', customer_name=names['ARUN'], action='VERIFY_PAYMENT', balance_minor='3250000',
             why='Customer says it paid (UTR ARUN-T9) but no matching bank credit is allocated yet.'),
        dict(invoice_id='SF-1003', customer_name=names['SUNRISE'], action='CLOSE', balance_minor='0',
             why='Full INR 40,000 bank credit allocated by the owner; closure still needs the owner\'s confirmation.'),
        dict(invoice_id='KP-1004', customer_name=names['KAVERI'], action='WAIT', balance_minor='7500000', promise_by=iso(7),
             why=f'Promise to pay INR 75,000 by {long(7)}; review again when that day ends.'),
        dict(invoice_id='LE-1005', customer_name=names['LOTUS'], action='FOLLOW_UP', balance_minor='8000000',
             why=f'Clear customer promise for {long(-2)} has passed; INR 80,000 remains. Review the supported reminder before using it.'),
        dict(invoice_id='PH-1006', customer_name=names['PATEL'], action='FOLLOW_UP', balance_minor='1500000',
             why='INR 10,000 part payment matched by hint; INR 15,000 overdue. The conditional message is refused, not imported.'),
    ]
    presentation=dict(
        scenarios=[
            dict(id='HAPPY_PATH',title='Happy path: supported follow-up to verified payment',customer_name='Lotus Electricals',invoice_id='LE-1005',
                 start_action='FOLLOW_UP',start_balance_minor='8000000',later_payment_path=happy_path_finale['path'],final_action='CLOSE',final_balance_minor='0',requires_owner_closure=True),
            dict(id='PAYMENT_VERIFICATION',title='Problematic payment evidence: claimed payment without a matching receipt',customer_name='Arun Traders',invoice_id='AT-1002',
                 start_action='VERIFY_PAYMENT',start_balance_minor='3250000',claim_reference='ARUN-T9',later_payment_path=finale['path'],final_action='CLOSE',final_balance_minor='0',requires_owner_closure=True),
        ],
        background_invoice_ids=['MT-1001','SF-1003','KP-1004','PH-1006'],
        initial_upload_files=['01-customers.csv','02-invoices.csv','03-bank-statement.csv',*[d['path'] for d in documents]],
        staged_receipt_files=[happy_path_finale['path'],finale['path']],
        presenter_guide='TWO-SCENARIOS.md',
    )
    manifest = dict(schema_version=1, as_of=as_of.isoformat(), fictional=True,
                    customers=[dict(zip(CUSTOMER_FIELDS, row)) for row in customers],
                    invoices=[dict(invoice_id=inv, customer_id=cust, amount=str(amount), issued_at=iso(issued), due_at=iso(due))
                              for inv, cust, amount, issued, due in invoices],
                    documents=documents, allocations=allocations, expected=expected, refused=refused, finale=finale,
                    happy_path_finale=happy_path_finale,presentation=presentation)
    manifest['files'] = sorted([*files, 'EXPECTED-RESULTS.json', 'START-HERE.md','TWO-SCENARIOS.md'])
    files['EXPECTED-RESULTS.json'] = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    files['START-HERE.md'] = _script(as_of, long, invoices, names, documents, allocations, expected, finale)
    files['TWO-SCENARIOS.md'] = _two_scenario_script(as_of,long,happy_path_finale,finale)
    for relative, content in files.items():
        target = output / relative;target.parent.mkdir(parents=True, exist_ok=True);target.write_bytes(content.encode('utf-8'))
    return manifest


def _script(as_of, long, invoices, names, documents, allocations, expected, finale):
    total = sum(amount for _, _, amount, _, _ in invoices) * 100
    open_after = sum(int(e['balance_minor']) for e in expected)
    face = {inv: amount * 100 for inv, _, amount, _, _ in invoices}
    by_invoice = {inv: cust for inv, cust, *_ in invoices}
    message_rows = '\n'.join(f"| `{d['path']}` | {KIND_LABEL[d['kind']]} | {d['invoice_id']} · {names[by_invoice[d['invoice_id']]]} | Customer (I checked the sender) |"
                             for d in documents)
    allocation_rows = '\n'.join(f"| {a['bank_description']} (`{a['transaction_ref']}`) | {a['invoice_id']} · {names[by_invoice[a['invoice_id']]]} | {a['amount']} | {a['note']} |"
                                for a in allocations)
    outcome_rows = '\n'.join(f"| {names[by_invoice[e['invoice_id']]]} | {e['invoice_id']} | {rupees(face[e['invoice_id']])} | {ACTION_LABEL[e['action']]} | {rupees(e['balance_minor'])} | {e['why']} |"
                             for e in expected)
    return f'''# Course demo pack - anchored to {as_of.isoformat()}

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
| 2 Invoices | `02-invoices.csv` | Invoices | - (six invoices, {rupees(total)} in total) | - |
| 3 Bank receipts | `03-bank-statement.csv` | Receipts / bank statement | - | - |
| 4 Customer messages | see the table below, one file at a time | | | |

Step 3 shows the bank-profile assumptions. The BESCOM electricity row is a debit and
is skipped on purpose. Credits are not allocated automatically.

| File | Kind | Target invoice | Sender role |
|---|---|---|---|
{message_rows}

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
{allocation_rows}

The "looks like" suggestions are hints from names only; you make the match.
Leave nothing else allocated. Skip the optional "Existing allocations" import.

## 5. Confirm and check (step 6)

Confirm ledger coverage for all six invoices through the displayed cutoff (your
assertion for these fictional records), then press **Start morning review**.

Expected after the morning check (verified offline with STUB agents):

| Customer | Invoice | Invoice value | Suggestion | Still to collect | Why |
|---|---|---:|---|---:|---|
{outcome_rows}

Still to collect: {rupees(open_after)} across the open invoices. Sunrise shows Close,
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
for example "{rupees(8000000)}".

## 7. Optional resolution within scenario 2 - the claimed payment arrives

1. Upload `{finale['path']}` in step 3 (Receipts / bank statement). It has the
   NEFT ARUN TRADERS credit with reference ARUN-T9 dated {long(-3)}.
2. In step 5 allocate ARUN-T9 to AT-1002 · Arun Traders for INR 32500.
3. In step 6 confirm coverage again (every new import makes the earlier
   coverage and approvals stale).
4. Open the Arun Traders case and press **Investigate case**. Expected: **Close**,
   still to collect {rupees(0)}, and the claim is now supported by the bank
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
'''


def _two_scenario_script(as_of,long,happy,problem):
    return f'''# Two customer stories - {as_of.isoformat()}

Prepare with `START-HERE.md`, load all six customers/invoices, the initial bank
statement and all four messages, match the three initial credits and confirm
coverage. Run **Start morning review**. Then narrate only the two stories below.

Keep `{happy['path']}` and `{problem['path']}` out of the initial upload.
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
   INR 80,000 invoice, its due date {long(-9)}, and the direct customer promise:
   "For invoice LE-1005, we will pay INR 80000 by {long(-2)}."
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
   `{happy['path']}`. It contains a settled INR 80,000 credit dated {long(0)}
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

**Story:** Arun says it paid INR 32,500 on {long(-3)} and provides **ARUN-T9**.
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
   `{problem['path']}` at **step 3**, explicitly allocate **ARUN-T9** to
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
'''


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat, default=datetime.now(IST).date())
    parser.add_argument('--out', type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    manifest = generate_course_demo(args.out, args.as_of)
    print(json.dumps(dict(as_of=manifest['as_of'], out=str(args.out), files=len(manifest['files']),
                          expected={e['invoice_id']: e['action'] for e in manifest['expected']})))


if __name__ == '__main__':
    main()
