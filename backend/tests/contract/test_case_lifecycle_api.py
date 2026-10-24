from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from test_common_api import HEADERS, app_for
from support.lifecycle import close_ready, closure, command


def test_exact_closure_reopening_and_disposition_receipts_are_scoped_and_strict(tmp_path):
    app = app_for(tmp_path/'db.sqlite')
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        did, cid, view = close_ready(app.state.db)
        base = f'/api/v1/cases/{cid}'
        params = {'demonstration_id':did}
        body = command(view, investigation_id=view['current_result']['investigation_id'], decision='ACCEPT', reason=None)
        saved = client.post(base+'/dispositions', params=params, json=body, headers=HEADERS)
        assert saved.status_code == 200, saved.text
        assert saved.json()['disposition']['decision'] == 'ACCEPT'
        assert client.get(base, params=params).json()['lifecycle'] == 'OPEN'
        assert client.get(f"/api/v1/operations/{body['operation_id']}", params=params).json() == saved.json()
        view = client.get(base, params=params).json()
        assert view['owner_dispositions'] == [saved.json()['disposition']]
        body = closure(view)
        for change in [{'confirm':False}, {'confirm':1}, {'extra':True}, {'expected_case_revision':str(view['case_revision'])}]:
            assert client.post(base+'/closure', params=params, json=body|change, headers=HEADERS).status_code == 422
        assert client.post(base+'/closure', params=params, json=body|{'confirmed_result_hash':'0'*64}, headers=HEADERS).status_code == 409
        closed = client.post(base+'/closure', params=params, json=body, headers=HEADERS)
        assert closed.status_code == 200, closed.text
        assert closed.json()['lifecycle'] == 'CLOSED'
        assert client.post(base+'/closure', params=params, json=body, headers=HEADERS).json() == closed.json()
        assert client.get(f"/api/v1/operations/{body['operation_id']}", params=params).json() == closed.json()
        view = client.get(base, params=params).json()
        reopening = command(view, confirm=True, reason='Review later evidence')
        assert client.post(base+'/reopening', params=params, json=reopening|{'confirm':False}, headers=HEADERS).status_code == 422
        assert client.post(base+'/reopening', params=params, json=reopening|{'reason':'x'*1001}, headers=HEADERS).status_code == 422
        reopened = client.post(base+'/reopening', params=params, json=reopening, headers=HEADERS)
        assert reopened.status_code == 200, reopened.text
        assert reopened.json()['lifecycle'] == 'OPEN'
        assert client.get(f"/api/v1/operations/{reopening['operation_id']}", params=params).json() == reopened.json()
        assert client.post(base+'/reopening', params=params, json=reopening, headers=HEADERS).json() == reopened.json()
        assert client.post(base+'/closure', json=closure(view), headers=HEADERS).status_code == 422
        assert client.post(base+'/dispositions', params={'demonstration_id':str(uuid4())}, json=command(view,investigation_id=view['current_result']['investigation_id'],decision='ACCEPT',reason=None), headers=HEADERS).status_code == 404


def test_historical_unreviewed_draft_is_directly_inspectable_with_copy_scope(tmp_path):
    from support.lifecycle import create_case, run
    from promisekeeper.application.reviews import save_draft
    app = app_for(tmp_path/'db.sqlite')
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        did, cid = create_case(app.state.db, catalogue_case_id='PK-001')
        view = run(app.state.db,did,cid); old = view['draft']
        save_draft(app.state.db,did,cid,command(view,investigation_id=old['investigation_id'],parent_version_id=old['id'],recipient=old['recipient'],exact_text=old['exact_text'].replace('Hello','Hi')))
        url = f"/api/v1/draft-versions/{old['id']}"
        response = client.get(url,params={'demonstration_id':did})
        assert response.status_code == 200, response.text
        assert response.json() == {'schema_version':'1','draft_version':old}
        assert client.get(url,params={'demonstration_id':str(uuid4())}).status_code == 404


@pytest.mark.parametrize('changes', [{'decision':'APPROVE'}, {'reason':'x'*1001}, {'reason':7}, {'extra':True}])
def test_disposition_rejects_invalid_fields(tmp_path,changes):
    app = app_for(tmp_path/'db.sqlite')
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        did,cid,view=close_ready(app.state.db)
        body=command(view,investigation_id=view['current_result']['investigation_id'],decision='REJECT',reason=None)
        response=client.post(f'/api/v1/cases/{cid}/dispositions',params={'demonstration_id':did},json=body|changes,headers=HEADERS)
        assert response.status_code == 422,response.text


def test_missing_and_foreign_results_and_history_query_boundaries(tmp_path):
    from support.lifecycle import create_case,run
    app=app_for(tmp_path/'db.sqlite')
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        did,cid=create_case(app.state.db)
        params={'demonstration_id':did};base=f'/api/v1/cases/{cid}'
        view=client.get(base,params=params).json()
        assert view['allowed_commands']['close']=={'allowed':False,'blocking_reasons':['NO_COMPLETED_RESULT']}
        missing=command(view,investigation_id=str(uuid4()),confirmed_result_hash='a'*64,confirm=True)
        response=client.post(base+'/closure',params=params,json=missing,headers=HEADERS)
        assert response.status_code==404 and response.json()['error']['code']=='NOT_FOUND'
        foreign,other=create_case(app.state.db);other_view=run(app.state.db,foreign,other)
        response=client.post(base+'/closure',params=params,json=missing|{'operation_id':str(uuid4()),'investigation_id':other_view['current_result']['investigation_id']},headers=HEADERS)
        assert response.status_code==404
        for query in [{'limit':0},{'limit':101},{'cursor':-1},{'cursor':'wrong'}]:
            assert client.get(base+'/history',params=params|query).status_code==422
        assert client.get(base+'/history',params={'demonstration_id':foreign}).status_code==404
        assert client.get(base+'/history').status_code==422
