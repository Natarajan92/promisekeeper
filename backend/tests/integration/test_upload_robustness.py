"""End-to-end upload robustness through the real intake API (STUB, fictional data).

Every realistic variant has an independently specified outcome: either supported
with exact normalized values (paise, identifiers, dates, extracted fields), or
refused with a specific plain message, HTTP 422 on commit and nothing saved.
A crash, HTTP 500, wrong paise, silent drop or Python-internal message is a bug.
"""
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from promisekeeper.api.app import create_app
from promisekeeper.config import Settings
from support.intake import CUSTOMERS, HEADERS, commit, operation, overview, preview
from support.lifecycle import run

IST = ZoneInfo('Asia/Kolkata')
LEAKS = ('isoformat', 'traceback', 'invalid literal', 'unconverted data', 'does not match format',
         'nonetype', 'keyerror', 'universal-newline', 'new-line character')
INVOICE_HEAD = 'invoice_id,customer_id,amount,currency,issued_at,due_at\n'
MESSAGE_GROUPING = ('A quoted INR amount is not a plain number. Use digits with standard grouping, '
                    'for example 48000, 48,000.50 or 1,20,000; no amount was guessed.')


def past(days):
    return (datetime.now(IST) - timedelta(days=days)).date()


def client_for(tmp_path, name='robust.sqlite'):
    return TestClient(create_app(Settings('STUB', 'scripted', tmp_path / name, None)), base_url='http://127.0.0.1')


def text_of(view):
    return ' | '.join(e['message'] for e in view['errors'])


def demonstration_count(client):
    with client.app.state.db.connection() as con:
        return con.execute('SELECT count(*) FROM demonstrations').fetchone()[0]


def refused(client, kind, content, did, needle, **kwargs):
    before = overview(client, did) if did else demonstration_count(client)
    command, view = preview(client, kind, content, did, **kwargs)
    message = text_of(view)
    assert view['errors'], view
    assert needle.casefold() in message.casefold(), message
    assert not any(leak in message.casefold() for leak in LEAKS), message
    command.update(operation_id=str(uuid4()), confirmed_preview_hash=view['preview_hash'], confirm=True,
                   fictional_data=True, settled_confirmed=True)
    response = client.post('/api/v1/intake/commits', json=command, headers=HEADERS)
    assert response.status_code == 422, response.text
    assert (overview(client, did) if did else demonstration_count(client)) == before
    return view


def customers_workspace(client):
    saved, _ = commit(client, 'customers', CUSTOMERS)
    return saved['demonstration_id']


def coverage(client, did):
    for row in overview(client, did)['cases']:
        state = overview(client, did)
        response = client.post(f'/api/v1/demonstrations/{did}/intake/ledger-reviews',
                               json=operation(case_id=row['id'], expected_case_revision=row['case_revision'],
                                              reviewed_through=state['as_of'], complete=True, confirm=True), headers=HEADERS)
        assert response.status_code == 200, response.text


# --- CSV encoding and layout -------------------------------------------------------

LAYOUTS = {
    'utf8_bom': '﻿' + INVOICE_HEAD + 'EC-201,ECON,48000,INR,{issued},{due}\nEC-202,ECON,12000.50,INR,{issued},{due}\n',
    'crlf': (INVOICE_HEAD + 'EC-201,ECON,48000,INR,{issued},{due}\nEC-202,ECON,12000.50,INR,{issued},{due}\n').replace('\n', '\r\n'),
    'trailing_blank_lines': INVOICE_HEAD + 'EC-201,ECON,48000,INR,{issued},{due}\nEC-202,ECON,12000.50,INR,{issued},{due}\n\n\n\r\n',
    'excel_trailing_empty_rows': INVOICE_HEAD + 'EC-201,ECON,48000,INR,{issued},{due}\nEC-202,ECON,12000.50,INR,{issued},{due}\n,,,,,\n,,,,,\n',
    'header_case_and_order': 'Due_At,Issued_At,Currency,Amount,Customer_ID,Invoice_ID\n{due},{issued},INR,48000,ECON,EC-201\n{due},{issued},INR,12000.50,ECON,EC-202\n',
    'header_spaces_after_commas': 'invoice_id, customer_id, amount, currency, issued_at, due_at\nEC-201,ECON,48000,INR,{issued},{due}\nEC-202,ECON,12000.50,INR,{issued},{due}\n',
    'bom_crlf_quoted': ('﻿' + INVOICE_HEAD + 'EC-201,ECON,"48,000",INR,{issued},{due}\nEC-202,ECON,"12,000.50",INR,{issued},{due}\n').replace('\n', '\r\n'),
}


@pytest.mark.parametrize('layout', sorted(LAYOUTS))
def test_csv_layout_variants_import_exact_invoices(tmp_path, layout):
    content = LAYOUTS[layout].format(issued=past(30).isoformat(), due=past(5).isoformat())
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        _, view = preview(client, 'invoices', content, did)
        assert not view['errors'], view
        commit(client, 'invoices', content, did)
        cases = {c['invoice_id']: c for c in overview(client, did)['cases']}
        assert {k: c['invoice_minor'] for k, c in cases.items()} == {'EC-201': '4800000', 'EC-202': '1200050'}
        assert {c['client'] for c in cases.values()} == {'Econcity Private Limited'}


def test_quoted_addresses_with_commas_keep_the_exact_text(tmp_path):
    content = ('﻿customer_id,customer_name,customer_alias,address\r\n'
               'MT,"Meera Textiles, Pvt Ltd",meera,"No. 14, 2nd Cross, Gandhinagar, Bengaluru 560009"\r\n'
               'AT,Arun Traders,,"Shop 3, ""Market"" Road, Mysuru"\r\n')
    with client_for(tmp_path) as client:
        saved, _ = commit(client, 'customers', content)
        customers = {c['customer_id']: c for c in overview(client, saved['demonstration_id'])['customers']}
        assert customers['MT']['customer_name'] == 'Meera Textiles, Pvt Ltd'
        assert customers['MT']['address'] == 'No. 14, 2nd Cross, Gandhinagar, Bengaluru 560009'
        assert customers['AT']['address'] == 'Shop 3, "Market" Road, Mysuru'


def test_unknown_extra_column_is_refused_and_named(tmp_path):
    content = INVOICE_HEAD.replace('\n', ',notes\n') + f'EC-201,ECON,48000,INR,{past(30)},{past(5)},call Ravi\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', content, did, 'notes')


def test_missing_required_column_is_refused_and_named(tmp_path):
    content = 'invoice_id,customer_id,amount,issued_at,due_at\n' + f'EC-201,ECON,48000,{past(30)},{past(5)}\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', content, did, 'currency')


def test_unquoted_grouped_amount_explains_the_comma(tmp_path):
    content = INVOICE_HEAD + f'EC-201,ECON,48,000,INR,{past(30)},{past(5)}\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', content, did, 'quote')


# --- Amounts --------------------------------------------------------------------------

AMOUNTS = [
    ('48000', 4800000), ('48000.50', 4800050), ('48000.5', 4800050), ('"48,000"', 4800000),
    ('"1,20,000.00"', 12000000), ('"12,34,567.89"', 123456789), ('"1,234,567.89"', 123456789),
    ('"Rs. 48,000/-"', 4800000), ('"₹48,000"', 4800000), ('"₹ 1,20,000"', 12000000), ('INR 48000', 4800000),
    ('Rs.48000', 4800000), ('48000/-', 4800000),
]


@pytest.mark.parametrize('cell,minor', AMOUNTS)
def test_invoice_amount_spellings_normalize_to_exact_paise_end_to_end(tmp_path, cell, minor):
    content = INVOICE_HEAD + f'EC-201,ECON,{cell},INR,{past(30)},{past(5)}\n'
    receipt = ('transaction_ref,payer_name,amount,currency,paid_at,status\n'
               f'ECON-R1,Econcity Private Limited,{cell},INR,{past(3)},SETTLED\n')
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        commit(client, 'invoices', content, did)
        case = overview(client, did)['cases'][0]
        assert case['invoice_minor'] == str(minor)
        commit(client, 'payments', receipt, did)
        payment = overview(client, did)['payments'][0]
        assert payment['amount_minor'] == str(minor)
        # Allocate all but one rupee, then confirm the investigation balance is exact.
        allocation = f'transaction_ref,invoice_id,amount\nECON-R1,EC-201,{(minor - 100) // 100}.{(minor - 100) % 100:02d}\n'
        commit(client, 'allocations', allocation, did)
        coverage(client, did)
        view = run(client.app.state.db, did, case['id'])
        assert view['current_result']['financial_facts']['balance']['minor_units'] == '100'


@pytest.mark.parametrize('cell,needle', [
    ('"48,00,0"', 'plain number'), ('"60,00.00"', 'plain number'), ('48000.505', 'two decimal'),
    ('0', 'positive'), ('-48000', 'positive'), ('48 000', 'plain number'), ('USD 48000', 'plain number'),
    ('"$48,000"', 'plain number'), ('"Rs. 48,000/- only"', 'plain number'), ('1e5', 'plain number'),
])
def test_unsupported_amount_spellings_are_refused_plainly(tmp_path, cell, needle):
    content = INVOICE_HEAD + f'EC-201,ECON,{cell},INR,{past(30)},{past(5)}\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', content, did, needle)


def test_rupee_marker_with_non_inr_currency_column_is_refused(tmp_path):
    content = INVOICE_HEAD + f'EC-201,ECON,"₹48,000",USD,{past(30)},{past(5)}\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', content, did, 'INR')


# --- Dates ----------------------------------------------------------------------------

def test_iso_invoice_dates_are_ist_calendar_days(tmp_path):
    issued, due = past(30), past(5)
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        _, view = preview(client, 'invoices', INVOICE_HEAD + f'EC-201,ECON,48000,INR,{issued},{due}\n', did)
        assert not view['errors']
        assert view['rows'][0]['issued_at'] == f'{issued}T00:00:00+05:30'


@pytest.mark.parametrize('spelling', ['%d/%m/%Y', '%d-%m-%Y', '%d %b %Y', '%d.%m.%Y', '%m/%d/%Y'])
def test_non_iso_invoice_dates_are_refused_with_the_supported_format(tmp_path, spelling):
    issued = past(30).strftime(spelling)
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', INVOICE_HEAD + f'EC-201,ECON,48000,INR,{issued},{past(5)}\n', did, 'YYYY-MM-DD')


def test_future_issued_invoice_is_refused(tmp_path):
    future = (datetime.now(IST) + timedelta(days=3)).date()
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', INVOICE_HEAD + f'EC-201,ECON,48000,INR,{future},{future + timedelta(days=30)}\n',
                did, 'issued in the future')


# --- Bank statements ------------------------------------------------------------------

@pytest.mark.parametrize('spelling,supported', [
    ('%Y-%m-%d', True), ('%d/%m/%Y', True), ('%d-%m-%Y', False), ('%d %b %Y', False),
])
def test_bank_statement_date_spellings(tmp_path, spelling, supported):
    day = past(4)
    content = f'Date,Description,Credit,Reference\n{day.strftime(spelling)},NEFT ECONCITY,"48,000.00",UTR-1\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        if supported:
            commit(client, 'payments', content, did)
            payment = overview(client, did)['payments'][0]
            assert payment['paid_at'] == f'{day}T00:00:00+05:30' and payment['amount_minor'] == '4800000'
        else:
            refused(client, 'payments', content, did, 'DD/MM/YYYY')


def test_bank_statement_with_debit_only_row_and_missing_reference(tmp_path):
    day = past(4).isoformat()
    content = ('﻿Date,Description,Debit,Credit,Reference,Balance\r\n'
               f'{day},Office rent,"15,000.00",,RENT-1,"1,05,000.00"\r\n'
               f'{day},"NEFT, ECONCITY PVT LTD","",\"1,20,000.00\",,"2,25,000.00"\r\n'
               f'{day},UPI ARUN,,"Rs. 2,500/-",UPI-77,"2,27,500.00"\r\n\r\n')
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        _, view = preview(client, 'payments', content, did)
        assert not view['errors'], view
        assert any('Skipped row 2' in w for w in view['warnings'])
        assert any('not UTRs' in w for w in view['warnings'])
        commit(client, 'payments', content, did)
        payments = overview(client, did)['payments']
        assert [(p['payer_name'], p['amount_minor'], p['status']) for p in payments] == [
            ('NEFT, ECONCITY PVT LTD', '12000000', 'UNKNOWN'), ('UPI ARUN', '250000', 'UNKNOWN')]
        assert payments[0]['transaction_ref'].startswith('BANK-') and payments[1]['transaction_ref'] == 'UPI-77'
        assert all(p['allocations'] == [] for p in payments)


def test_bank_statement_with_only_debits_is_refused(tmp_path):
    content = f'Date,Description,Credit,Debit\n{past(4)},Office rent,,15000\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'payments', content, did, 'No positive bank credits')


# --- Duplicates and limits -----------------------------------------------------------

def test_duplicate_reupload_of_each_file_is_a_noop(tmp_path):
    invoices = INVOICE_HEAD + f'EC-201,ECON,48000,INR,{past(30)},{past(5)}\n'
    receipts = f'Date,Description,Credit\n{past(4)},NEFT ECONCITY,48000\n'
    message = ('From: accounts@econcity.example\nDate: ' + past(2).strftime('%a, %d %b %Y') + ' 10:00:00 +0530\n'
               'Subject: Invoice EC-201\n\nWe will pay INR 48000 by 30 November 2026.\n')
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        commit(client, 'invoices', invoices, did)
        cid = overview(client, did)['cases'][0]['id']
        commit(client, 'payments', receipts, did)
        commit(client, 'customer_email', message, did, case_id=cid)
        before = overview(client, did)
        for kind, content, extra in [('customers', CUSTOMERS, {}), ('invoices', invoices, {}), ('payments', receipts, {}),
                                     ('customer_email', message, {'case_id': cid})]:
            saved, _ = commit(client, kind, content, did, **extra)
            assert saved['receipt']['outcome'] == 'UNCHANGED' and saved['imported'] == 0, saved
        assert overview(client, did) == before


def test_seventh_invoice_is_refused_by_the_workspace_limit(tmp_path):
    rows = ''.join(f'EC-{n},ECON,1000,INR,{past(30)},{past(5)}\n' for n in range(301, 307))
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        commit(client, 'invoices', INVOICE_HEAD + rows, did)
        refused(client, 'invoices', INVOICE_HEAD + f'EC-307,ECON,1000,INR,{past(30)},{past(5)}\n', did, 'up to six invoices')
        assert len(overview(client, did)['cases']) == 6


def test_seven_invoices_in_one_file_are_refused(tmp_path):
    rows = ''.join(f'EC-{n},ECON,1000,INR,{past(30)},{past(5)}\n' for n in range(301, 308))
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', INVOICE_HEAD + rows, did, 'up to six invoices')


# --- Communications ------------------------------------------------------------------

def invoice_case(client):
    did = customers_workspace(client)
    commit(client, 'invoices', INVOICE_HEAD + f'EC-201,ECON,48000,INR,{past(30)},{past(5)}\n', did)
    return did, overview(client, did)['cases'][0]['id']


def email(body, *, subject='Invoice EC-201', headers='Content-Type: text/plain; charset=utf-8\n', newline='\n'):
    date = past(2).strftime('%a, %d %b %Y') + ' 10:00:00 +0530'
    text = f'From: Ravi Kumar <accounts@econcity.example>\nDate: {date}\nSubject: {subject}\n{headers}\n{body}'
    return text.replace('\n', newline)


SUPPORTED_MESSAGES = {
    'email_signature': ('customer_email', email('Hi team,\n\nWe will pay INR 48000 by 30 November 2026.\n\nThanks,\nRavi Kumar\nEconcity Accounts\n'),
                        dict(kind='COMMITMENT', amount_text='48000', currency_text='INR', date_text='30 November 2026')),
    'email_crlf': ('customer_email', email('Dear Sir,\n\nWe will pay Rs. 48000 by 30 November 2026.\n\nRegards,\nRavi\n', newline='\r\n'),
                   dict(kind='COMMITMENT', amount_text='48000', currency_text='Rs.', date_text='30 November 2026')),
    'email_plain_and_different_html_alternative': ('customer_email', email(
        '--b1\nContent-Type: text/plain; charset=utf-8\n\nWe will pay INR 48000 by 30 November 2026.\n'
        '--b1\nContent-Type: text/html; charset=utf-8\n\n<p>Payment plan attached.</p>\n--b1--\n',
        headers='MIME-Version: 1.0\nContent-Type: multipart/alternative; boundary="b1"\n'),
        dict(kind='COMMITMENT', amount_text='48000', currency_text='INR', date_text='30 November 2026')),
    'email_rupee_symbol': ('customer_email', email('We will pay ₹48,000 by 30 November 2026.\n'),
                           dict(kind='COMMITMENT', amount_text='48,000', currency_text='₹', date_text='30 November 2026')),
    'email_indian_grouped_amount': ('customer_email', email('We will pay ₹1,20,000 by 30 November 2026.\n\nRegards,\nRavi Kumar\n'),
                                    dict(kind='COMMITMENT', amount_text='1,20,000', currency_text='₹', date_text='30 November 2026')),
    'remittance_claim': ('remittance_email', email('We paid INR 48000 on ' + past(3).strftime('%d %B %Y').lstrip('0') + '. UTR: NEFT123.\n',
                                                   subject='Remittance for invoice EC-201'),
                         dict(kind='CLAIM', amount_text='48000', currency_text='INR', transaction_reference_text='NEFT123')),
    'whatsapp_hinglish': ('whatsapp', 'Sender: Ravi (Econcity)\nSent: ' + past(2).isoformat() + 'T10:00:00+05:30\n'
                          'Namaste ji\nHum ₹48000 2026-11-30 ko payment kar denge.\nThank you\n',
                          dict(kind='COMMITMENT', amount_text='48000', currency_text='₹', date_text='2026-11-30')),
    'whatsapp_crlf_english': ('whatsapp', ('Sender: Ravi\nSent: ' + past(2).isoformat() + 'T10:00:00+05:30\n'
                              'We will pay ₹48000 by 30 November 2026.\n').replace('\n', '\r\n'),
                              dict(kind='COMMITMENT', amount_text='48000', currency_text='₹', date_text='30 November 2026')),
}


@pytest.mark.parametrize('name', sorted(SUPPORTED_MESSAGES))
def test_supported_communications_extract_exact_fields(tmp_path, name):
    kind, content, want = SUPPORTED_MESSAGES[name]
    with client_for(tmp_path) as client:
        did, cid = invoice_case(client)
        _, view = preview(client, kind, content, did, case_id=cid)
        assert not view['errors'], view
        [candidate] = view['extraction']['candidates']
        assert {k: candidate.get(k) for k in want} == want
        assert candidate['interpreted_currency'] == 'INR'
        commit(client, kind, content, did, case_id=cid)
        evidence = client.get(f'/api/v1/cases/{cid}', params={'demonstration_id': did}).json()['evidence']
        assert any(e['kind'] == 'MESSAGE' and e['original_content'] == content for e in evidence)


@pytest.mark.parametrize('kind,content,needle', [
    ('customer_email', email('<p>We will pay INR 48000 by 30 November 2026.</p>\n', headers='Content-Type: text/html; charset=utf-8\n'),
     'text/plain'),
    ('customer_email', email('--b1\nContent-Type: text/html\n\n<p>We will pay INR 48000 by 30 November 2026.</p>\n--b1--\n',
                             headers='MIME-Version: 1.0\nContent-Type: multipart/alternative; boundary="b1"\n'), 'text/plain'),
    ('customer_email', email('V2Ugd2lsbCBwYXkgSU5SIDQ4MDAwIGJ5IDMwIE5vdmVtYmVyIDIwMjYuCg==\n',
                             headers='Content-Type: text/plain; charset=utf-8\nContent-Transfer-Encoding: base64\n'), 'encoded'),
    ('customer_email', email('We will pay INR 48000 by 30 November 2026 if the goods arrive.\n'), 'conditional'),
    ('customer_email', email('We will pay INR 48000 by 30 November 2026.\n\nThanks,\nRavi, if possible\n'), 'conditional'),
    ('customer_email', 'Subject: Invoice EC-201\n\nWe will pay INR 48000 by 30 November 2026.\n', 'From and Date'),
    ('customer_email', email('--b1\nContent-Type: text/plain; charset=utf-8\n\nWe will pay INR 48000 by 30 November 2026.\n'
                             '--b1\nContent-Type: text/html; charset=utf-8\n\n<p>We will pay INR 48000 by 30 November 2026.</p>\n--b1--\n',
                             headers='MIME-Version: 1.0\nContent-Type: multipart/alternative; boundary="b1"\n'), 'HTML'),
    ('customer_email', email('We will pay ₹48000 by 30 November 2026.\n', headers='Content-Type: text/plain; charset=windows-1252\n'), 'UTF-8'),
    ('customer_email', email('Invoice unpaid\nWe will pay INR 48000 by 30 November 2026.\n'), 'conditional'),
    ('customer_email', email('Invoice: EC-201\nWe will pay INR 48000 by 30 November 2026.\nInvoice disputed\n'), 'prose'),
    # A raw WhatsApp chat export line is not the documented Sender/Sent format.
    ('whatsapp', '20/10/2026, 10:15 - Ravi: Hum ₹48000 2026-11-30 ko payment kar denge.\n', 'date with timezone'),
    ('whatsapp', 'Sender: Ravi\nSent: ' + past(2).isoformat() + 'T10:00:00+05:30\n'
                 '20/10/2026, 10:15 - Ravi: Hum ₹48000 2026-11-30 ko payment kar denge.\n', 'No supported payment'),
    ('whatsapp', 'Sender: Ravi\nSent: ' + past(2).isoformat() + 'T10:00:00+05:30\nAgar maal mil gaya to hum ₹48000 2026-11-30 ko payment kar denge.\n',
     'conditional'),
    *[('whatsapp', 'Sender: Ravi\nSent: ' + past(2).isoformat() + f'T10:00:00+05:30\nWe will pay {amount} by 30 November 2026.\n', MESSAGE_GROUPING)
      for amount in ('₹1,20,00', '₹12,00', 'INR 48,00,0', 'Rs. 1,2,3')],
    ('customer_email', email('We will pay ₹1,20,00 by 30 November 2026.\n'), MESSAGE_GROUPING),
    ('whatsapp', 'Sender: Ravi\nSent: ' + past(2).isoformat() + 'T10:00:00+05:30\nWe will pay ₹48000.505 by 30 November 2026.\n',
     'A quoted INR amount has more than two decimal places; paise cannot be rounded and no amount was selected.'),
])
def test_unsupported_communications_are_refused_plainly(tmp_path, kind, content, needle):
    with client_for(tmp_path) as client:
        did, cid = invoice_case(client)
        refused(client, kind, content, did, needle, case_id=cid)


# --- Review fix round 1 ------------------------------------------------------------

def test_lone_dash_bank_cells_mean_empty(tmp_path):
    # Indian bank exports often print "-" for an empty Debit/Credit/Reference cell.
    day = past(4).isoformat()
    content = ('Date,Description,Debit,Credit,Reference,Balance\n'
               f'{day},Office rent,"15,000.00",-,RENT-1,"1,05,000.00"\n'
               f'{day},NEFT ECONCITY, - ,"48,000.00",-,"1,53,000.00"\n')
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        _, view = preview(client, 'payments', content, did)
        assert not view['errors'], view
        assert any('Skipped row 2' in w for w in view['warnings'])
        commit(client, 'payments', content, did)
        [payment] = overview(client, did)['payments']
        assert payment['amount_minor'] == '4800000' and payment['transaction_ref'].startswith('BANK-')


@pytest.mark.parametrize('cell', ['--', '-48000', '- 48000'])
def test_other_dash_bank_cells_are_refused_plainly(tmp_path, cell):
    content = f'Date,Description,Credit\n{past(4)},NEFT ECONCITY,{cell}\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'payments', content, did, 'Bank credit')


def customer_rows(count):
    return ''.join(f'C{n:03d},Customer {n}\n' for n in range(count))


@pytest.mark.parametrize('count,ok', [(100, True), (101, False)])
def test_blank_rows_do_not_count_toward_the_100_row_limit(tmp_path, count, ok):
    content = 'customer_id,customer_name\n' + ',\n' * 30 + customer_rows(count) + ',\n\n,\n' * 10
    with client_for(tmp_path) as client:
        if ok:
            saved, _ = commit(client, 'customers', content)
            assert len(overview(client, saved['demonstration_id'])['customers']) == 100
        else:
            refused(client, 'customers', content, None, 'Maximum 100 data rows')


@pytest.mark.parametrize('count,ok', [(100, True), (101, False)])
def test_blank_bank_rows_do_not_count_toward_the_100_row_limit(tmp_path, count, ok):
    day = past(4).isoformat()
    rows = ''.join(f'{day},Payer {n},{n + 1},REF-{n}\n' for n in range(count))
    content = 'Date,Description,Credit,Reference\n' + ',,,\n' * 30 + rows + ',,,\n' * 10
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        if ok:
            commit(client, 'payments', content, did)
            assert len(overview(client, did)['payments']) == 100
        else:
            refused(client, 'payments', content, did, 'Maximum 100 data rows')


def test_header_repeated_after_case_folding_is_refused(tmp_path):
    content = 'invoice_id,customer_id,Amount,amount,currency,issued_at,due_at\n' + f'EC-201,ECON,48000,48000,INR,{past(30)},{past(5)}\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        refused(client, 'invoices', content, did, 'repeated: amount')


def test_partly_blank_row_is_reported_not_skipped(tmp_path):
    content = INVOICE_HEAD + f'EC-201,ECON,48000,INR,{past(30)},{past(5)}\nEC-203,,,,,\n'
    with client_for(tmp_path) as client:
        did = customers_workspace(client)
        view = refused(client, 'invoices', content, did, 'customer')
        assert [e['row'] for e in view['errors']] == [3]
