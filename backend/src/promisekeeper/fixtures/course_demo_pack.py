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
    ]
    whatsapp(documents[0]['path'], 'Meera Textiles accounts', stamp(-12, 10, 30),
             ['Namaste,', 'Invoice: MT-1001', f'Hum ₹48000 {long(-8)} ko payment kar denge.', 'Thank you,', 'Suresh Mehta', 'Meera Textiles'])
    email(documents[1]['path'], 'Arun Kumar <accounts@arun-traders.example>', stamp(-2, 11, 15), 'Payment for invoice AT-1002',
          ['Dear Sir,', '', f'For invoice AT-1002, we paid INR 32500 on {long(-3)}. UTR: ARUN-T9.', '',
           'Regards,', 'Arun Kumar', 'Arun Traders'])
    email(documents[2]['path'], 'Lakshmi Rao <accounts@kaveri-packaging.example>', stamp(-1, 16, 40), 'Invoice KP-1004',
          ['Dear Sir,', '', 'Hope you are doing well.', '', f'For invoice KP-1004, we will pay INR 75000 by {long(7)}.', '',
           'Thank you for your patience.', '', 'Warm regards,', 'Lakshmi Rao', 'Kaveri Packaging'])
    refused = [dict(path='06-refused/patel-conditional.txt', kind='whatsapp', invoice_id='PH-1006', sender_role='CUSTOMER',
                    reason='Conditional wording ("if the goods are replaced") is not a firm promise; preview refuses it and nothing is saved.')]
    whatsapp(refused[0]['path'], 'Patel Hardware accounts', stamp(-4, 12), ['Hi,', 'Invoice: PH-1006', 'We will pay INR 15000 if the goods are replaced.'])

    table('05-later/payments-later.csv', BANK_FIELDS, [[iso(-3), 'NEFT ARUN TRADERS', '32500.00', '', 'ARUN-T9', f'{balance + 32500}.00']])
    finale = dict(path='05-later/payments-later.csv', kind='payments', invoice_id='AT-1002', action='CLOSE', balance_minor='0',
                  allocations=[dict(transaction_ref='ARUN-T9', bank_description='NEFT ARUN TRADERS', invoice_id='AT-1002', amount='32500', hint_required=True,
                                    note='The claimed UTR now appears in the bank statement.')])

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
             why='Overdue, no payment and no message.'),
        dict(invoice_id='PH-1006', customer_name=names['PATEL'], action='FOLLOW_UP', balance_minor='1500000',
             why='INR 10,000 part payment matched by hint; INR 15,000 overdue. The conditional message is refused, not imported.'),
    ]
    manifest = dict(schema_version=1, as_of=as_of.isoformat(), fictional=True,
                    customers=[dict(zip(CUSTOMER_FIELDS, row)) for row in customers],
                    invoices=[dict(invoice_id=inv, customer_id=cust, amount=str(amount), issued_at=iso(issued), due_at=iso(due))
                              for inv, cust, amount, issued, due in invoices],
                    documents=documents, allocations=allocations, expected=expected, refused=refused, finale=finale)
    manifest['files'] = sorted([*files, 'EXPECTED-RESULTS.json', 'START-HERE.md'])
    files['EXPECTED-RESULTS.json'] = json.dumps(manifest, indent=2, ensure_ascii=False) + '\n'
    files['START-HERE.md'] = _script(as_of, long, invoices, names, documents, allocations, expected, finale)
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

**Safety refusal (show, do not import).** In step 4 preview
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
assertion for these fictional records), then press **Start morning check**.

Expected after the morning check (verified offline with STUB agents):

| Customer | Invoice | Invoice value | Suggestion | Still to collect | Why |
|---|---|---:|---|---:|---|
{outcome_rows}

Still to collect: {rupees(open_after)} across the open invoices. Sunrise shows Close,
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
for example "{rupees(8000000)}".

## 7. Finale - the claimed payment arrives

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
