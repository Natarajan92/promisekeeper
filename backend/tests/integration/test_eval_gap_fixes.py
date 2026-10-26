"""Whole saved investigations for raw currency/date/language and role review."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient
import pytest
from promisekeeper.api.app import create_app
from promisekeeper.config import Settings
from support.intake import HEADERS,operation,workspace,overview,commit,preview
from support.lifecycle import run


def current_message(text):
    source=datetime.now(ZoneInfo('Asia/Kolkata'))-timedelta(days=1)
    return f'Sender: Econ accounts\nSent: {source.isoformat()}\n{text}\n'


@pytest.mark.parametrize('wording',[
    'We will pay Rs. 40000 by {date}.',
    'We will pay RS.40000 by {date}.',
    'We will pay \u20b940000 by {date}.',
    'We will pay inr 40000 by {date}.',
    'Payment of INR 40000 will be made by {date}.',
    'Hum INR 40000 {iso} ko pay kar denge.',
    'We will pay INR 40000 by next Friday.',
])
def test_reviewed_supported_messages_reach_complete_wait_without_changing_money(tmp_path,wording):
    today=datetime.now(ZoneInfo('Asia/Kolkata'));future=today+timedelta(days=10)
    text=wording.format(date=f'{future.day} {future:%B %Y}',iso=future.date().isoformat())
    app=create_app(Settings('STUB','scripted',tmp_path/'reviewed.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);cid=overview(client,did)['cases'][1]['id']
        commit(client,'whatsapp',current_message(text),did,case_id=cid,sender_role='CUSTOMER')
        state=overview(client,did);row=next(c for c in state['cases'] if c['id']==cid)
        response=client.post(f'/api/v1/demonstrations/{did}/intake/ledger-reviews',headers=HEADERS,
            json=operation(case_id=cid,expected_case_revision=row['case_revision'],reviewed_through=state['as_of'],complete=True,confirm=True))
        assert response.status_code==200,response.text
        view=run(app.state.db,did,cid);result=view['current_result']
        assert result['status']=='COMPLETE' and result['action']=='WAIT'
        assert result['financial_facts']['balance']==dict(currency='INR',minor_units='4000000')
        assert view['lifecycle']=='OPEN' and view['draft_reviews']==[]


def test_api_does_not_default_an_unknown_sender_to_customer(tmp_path):
    app=create_app(Settings('STUB','scripted',tmp_path/'unknown.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);cid=overview(client,did)['cases'][0]['id']
        body=operation(kind='whatsapp',filename='owner.txt',content=current_message('We will pay INR 1000 by tomorrow.'),
                       demonstration_id=did,case_id=cid)
        response=client.post('/api/v1/intake/previews',headers=HEADERS,json=body)
        assert response.status_code==200
        assert response.json()['errors']
        assert not overview(client,did)['documents']


def test_legacy_import_receipts_replay_after_sender_field_is_added(tmp_path):
    from promisekeeper.contracts.intake import IntakePreview
    from promisekeeper.application.intake import preview_import,commit_import
    app=create_app(Settings('STUB','scripted',tmp_path/'legacy-replay.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        old=IntakePreview.model_validate(operation(kind='customers',filename='old.csv',content='customer_id,customer_name\nOLD,Old Demo\n')).model_dump()
        old.pop('sender_role')
        p=preview_import(app.state.db,old)
        old.update(confirmed_preview_hash=p['preview_hash'],confirm=True,fictional_data=True,settled_confirmed=False)
        saved=commit_import(app.state.db,old)
        replay=client.post('/api/v1/intake/commits',headers=HEADERS,json=old)
        assert replay.status_code==200 and replay.json()==saved
        assert len(client.get('/api/v1/demonstrations').json()['demonstrations'])==1


def test_upgrade_invalidates_unreviewed_legacy_advice_and_preserves_history(tmp_path):
    from uuid import uuid4
    path=tmp_path/'legacy.sqlite'
    app=create_app(Settings('STUB','scripted',path,None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did=workspace(client);cid=overview(client,did)['cases'][0]['id']
        future=datetime.now(ZoneInfo('Asia/Kolkata'))+timedelta(days=10)
        commit(client,'whatsapp',current_message(f'We will pay INR 1000 by {future.date().isoformat()}.'),did,case_id=cid)
        state=overview(client,did);row=state['cases'][0]
        client.post(f'/api/v1/demonstrations/{did}/intake/ledger-reviews',headers=HEADERS,
            json=operation(case_id=cid,expected_case_revision=row['case_revision'],reviewed_through=state['as_of'],complete=True,confirm=True))
        old=run(app.state.db,did,cid)['current_result'];assert old['action']=='WAIT'
        # Recreate pre-upgrade document metadata in this isolated database.
        with app.state.db.transaction() as con:
            batch=con.execute('SELECT id FROM intake_batches WHERE demonstration_id=?',(did,)).fetchone()[0]
            con.execute('INSERT INTO intake_documents VALUES (?,?,?,?,?,?,?,?)',(str(uuid4()),did,cid,'whatsapp',batch,'legacy-content','{"candidates":[]}',datetime.now().astimezone().isoformat()))
            con.execute("DELETE FROM schema_migrations WHERE version='012_sender_review.sql'")
    with TestClient(create_app(Settings('STUB','scripted',path,None)),base_url='http://127.0.0.1') as client:
        view=client.get(f'/api/v1/cases/{cid}?demonstration_id={did}').json()
        assert view['current_result'] is None
        assert not view['allowed_commands']['start_investigation']['allowed']
        assert overview(client,did)['needs_sender_review']
        historical=client.get(f"/api/v1/investigations/{old['investigation_id']}?demonstration_id={did}").json()
        assert historical['result']==old
