"""Message-review recovery preserves exact sources and the explicit commit boundary."""
import pytest
from fastapi.testclient import TestClient
from test_common_api import HEADERS, app_for
from support.intake import commit, overview, preview

QUOTE='Hum ₹48000 18 October 2026 ko payment kar denge.'
BODY=f'Namaste,\nInvoice: MT-1001\n{QUOTE}\nThank you,\nSuresh Mehta\nMeera Textiles\n'


@pytest.mark.parametrize('kind',['customer_email','remittance_email','whatsapp'])
def test_context_conflict_can_be_repreviewed_and_committed_as_reviewed_payment_wording(tmp_path,kind):
    with TestClient(app_for(tmp_path/'message.sqlite'),base_url='http://127.0.0.1') as client:
        saved,_=commit(client,'invoices','invoice_id,customer_name,amount,currency,issued_at,due_at\nMT-1001,Meera Textiles,60000,INR,2026-10-01,2026-10-10\n')
        did=saved['demonstration_id'];cid=overview(client,did)['cases'][0]['id']
        headers='Sender: Meera Textiles accounts\nSent: 2026-10-14T10:30:00+05:30\n' if kind=='whatsapp' else 'From: Suresh <accounts@meera.example>\nDate: Wed, 14 Oct 2026 10:30:00 +0530\nSubject: Payment for invoice MT-1001\nContent-Type: text/plain; charset=utf-8\n'
        content=headers+'\n'+BODY
        command,blocked=preview(client,kind,content,did,case_id=cid,sender_role='CUSTOMER',context_only=True)
        assert blocked['errors'][0]['code']=='PAYMENT_REVIEW_REQUIRED'
        rejected=client.post('/api/v1/intake/commits',headers=HEADERS,json={**command,'confirm':True,'fictional_data':True,'confirmed_preview_hash':blocked['preview_hash']})
        assert rejected.status_code==422
        assert overview(client,did)['documents']==[]
        _,ready=preview(client,kind,content,did,case_id=cid,sender_role='CUSTOMER',context_only=False)
        assert ready['errors']==[]
        assert ready['extraction']['candidates'][0]['clause']==QUOTE
        assert ready['extraction']['candidates'][0]['interpreted_date']=='2026-10-18'
        assert overview(client,did)['documents']==[]
        commit(client,kind,content,did,case_id=cid,sender_role='CUSTOMER',context_only=False)
        state=overview(client,did)
        assert len(state['documents'])==1
        document=state['documents'][0]
        assert document['case_id']==cid
        assert document['extraction']['context_only'] is False
        original=client.get(f"/api/v1/demonstrations/{did}/intake/files/{document['batch_id']}").json()
        assert original['content']==content


def test_informational_message_requires_explicit_context_review(tmp_path):
    with TestClient(app_for(tmp_path/'context.sqlite'),base_url='http://127.0.0.1') as client:
        saved,_=commit(client,'invoices','invoice_id,customer_name,amount,currency,issued_at,due_at\nMT-1001,Meera Textiles,60000,INR,2026-10-01,2026-10-10\n')
        did=saved['demonstration_id'];cid=overview(client,did)['cases'][0]['id']
        content='Sender: Meera accounts\nSent: 2026-10-14T10:30:00+05:30\nPlease call our accountant about the project.\n'
        _,blocked=preview(client,'whatsapp',content,did,case_id=cid,sender_role='CUSTOMER')
        assert blocked['errors'][0]['code']=='CONTEXT_REVIEW_REQUIRED'
        commit(client,'whatsapp',content,did,case_id=cid,sender_role='CUSTOMER',context_only=True)
        extraction=overview(client,did)['documents'][0]['extraction']
        assert extraction['candidates']==[] and extraction['context_only']


@pytest.mark.parametrize('context_only',[False,True])
def test_qualified_payment_wording_has_no_review_mode_bypass(tmp_path,context_only):
    with TestClient(app_for(tmp_path/'qualified.sqlite'),base_url='http://127.0.0.1') as client:
        saved,_=commit(client,'invoices','invoice_id,customer_name,amount,currency,issued_at,due_at\nMT-1001,Meera Textiles,60000,INR,2026-10-01,2026-10-10\n')
        did=saved['demonstration_id'];cid=overview(client,did)['cases'][0]['id']
        content='Sender: Meera accounts\nSent: 2026-10-14T10:30:00+05:30\nWe will pay INR 48000 by 18 October 2026 after finance approval.\n'
        _,blocked=preview(client,'whatsapp',content,did,case_id=cid,sender_role='CUSTOMER',context_only=context_only)
        assert blocked['errors'] and not blocked['errors'][0].get('code')
        assert overview(client,did)['documents']==[]
