"""Morning Review supervisor: decides which cases need work, runs them, briefs the owner."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from support.lifecycle import command
from promisekeeper.agents.briefing import ScriptedBriefing
from promisekeeper.agents.communicator import ScriptedCommunicator
from promisekeeper.agents.llm_client import scripted_call
from promisekeeper.agents.reviewer import ScriptedReviewer
from promisekeeper.agents.roster import AgentSet
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.cases import create_demonstration, get_case
from promisekeeper.application.operations import CommandError
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.orchestration.morning_review import get_morning_review, run_morning_review, start_morning_review
from promisekeeper.persistence.sqlite import Database


def agents(briefing=None):
    return AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), briefing or ScriptedBriefing())


def demo(db):
    return create_demonstration(db, dict(schema_version='1', operation_id=str(uuid4()), catalogue_version='release-0.1',
                                         variant_id=None, clock_mode='REFERENCE'))['demonstration_id']


def review(db, did, agent_set=None, operation_id=None):
    started = start_morning_review(db, did, dict(schema_version='1', operation_id=operation_id or str(uuid4())))
    run_morning_review(db, agent_set or agents(), started['id'])
    return get_morning_review(db, did, started['id'])


def investigation_count(db, did):
    with db.connection() as con:
        return con.execute('SELECT COUNT(*) FROM investigations WHERE demonstration_id=?', (did,)).fetchone()[0]


def test_morning_review_investigates_all_new_cases_and_briefs(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        result = review(db, did)
        assert result['status'] == 'COMPLETE' and result['briefing_source'] == 'AGENT'
        assert [o['outcome'] for o in result['outcomes']] == ['INVESTIGATED'] * 3
        assert [o['action'] for o in result['outcomes']] == ['FOLLOW_UP', 'WAIT', 'VERIFY_PAYMENT']
        for outcome in result['outcomes']:
            assert outcome['client'] in result['briefing']
        agents_seen = [row['agent'] for row in result['agent_activity']]
        assert agents_seen[0] == 'SUPERVISOR' and agents_seen[-1] == 'BRIEFING'


def test_second_morning_review_skips_current_cases(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        review(db, did)
        before = investigation_count(db, did)
        again = review(db, did)
        assert [o['outcome'] for o in again['outcomes']] == ['SKIPPED'] * 3
        assert all(o['reason'] for o in again['outcomes'])
        assert investigation_count(db, did) == before


def test_running_and_closed_cases_are_never_started(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        with db.connection() as con:
            cid = con.execute("SELECT id FROM cases WHERE demonstration_id=? AND catalogue_case_id='PK-002'", (did,)).fetchone()[0]
        start_investigation(db, did, cid, command(get_case(db, did, cid), retry_of=None))
        result = review(db, did)
        running = next(o for o in result['outcomes'] if o['case_id'] == cid)
        assert running['outcome'] == 'SKIPPED' and 'running' in running['reason'].lower()
        with db.connection() as con:
            assert con.execute('SELECT COUNT(*) FROM investigations WHERE case_id=?', (cid,)).fetchone()[0] == 1


def test_briefing_with_invented_number_falls_back(tmp_path):
    class Inventive:
        def summarize(self, facts, *, timeout):
            return scripted_call({'briefing': 'Northstar owes INR 9,99,999 today.'})
    with Database(tmp_path / 'db.sqlite') as db:
        result = review(db, demo(db), agents(Inventive()))
        assert result['briefing_source'] == 'DETERMINISTIC' and '9,99,999' not in result['briefing']
        assert any(r['agent'] == 'BRIEFING' and r['outcome'] == 'FALLBACK' for r in result['agent_activity'])


def test_briefing_failure_falls_back(tmp_path):
    class Broken:
        def summarize(self, facts, *, timeout):
            raise RuntimeError('provider down')
    with Database(tmp_path / 'db.sqlite') as db:
        result = review(db, demo(db), agents(Broken()))
        assert result['status'] == 'COMPLETE' and result['briefing_source'] == 'DETERMINISTIC'


def test_morning_review_is_idempotent_and_single_flight(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        op = str(uuid4())
        first = start_morning_review(db, did, dict(schema_version='1', operation_id=op))
        assert start_morning_review(db, did, dict(schema_version='1', operation_id=op))['id'] == first['id']
        with pytest.raises(CommandError) as raised:
            start_morning_review(db, did, dict(schema_version='1', operation_id=str(uuid4())))
        assert raised.value.code == 'MORNING_REVIEW_RUNNING'


def test_morning_review_api(tmp_path):
    from promisekeeper.api.app import create_app
    from promisekeeper.config import Settings
    app = create_app(Settings('STUB', 'm', tmp_path / 'api.sqlite', None))
    headers = {'X-PromiseKeeper-Request': '1'}
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        did = demo(app.state.db)
        url = f'/api/v1/demonstrations/{did}/morning-reviews'
        assert client.post(url, json=dict(schema_version='1', operation_id=str(uuid4()))).status_code in {400, 403}
        started = client.post(url, json=dict(schema_version='1', operation_id=str(uuid4())), headers=headers)
        assert started.status_code == 202
        view = client.get(f"/api/v1/morning-reviews/{started.json()['id']}", params={'demonstration_id': did}).json()
        assert view['status'] == 'COMPLETE' and len(view['outcomes']) == 3
        latest = client.get(f'{url}/latest').json()
        assert latest['morning_review']['id'] == started.json()['id']
        assert client.get(f'/api/v1/morning-reviews/{uuid4()}', params={'demonstration_id': did}).status_code == 404
