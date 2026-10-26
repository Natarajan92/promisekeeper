"""Fictional upload fixtures and real API helpers."""
from uuid import uuid4
HEADERS = {"X-PromiseKeeper-Request": "1"}

CUSTOMERS = 'customer_id,customer_name,customer_alias,address\nECON,Econcity Private Limited,econ,"12 1st Gandhinagar KR Bangalore 560012"\n'
INVOICES = 'invoice_id,customer_id,customer_name,customer_alias,address,amount,currency,issued_at,due_at\nEC-101,ECON,,,,100000,INR,2026-09-01,2026-10-01\nEC-102,ECON,,,,40000,INR,2026-09-10,2026-10-10\n'
PAYMENTS = 'transaction_ref,payer_name,payer_alias,address,amount,currency,paid_at,invoice_reference,status\nECON-T1,Econ Private Limited,ECONC,"12 1st Gandhinagar KR PURAM Bangalore 560012",25000,INR,2026-10-15,,SETTLED\nECON-T2,Econ Private Limited,ECONC,,15000,INR,2026-10-20,,SETTLED\n'
EMAIL = 'From: accounts@econ.example\nDate: Thu, 22 Oct 2026 10:00:00 +0530\nSubject: Payment for EC-101\nContent-Type: text/plain; charset=utf-8\n\nWe paid INR 60000 on 22 October 2026. UTR: ECON-T3.\n'
PROMISE = 'Sender: Econ accounts\nSent: 2026-10-20T10:00:00+05:30\nWe will pay INR 60000 by 30 October 2026.\n'


def operation(**data):
    return dict(schema_version='1', operation_id=str(uuid4()), **data)


def preview(client, kind, content, did=None, **kwargs):
    if kind in {'whatsapp','customer_email','remittance_email'}:kwargs.setdefault('sender_role','CUSTOMER')
    command = operation(kind=kind, filename='sample.eml' if 'email' in kind else 'sample.csv',
                        content=content, demonstration_id=did, **kwargs)
    response = client.post('/api/v1/intake/previews', json=command, headers=HEADERS)
    assert response.status_code == 200, response.text
    return command, response.json()


def commit(client, kind, content, did=None, **kwargs):
    command, view = preview(client, kind, content, did, **kwargs)
    assert not view['errors'], view
    command.update(operation_id=str(uuid4()), confirmed_preview_hash=view['preview_hash'], confirm=True,
                   fictional_data=True, settled_confirmed=True)
    response = client.post('/api/v1/intake/commits', json=command, headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json(), command


def workspace(client):
    created, _ = commit(client, 'customers', CUSTOMERS)
    did = created['demonstration_id']
    commit(client, 'invoices', INVOICES, did)
    return did


def overview(client, did):
    response = client.get(f'/api/v1/demonstrations/{did}/intake')
    assert response.status_code == 200, response.text
    return response.json()


def allocate(client, did, payment, case, amount):
    command = operation(payment_id=payment['id'], case_id=case['id'], amount_text=amount,
                        expected_case_revision=case['case_revision'], confirm=True, settled_confirmed=True)
    return client.post(f'/api/v1/demonstrations/{did}/intake/allocations', json=command, headers=HEADERS), command
