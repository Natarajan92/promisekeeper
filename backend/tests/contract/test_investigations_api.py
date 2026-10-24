from uuid import uuid4

from fastapi.testclient import TestClient

from test_common_api import HEADERS, app_for
from test_cases_api import new_demo


def test_start_returns_durable_receipt_and_completed_source_linked_result(tmp_path):
    app = app_for(tmp_path / 'investigation.sqlite')
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        did, cases = new_demo(client)
        cid = cases[0]['id']
        request = dict(schema_version='1', operation_id=str(uuid4()), expected_case_revision=0, retry_of=None)
        url = f'/api/v1/cases/{cid}/investigations?demonstration_id={did}'
        response = client.post(url, json=request, headers=HEADERS)
        assert response.status_code == 202, response.text
        started = response.json()
        assert client.post(url, json=request, headers=HEADERS).json() == started
        status = client.get(f"/api/v1/investigations/{started['investigation_id']}", params={'demonstration_id': did})
        assert status.status_code == 200, status.text
        attempt = status.json()
        assert attempt['status'] == 'COMPLETE'
        result = attempt['result']
        assert result['action'] == 'FOLLOW_UP'
        assert result['financial_facts']['balance']['minor_units'] == '8000000'
        assert result['snapshot_id'] == started['snapshot_id']
        assert result['evaluation_at'] == started['evaluation_at']
        assert result['timeline'] and result['explanation']['sources']
        view = client.get(f'/api/v1/cases/{cid}', params={'demonstration_id': did}).json()
        assert view['current_result'] == result
        assert view['latest_completed_result'] == result
        assert view['allowed_commands']['start_investigation']['allowed'] is True
        assert client.get(f"/api/v1/investigations/{started['investigation_id']}").status_code == 422
        other, _ = new_demo(client)
        assert client.get(f"/api/v1/investigations/{started['investigation_id']}", params={'demonstration_id': other}).status_code == 404


def test_start_rejects_extra_coerced_and_missing_nullable_retry(tmp_path):
    with TestClient(app_for(tmp_path / 'db.sqlite'), base_url='http://127.0.0.1:8000') as client:
        did, cases = new_demo(client)
        base = dict(schema_version='1', operation_id=str(uuid4()), expected_case_revision=0, retry_of=None)
        url = f"/api/v1/cases/{cases[0]['id']}/investigations?demonstration_id={did}"
        for changed in [base | {'action': 'CLOSE'}, base | {'expected_case_revision': '0'}, {k:v for k,v in base.items() if k != 'retry_of'}]:
            assert client.post(url, json=changed, headers=HEADERS).status_code == 422
