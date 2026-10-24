from uuid import uuid4
from fastapi.testclient import TestClient
from test_common_api import HEADERS, app_for
from test_cases_api import new_demo


def ready(client):
    did, rows = new_demo(client)
    cid = rows[0]['id']
    response = client.post(f'/api/v1/cases/{cid}/investigations?demonstration_id={did}', json=dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=0,retry_of=None),headers=HEADERS)
    assert response.status_code == 202
    view = client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()
    return did,cid,view


def command(view, **fields):
    return dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=view['case_revision'],**fields)


def test_generated_draft_review_exact_payload_replay_and_edit_invalidation(tmp_path):
    with TestClient(app_for(tmp_path/'db.sqlite'),base_url='http://127.0.0.1:8000') as client:
        did,cid,view=ready(client)
        assert view['draft_state']=='READY'
        draft=view['draft']
        assert draft['invoice_id']=='NS-104'
        url=f'/api/v1/cases/{cid}/draft-reviews?demonstration_id={did}'
        request=command(view,draft_version_id=draft['id'],payload_hash=draft['payload_hash'],expected_review_epoch=view['review_epoch'],decision='APPROVE')
        approved=client.post(url,json=request,headers=HEADERS)
        assert approved.status_code==200,approved.text
        assert client.get(f"/api/v1/operations/{request['operation_id']}",params={'demonstration_id':did}).json()==approved.json()
        review=approved.json()['draft_review']
        assert review['exact_text']==draft['exact_text']
        assert review['recipient']==draft['recipient']
        assert client.post(url,json=request,headers=HEADERS).json()==approved.json()
        view=client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()
        assert view['review_state']=='APPROVED'
        edit=command(view,investigation_id=draft['investigation_id'],parent_version_id=draft['id'],exact_text=draft['exact_text'].replace('Hello','Hi'),recipient=draft['recipient'])
        saved=client.post(f'/api/v1/cases/{cid}/draft-versions?demonstration_id={did}',json=edit,headers=HEADERS)
        assert saved.status_code==201,saved.text
        assert client.get(f"/api/v1/operations/{edit['operation_id']}",params={'demonstration_id':did}).json()==saved.json()
        assert saved.json()['draft_version']['id']!=draft['id']
        view=client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()
        assert view['review_state']=='UNAPPROVED'
        assert len(view['draft_reviews'])==1


def test_invalid_text_saved_but_approval_and_arbitrary_recipient_blocked(tmp_path):
    with TestClient(app_for(tmp_path/'db.sqlite'),base_url='http://127.0.0.1:8000') as client:
        did,cid,view=ready(client);draft=view['draft']
        url=f'/api/v1/cases/{cid}/draft-versions?demonstration_id={did}'
        body=command(view,investigation_id=draft['investigation_id'],parent_version_id=draft['id'],exact_text='Pay INR 999999 plus a fee to my bank.',recipient=draft['recipient'])
        saved=client.post(url,json=body,headers=HEADERS)
        assert saved.status_code==201,saved.text
        invalid=saved.json()['draft_version']
        assert invalid['validation_status']=='INVALID' and invalid['validation_reasons']
        view=client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()
        approve=command(view,draft_version_id=invalid['id'],payload_hash=invalid['payload_hash'],expected_review_epoch=view['review_epoch'],decision='APPROVE')
        assert client.post(f'/api/v1/cases/{cid}/draft-reviews?demonstration_id={did}',json=approve,headers=HEADERS).status_code==409
        body=command(view,investigation_id=draft['investigation_id'],parent_version_id=invalid['id'],exact_text=draft['exact_text'],recipient='real@example.com')
        assert client.post(url,json=body,headers=HEADERS).status_code==422
        assert client.post(url,json=body|{'verified':True},headers=HEADERS).status_code==422
        assert client.post(f'/api/v1/cases/{cid}/send?demonstration_id={did}',json=body,headers=HEADERS).status_code in (404,405)


def test_independent_failure_status_retry_route_and_scoped_strict_commands(tmp_path):
    from promisekeeper.agents.protocol import InvestigatorFailure
    app=app_for(tmp_path/'db.sqlite')
    def fail(plan):raise InvestigatorFailure('SCRIPTED_DRAFT_FAILURE')
    app.state.draft_generator=fail
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        did,cid,view=ready(client)
        assert view['current_result']['action']=='FOLLOW_UP'
        assert view['draft_generation_state']=='FAILED'
        assert view['allowed_commands']['retry_draft']['allowed'] is True
        iid=view['current_result']['investigation_id']
        status=client.get(f'/api/v1/investigations/{iid}',params={'demonstration_id':did}).json()
        assert status['draft_status']=='FAILED'
        a=view['draft_generation_attempt']
        assert client.get(f"/api/v1/draft-attempts/{a['id']}",params={'demonstration_id':did}).json()['status']=='FAILED'
        other,_=new_demo(client)
        assert client.get(f"/api/v1/draft-attempts/{a['id']}",params={'demonstration_id':other}).status_code==404
        body=command(view,investigation_id=iid,failed_draft_attempt_id=a['id'],expected_draft_head=None)
        url=f'/api/v1/cases/{cid}/draft-retries?demonstration_id={did}'
        assert client.post(url,json=body|{'expected_case_revision':str(view['case_revision'])},headers=HEADERS).status_code==422
        del app.state.draft_generator
        response=client.post(url,json=body,headers=HEADERS)
        assert response.status_code==202,response.text
        assert client.get(f"/api/v1/operations/{body['operation_id']}",params={'demonstration_id':did}).json()==response.json()
        assert client.post(url,json=body,headers=HEADERS).json()==response.json()
        assert client.get(f"/api/v1/draft-attempts/{response.json()['draft_attempt_id']}",params={'demonstration_id':did}).json()['status']=='READY'
        view=client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()
        assert view['current_result']['investigation_id']==iid
        assert view['draft_generation_state']=='READY'
        for route,payload in [('draft-versions',command(view,investigation_id=iid,parent_version_id=view['draft']['id'],recipient=view['draft']['recipient'],exact_text=view['draft']['exact_text'])),('draft-reviews',command(view,draft_version_id=view['draft']['id'],payload_hash=view['draft']['payload_hash'],expected_review_epoch=view['review_epoch'],decision='APPROVE'))]:
            assert client.post(f'/api/v1/cases/{cid}/{route}?demonstration_id={did}',json=payload|{'extra':True},headers=HEADERS).status_code==422
            assert client.post(f'/api/v1/cases/{cid}/{route}',json=payload,headers=HEADERS).status_code==422


def test_deleted_copy_replays_content_free_review_receipt(tmp_path):
    with TestClient(app_for(tmp_path/'db.sqlite'),base_url='http://127.0.0.1:8000') as client:
        did,cid,view=ready(client);draft=view['draft']
        body=command(view,draft_version_id=draft['id'],payload_hash=draft['payload_hash'],expected_review_epoch=view['review_epoch'],decision='APPROVE')
        url=f'/api/v1/cases/{cid}/draft-reviews?demonstration_id={did}'
        assert client.post(url,json=body,headers=HEADERS).status_code==200
        deletion=dict(schema_version='1',operation_id=str(uuid4()),confirmed_demonstration_id=did,confirm=True)
        assert client.post(f'/api/v1/demonstrations/{did}/deletion',json=deletion,headers=HEADERS).status_code==200
        replay=client.post(url,json=body,headers=HEADERS)
        assert replay.status_code==200,replay.text
        assert replay.json()['receipt']['outcome']=='DELETED'
        assert 'exact_text' not in replay.text and 'draft_review' not in replay.json()
