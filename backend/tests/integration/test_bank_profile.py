"""Raw statements are evidence, not automatic customer links or settlement."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
import pytest
from promisekeeper.api.app import create_app
from promisekeeper.config import Settings
from support.intake import workspace,overview,commit,preview,HEADERS


def yesterday():return (datetime.now(ZoneInfo('Asia/Kolkata'))-timedelta(days=2)).date()


def test_bank_profile_preserves_originals_explains_assumptions_and_deduplicates_overlap(tmp_path):
    app=create_app(Settings('STUB','scripted',tmp_path/'bank.sqlite',None))
    date=yesterday().isoformat()
    text=f'Date,Description,Credit,Debit,Balance\n{date},Econ payment,400.25,,9000\n{date},Office expense,,20,8980\n'
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);before=overview(client,did)
        _,p=preview(client,'payments',text,did)
        assert not p['errors']
        assert len(p['rows'])==1 and p['rows'][0]['status']=='UNKNOWN'
        assert p['rows'][0]['reference_origin']=='GENERATED_FINGERPRINT'
        assert any('INR' in w for w in p['warnings'])
        assert any('Skipped' in w for w in p['warnings'])
        assert any('identical' in w for w in p['warnings'])
        assert overview(client,did)==before
        saved,_=commit(client,'payments',text,did)
        state=overview(client,did);payment=state['payments'][0]
        assert payment['amount_minor']=='40025' and payment['allocations']==[]
        assert payment['status']=='UNKNOWN' and payment['transaction_ref'].startswith('BANK-')
        # Re-export has different balance/order/number spelling, same deposit.
        overlap=f'Date,Description,Credit,Currency\n{date},Econ payment,400.250,INR\n'
        _,p=preview(client,'payments',overlap,did);assert p['errors'] # never round invalid precision
        overlap=overlap.replace('400.250','400.25')
        commit(client,'payments',overlap,did)
        assert len(overview(client,did)['payments'])==1
        original=client.get(f"/api/v1/demonstrations/{did}/intake/files/{payment['batch_id']}").json()
        assert original['content']==text


def test_bank_reference_keeps_identical_real_receipts_distinct_and_day_first_is_explicit(tmp_path):
    app=create_app(Settings('STUB','scripted',tmp_path/'reference.sqlite',None))
    day=yesterday().strftime('%d/%m/%Y')
    text=f'Date,Description,Credit,Reference,Currency\n{day},Same payer,100,REAL-1,INR\n{day},Same payer,100,REAL-2,INR\n'
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);_,p=preview(client,'payments',text,did)
        assert not p['errors'];assert any('DD/MM/YYYY' in w for w in p['warnings'])
        commit(client,'payments',text,did)
        assert {p['transaction_ref'] for p in overview(client,did)['payments']}=={'REAL-1','REAL-2'}


@pytest.mark.parametrize('row',[
    '{date},Econ,100,1,INR',
    '{date},Econ,-100,,INR',
    '{date},Econ,100.001,,INR',
    '{date},Econ,100,,USD',
    '2099-01-01,Econ,100,,INR',
    '10-11-2026,Econ,100,,INR',
])
def test_invalid_bank_rows_reject_the_entire_batch_without_writes(tmp_path,row):
    app=create_app(Settings('STUB','scripted',tmp_path/'bad.sqlite',None))
    text='Date,Description,Credit,Debit,Currency\n{date},Valid,10,,INR\n'+row+'\n'
    text=text.format(date=yesterday().isoformat())
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);before=overview(client,did);command,p=preview(client,'payments',text,did)
        assert p['errors']
        command.update(confirmed_preview_hash=p['preview_hash'],confirm=True,fictional_data=True)
        assert client.post('/api/v1/intake/commits',json=command,headers=HEADERS).status_code==422
        assert overview(client,did)==before


@pytest.mark.parametrize('issued,due',[('2099-01-01','2099-02-01'),('2026-09-20','2026-09-19')])
def test_outstanding_invoice_dates_must_be_real_and_ordered(tmp_path,issued,due):
    app=create_app(Settings('STUB','scripted',tmp_path/'invoice-dates.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);before=overview(client,did)
        _,p=preview(client,'invoices',f'invoice_id,customer_id,amount,currency,issued_at,due_at\nEC-103,ECON,100,INR,{issued},{due}\n',did)
        assert p['errors'] and overview(client,did)==before


def test_calendar_due_date_includes_the_whole_issue_day(tmp_path):
    app=create_app(Settings('STUB','scripted',tmp_path/'same-day.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client)
        _,p=preview(client,'invoices','invoice_id,customer_id,amount,currency,issued_at,due_at\nEC-103,ECON,100,INR,2026-09-20T10:00:00+05:30,2026-09-20\n',did)
        assert not p['errors']


@pytest.mark.parametrize('order',['generated_then_reference','reference_then_generated','same_batch','canonical_then_generated'])
def test_generated_and_genuine_reference_overlap_needs_clarification(tmp_path,order):
    app=create_app(Settings('STUB','scripted',tmp_path/'overlap.sqlite',None));date=yesterday().isoformat()
    generated=f'Date,Description,Credit\n{date},Econ transfer,400\n'
    referenced=f'Date,Description,Credit,Reference\n{date},Econ transfer,400,REAL-123\n'
    canonical=f'transaction_ref,payer_name,amount,currency,paid_at\nREAL-123,Econ transfer,400,INR,{date}\n'
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client)
        if order=='same_batch':incoming=referenced+f'{date},Econ transfer,400,\n'
        else:
            first,incoming=(generated,referenced) if order=='generated_then_reference' else (canonical,generated) if order=='canonical_then_generated' else (referenced,generated)
            commit(client,'payments',first,did)
        before=overview(client,did);body,p=preview(client,'payments',incoming,did)
        assert p['errors'] and any('overlap' in e['message'].lower() for e in p['errors'])
        body.update(confirmed_preview_hash=p['preview_hash'],confirm=True,fictional_data=True)
        assert client.post('/api/v1/intake/commits',json=body,headers=HEADERS).status_code==422
        assert overview(client,did)==before
