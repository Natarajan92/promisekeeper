"""Upload-only intake exercises real API/storage, never provider/network access."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from test_common_api import HEADERS, app_for

from support.intake import CUSTOMERS, INVOICES, PAYMENTS, EMAIL, PROMISE, operation, preview, commit, workspace, overview, allocate


def test_preview_is_read_only_and_separate_inputs_create_actual_customer_invoices(tmp_path):
    with TestClient(app_for(tmp_path/'intake.sqlite'), base_url='http://127.0.0.1') as client:
        _, view = preview(client, 'customers', CUSTOMERS)
        assert view['rows'][0]['customer_name'] == 'Econcity Private Limited'
        assert client.get('/api/v1/demonstrations').json()['demonstrations'] == []
        did = workspace(client)
        data = overview(client, did)
        assert [c['invoice_id'] for c in data['cases']] == ['EC-101', 'EC-102']
        assert all(c['client'] == 'Econcity Private Limited' for c in data['cases'])
        assert all(not c['ledger_complete'] for c in data['cases'])
        assert data['payments'] == []
        assert data['customers'][0]['customer_id'] == 'ECON'
        assert client.get(f'/api/v1/demonstrations/{did}/cases').status_code == 200


def test_payments_are_independent_suggestions_never_allocate_fuzzy_customer_names(tmp_path):
    with TestClient(app_for(tmp_path/'match.sqlite'), base_url='http://127.0.0.1') as client:
        did = workspace(client)
        saved, command = commit(client, 'payments', PAYMENTS, did)
        data = overview(client, did)
        assert len(data['payments']) == 2
        assert data['payments'][0]['remaining_minor'] == '2500000'
        assert data['payments'][0]['allocations'] == []
        assert len(data['payments'][0]['candidates']) == 2
        assert all(c['reasons'] for c in data['payments'][0]['candidates'])
        replay = client.post('/api/v1/intake/commits', json=command, headers=HEADERS)
        assert replay.json() == saved
        commit(client, 'payments', PAYMENTS, did)
        assert len(overview(client, did)['payments']) == 2


def test_partial_and_split_allocations_are_exact_and_same_receipt_can_fund_same_invoice_twice(tmp_path):
    with TestClient(app_for(tmp_path/'allocation.sqlite'), base_url='http://127.0.0.1') as client:
        did = workspace(client);commit(client, 'payments', PAYMENTS, did)
        data = overview(client, did);payment = data['payments'][0]
        response, command = allocate(client, did, payment, data['cases'][0], '20000')
        assert response.status_code == 200, response.text
        assert client.post(f'/api/v1/demonstrations/{did}/intake/allocations', json=command, headers=HEADERS).json() == response.json()
        data = overview(client, did)
        response, _ = allocate(client, did, data['payments'][0], data['cases'][0], '5000')
        assert response.status_code == 200, response.text
        data = overview(client, did)
        assert data['payments'][0]['remaining_minor'] == '0'
        assert data['cases'][0]['allocated_minor'] == '2500000'
        assert len(data['payments'][0]['allocations']) == 2
        response, _ = allocate(client, did, data['payments'][0], data['cases'][1], '1')
        assert response.status_code == 409
        cid = data['cases'][0]['id']
        view = client.get(f'/api/v1/cases/{cid}', params={'demonstration_id':did}).json()
        refs = [e['data']['transaction_ref'] for e in view['evidence'] if e['kind']=='LEDGER']
        assert len(set(refs)) == 2
        review = operation(case_id=cid, expected_case_revision=view['case_revision'],
                           reviewed_through=data['as_of'], complete=True, confirm=True)
        checked = client.post(f'/api/v1/demonstrations/{did}/intake/ledger-reviews', json=review, headers=HEADERS)
        assert checked.status_code == 200, checked.text
        after = client.get(f'/api/v1/cases/{cid}', params={'demonstration_id':did}).json()
        assert after['financial_facts']['balance']['minor_units'] == '7500000'
        commit(client, 'payments', PAYMENTS.replace('ECON-T1','ECON-T9').splitlines()[0]+'\n'+PAYMENTS.replace('ECON-T1','ECON-T9').splitlines()[1]+'\n', did)
        assert not overview(client, did)['cases'][0]['ledger_complete']


def test_existing_allocation_export_reuses_links_only_on_confirmed_commit(tmp_path):
    with TestClient(app_for(tmp_path/'existing.sqlite'), base_url='http://127.0.0.1') as client:
        did = workspace(client);commit(client,'payments',PAYMENTS,did)
        content='transaction_ref,invoice_id,amount\nECON-T1,EC-101,25000\nECON-T2,EC-101,15000\n'
        _, view = preview(client,'allocations',content,did)
        assert not view['errors'];assert overview(client,did)['cases'][0]['allocated_minor']=='0'
        commit(client,'allocations',content,did)
        assert overview(client,did)['cases'][0]['allocated_minor']=='4000000'
        commit(client,'allocations',content,did)
        assert overview(client,did)['cases'][0]['allocated_minor']=='4000000'


@pytest.mark.parametrize('bad', [INVOICES.replace('100000','-1'), INVOICES.replace('INR','USD'),
    INVOICES.replace('2026-09-01','not-a-date'), INVOICES.replace('100000','1.234'),
    INVOICES.replace('EC-102','EC-101'), 'invoice_id,invoice_id\na,b\n'])
def test_malformed_invoice_upload_returns_row_errors_without_writes(tmp_path,bad):
    with TestClient(app_for(tmp_path/'invalid.sqlite'), base_url='http://127.0.0.1') as client:
        _, result = preview(client,'invoices',bad)
        assert result['errors']
        assert client.get('/api/v1/demonstrations').json()['demonstrations']==[]


def test_changed_preview_and_cross_workspace_allocation_cannot_mutate(tmp_path):
    with TestClient(app_for(tmp_path/'scope.sqlite'), base_url='http://127.0.0.1') as client:
        did=workspace(client);other=workspace(client)
        command, view=preview(client,'payments',PAYMENTS,did)
        commit(client,'payments',PAYMENTS.replace('ECON-T1','OTHER-T1'),did)
        command.update(confirmed_preview_hash=view['preview_hash'],confirm=True,fictional_data=True,settled_confirmed=True)
        assert client.post('/api/v1/intake/commits',json=command,headers=HEADERS).status_code==409
        a=overview(client,did);b=overview(client,other)
        response,_=allocate(client,other,a['payments'][0],b['cases'][0],'100')
        assert response.status_code==404
        assert overview(client,other)['payments']==[]


def test_communication_upload_extracts_quotes_but_never_verifies_payment(tmp_path):
    with TestClient(app_for(tmp_path/'documents.sqlite'), base_url='http://127.0.0.1') as client:
        did=workspace(client);cid=overview(client,did)['cases'][0]['id']
        _, view=preview(client,'remittance_email',EMAIL,did,case_id=cid)
        assert view['extraction']['candidates'][0]['kind']=='CLAIM'
        assert view['extraction']['candidates'][0]['amount_text']=='60000'
        assert view['extraction']['candidates'][0]['transaction_reference_text']=='ECON-T3'
        commit(client,'remittance_email',EMAIL,did,case_id=cid)
        commit(client,'whatsapp',PROMISE,did,case_id=cid)
        data=overview(client,did)
        assert data['payments']==[]
        assert len(data['documents'])==2
        case_view=client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()
        assert len([e for e in case_view['evidence'] if e['kind']=='MESSAGE'])==2
        assert case_view['commitment_anchors'] if 'commitment_anchors' in case_view else any(e['commitment_anchors'] for e in case_view['evidence'])
        original=client.get(f"/api/v1/demonstrations/{did}/intake/files/{data['documents'][0]['batch_id']}")
        assert original.status_code==200
        assert EMAIL in [d['content'] for d in [original.json()]] or PROMISE in original.json()['content']


@pytest.mark.parametrize('content',[
    'Sender: Econ accounts\nSent: 2026-10-20T10:00:00+05:30\nInvoice EC-101 is still under discussion.\nWe will pay INR 40000 for invoice EC-102 by 30 October 2026.\n',
    'Sender: Econ accounts\nSent: 2026-10-20T10:00:00+05:30\nWe cannot pay INR 40000 by 30 October 2026.\n',
    'Sender: Econ accounts\nSent: 2026-10-20T10:00:00+05:30\n'+'\n'.join(f'We will pay INR {i} by 30 October 2026.' for i in range(1,32)),
])
def test_unsupported_document_preview_prevents_wrong_promises_and_permanent_commit_failures(tmp_path,content):
    with TestClient(app_for(tmp_path/'document-boundaries.sqlite'),base_url='http://127.0.0.1') as client:
        did=workspace(client);cid=overview(client,did)['cases'][0]['id']
        command,view=preview(client,'whatsapp',content,did,case_id=cid)
        assert view['errors']
        command.update(confirmed_preview_hash=view['preview_hash'],confirm=True,fictional_data=True)
        rejected=client.post('/api/v1/intake/commits',json=command,headers=HEADERS)
        assert rejected.status_code==422
        assert overview(client,did)['documents']==[]


def test_unsupported_communication_requires_explicit_context_review_and_deletion_purges_uploads(tmp_path):
    with TestClient(app_for(tmp_path/'delete.sqlite'), base_url='http://127.0.0.1') as client:
        did=workspace(client);cid=overview(client,did)['cases'][0]['id']
        content='Sent: 2026-10-20T10:00:00+05:30\nPlease call our accountant about the project.\n'
        _,view=preview(client,'whatsapp',content,did,case_id=cid)
        assert view['errors']
        commit(client,'whatsapp',content,did,case_id=cid,context_only=True)
        fid=overview(client,did)['documents'][0]['batch_id']
        deleted=client.post(f'/api/v1/demonstrations/{did}/deletion',json=operation(confirmed_demonstration_id=did,confirm=True),headers=HEADERS)
        assert deleted.status_code==200,deleted.text
        assert client.get(f'/api/v1/demonstrations/{did}/intake/files/{fid}').status_code==404


def test_later_receipt_resolves_original_utr_claim_and_preserves_previous_result(tmp_path):
    from support.lifecycle import run
    app=app_for(tmp_path/'claim-resolution.sqlite')
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);commit(client,'payments',PAYMENTS,did)
        commit(client,'allocations','transaction_ref,invoice_id,amount\nECON-T1,EC-101,25000\nECON-T2,EC-101,15000\n',did)
        cid=overview(client,did)['cases'][0]['id']
        commit(client,'remittance_email',EMAIL,did,case_id=cid)
        def review():
            state=overview(client,did);current=next(c for c in state['cases'] if c['id']==cid)
            r=client.post(f'/api/v1/demonstrations/{did}/intake/ledger-reviews',json=operation(
                case_id=cid,expected_case_revision=current['case_revision'],reviewed_through=state['as_of'],complete=True,confirm=True),headers=HEADERS)
            assert r.status_code==200,r.text
        review();before=run(app.state.db,did,cid)['current_result']
        assert before['action']=='VERIFY_PAYMENT'
        assert before['financial_facts']['balance']['minor_units']=='6000000'
        later='transaction_ref,payer_name,amount,currency,paid_at,status\nECON-T3,Econ Private Limited,60000,INR,2026-10-22,SETTLED\n'
        commit(client,'payments',later,did)
        state=overview(client,did);payment=next(p for p in state['payments'] if p['transaction_ref']=='ECON-T3')
        allocated,_=allocate(client,did,payment,state['cases'][0],'60000')
        assert allocated.status_code==200,allocated.text
        review();after=run(app.state.db,did,cid)
        assert after['current_result']['claims'][0]['resolved'] is True
        assert after['current_result']['action']=='CLOSE'
        assert after['lifecycle']=='OPEN'
        saved=client.get(f"/api/v1/investigations/{before['investigation_id']}",params={'demonstration_id':did}).json()
        assert saved['result']==before
