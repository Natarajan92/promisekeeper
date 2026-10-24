from copy import deepcopy
import json
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from promisekeeper.application.operations import canonical, digest, instant, utcnow
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.contracts.investigations import EvidenceObservation
from test_cases_api import new_demo
from test_common_api import HEADERS, app_for


def test_legacy_sqlite_result_is_returned_without_new_fields_or_hash_change(tmp_path):
    app = app_for(tmp_path/'legacy.sqlite')
    with TestClient(app,base_url='http://127.0.0.1:8000') as client:
        did, cases = new_demo(client, 'FV-07-PRECISION')
        cid = next(c['id'] for c in cases if c['catalogue_case_id']=='PK-003')
        response = client.post(f'/api/v1/cases/{cid}/investigations',params={'demonstration_id':did},headers=HEADERS,
                               json=dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=0,retry_of=None))
        iid = response.json()['investigation_id']
        current = client.get(f'/api/v1/investigations/{iid}',params={'demonstration_id':did}).json()['result']
        from promisekeeper.contracts.investigations import Result
        broken = deepcopy(current)
        broken['financial_facts']['issues'][0].pop('source_versions')
        with pytest.raises(ValidationError):
            Result.model_validate(broken)
        revision=client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()['case_revision']
        started = start_investigation(app.state.db,did,cid,dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=revision,retry_of=None))
        legacy = deepcopy(current)
        for field in ('findings_version','commitment_issues','evidence_observations'):
            legacy.pop(field)
        for issue in legacy['financial_facts']['issues']:
            issue.pop('source_versions',None)
        assert legacy['financial_facts']['issues']
        legacy.update(investigation_id=started['investigation_id'],snapshot_id=started['snapshot_id'])
        with app.state.db.transaction() as con:
            legacy['snapshot_hash']=con.execute('SELECT hash FROM evidence_snapshots WHERE id=?',(started['snapshot_id'],)).fetchone()[0]
            legacy['result_hash']=digest({k:v for k,v in legacy.items() if k!='result_hash'})
            con.execute('UPDATE investigations SET status=?,terminal_at=? WHERE id=?',(legacy['status'],instant(utcnow()),started['investigation_id']))
            con.execute('INSERT INTO investigation_results VALUES (?,?,?,?,?,?,?,?)',
                        (started['investigation_id'],did,cid,legacy['action'],legacy['review_at'],canonical(legacy),legacy['result_hash'],'rules-1'))
            con.execute('UPDATE cases SET latest_completed_investigation_id=? WHERE id=?',(started['investigation_id'],cid))
        app.state.db.capacity.release(started['investigation_id'])
        app.state.db.reservations.discard(started['investigation_id'])
        read = client.get(f"/api/v1/investigations/{started['investigation_id']}",params={'demonstration_id':did})
        assert read.status_code == 200, read.text
        assert read.json()['result'] == legacy
        case = client.get(f'/api/v1/cases/{cid}',params={'demonstration_id':did}).json()
        assert case['latest_completed_result'] == legacy
        with app.state.db.connection() as con:
            stored = json.loads(con.execute('SELECT result_json FROM investigation_results WHERE investigation_id=?',(started['investigation_id'],)).fetchone()[0])
        assert stored == legacy


@pytest.mark.parametrize('change',[
    dict(subject='SOURCE'),dict(field='complete',value='AVAILABLE'),dict(field='content_present',value=False),
    dict(value=True),dict(source=dict(source_id='s',evidence_version_id=str(uuid4()))),
])
def test_observation_subject_field_value_and_reference_are_consistent(change):
    base=dict(subject='LEDGER',field='availability',value='AVAILABLE',snapshot_id=str(uuid4()),snapshot_hash='a'*64,source=None)
    with pytest.raises(ValidationError):
        EvidenceObservation.model_validate(base | change)
