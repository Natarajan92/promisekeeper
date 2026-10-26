"""Cross-input boundaries, atomic imports and persisted allocation provenance."""
from fastapi.testclient import TestClient
from promisekeeper.api.app import create_app
from promisekeeper.config import Settings
from support.intake import HEADERS, PAYMENTS, EMAIL, operation, preview, commit, workspace, overview, allocate


def app_for(path):
    return create_app(Settings('STUB','gpt-5.6-terra',path,None))


def test_invalid_allocation_batch_is_atomic_and_split_crosses_invoices(tmp_path):
    with TestClient(app_for(tmp_path/'split.sqlite'),base_url='http://127.0.0.1') as client:
        did=workspace(client);commit(client,'payments',PAYMENTS,did)
        bad='transaction_ref,invoice_id,amount\nECON-T1,EC-101,20000\nECON-T1,EC-102,10000\n'
        command,view=preview(client,'allocations',bad,did)
        assert view['errors']
        command.update(confirmed_preview_hash=view['preview_hash'],confirm=True,fictional_data=True,settled_confirmed=True)
        assert client.post('/api/v1/intake/commits',json=command,headers=HEADERS).status_code==422
        assert all(c['allocated_minor']=='0' for c in overview(client,did)['cases'])
        valid=bad.replace('10000','5000');commit(client,'allocations',valid,did)
        data=overview(client,did)
        assert [c['allocated_minor'] for c in data['cases']]==['2000000','500000']
        assert data['payments'][0]['remaining_minor']=='0'


def test_pending_receipt_and_stale_revision_cannot_change_money(tmp_path):
    with TestClient(app_for(tmp_path/'pending.sqlite'),base_url='http://127.0.0.1') as client:
        did=workspace(client);commit(client,'payments',PAYMENTS.replace('SETTLED','PENDING'),did)
        data=overview(client,did)
        response,_=allocate(client,did,data['payments'][0],data['cases'][0],'1')
        assert response.status_code==409
        assert response.json()['error']['code']=='PAYMENT_NOT_SETTLED'
        assert overview(client,did)['cases'][0]['allocated_minor']=='0'


def test_originals_are_scoped_and_restart_preserves_source_quotes(tmp_path):
    path=tmp_path/'restart.sqlite'
    with TestClient(app_for(path),base_url='http://127.0.0.1') as client:
        did=workspace(client);other=workspace(client);cid=overview(client,did)['cases'][0]['id']
        # Actual text, independent of filename or seeded candidate lookup.
        text=EMAIL.replace('60000','32123').replace('From:','X-Local-Note: fictional\nFrom:')
        _,request=commit(client,'customer_email',text,did,case_id=cid)
        data=overview(client,did);fid=data['documents'][0]['batch_id']
        assert client.get(f'/api/v1/demonstrations/{other}/intake/files/{fid}').status_code==404
        source=client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()['evidence']
        source=next(e for e in source if e['kind']=='MESSAGE')
        assert source['original_content']==text
        assert 'candidates' not in source['data']
    with TestClient(app_for(path),base_url='http://127.0.0.1') as client:
        assert client.get(f'/api/v1/demonstrations/{did}/intake/files/{fid}').json()['content']==text
        from support.lifecycle import run
        case=run(client.app.state.db,did,cid)
        assert case['current_result']['claims'][0]['resolved'] is False
        assert case['current_result']['action']=='VERIFY_PAYMENT'


def test_samples_are_allowlisted_and_changed_content_cannot_reuse_preview(tmp_path):
    with TestClient(app_for(tmp_path/'samples.sqlite'),base_url='http://127.0.0.1') as client:
        assert client.get('/api/v1/intake/samples/customers.csv').status_code==200
        assert client.get('/api/v1/intake/samples/unknown.csv').status_code==404
        did=workspace(client)
        command,view=preview(client,'payments',PAYMENTS,did)
        command.update(content=PAYMENTS.replace('25000','26000'),confirmed_preview_hash=view['preview_hash'],confirm=True,fictional_data=True)
        assert client.post('/api/v1/intake/commits',json=command,headers=HEADERS).status_code==409
        assert overview(client,did)['payments']==[]
