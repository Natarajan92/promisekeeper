"""Owner feedback and draft edits are kept locally and, best-effort, sent to LangSmith."""
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from support.lifecycle import command, create_case
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.cases import get_case
from promisekeeper.application.feedback import record_feedback
from promisekeeper.application.operations import CommandError
from promisekeeper.application.reviews import review_draft, save_draft
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.orchestration.investigate import investigate
from promisekeeper.persistence.sqlite import Database


def investigated(db):
    did, cid = create_case(db, catalogue_case_id='PK-001')
    iid = start_investigation(db, did, cid, command(get_case(db, did, cid), retry_of=None))['investigation_id']
    assert investigate(db, iid, ScriptedInvestigator())
    return did, cid, iid


def feedback(iid, **fields):
    return dict(schema_version='1', operation_id=str(uuid4()), investigation_id=iid, target='RECOMMENDATION', rating='UP', comment=None) | fields


def edit_and_approve(db, did, cid):
    view = get_case(db, did, cid)
    draft = view['draft']
    edited = draft['exact_text'].replace('Hello', 'Hi', 1)
    save_draft(db, did, cid, command(view, investigation_id=draft['investigation_id'], parent_version_id=draft['id'],
                                     exact_text=edited, recipient=draft['recipient']))
    view = get_case(db, did, cid)
    draft = view['draft']
    review_draft(db, did, cid, command(view, draft_version_id=draft['id'], payload_hash=draft['payload_hash'],
                                       expected_review_epoch=view['review_epoch'], decision='APPROVE'))
    return edited


def test_feedback_saved_and_idempotent(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid = investigated(db)
        request = feedback(iid, rating='DOWN', comment='Explain the promise date more clearly.')
        first = record_feedback(db, did, cid, request)
        assert record_feedback(db, did, cid, request) == first
        assert first['feedback']['rating'] == 'DOWN' and first['sent_to_langsmith'] is False
        with db.connection() as con:
            assert con.execute('SELECT COUNT(*) FROM owner_feedback').fetchone()[0] == 1


def test_feedback_saved_when_langsmith_unreachable(tmp_path, monkeypatch):
    monkeypatch.setenv('LANGSMITH_TRACING', 'true')
    monkeypatch.setenv('LANGSMITH_API_KEY', 'ls-test')
    def unreachable():
        raise ConnectionError('LangSmith unreachable')
    monkeypatch.setattr('promisekeeper.application.feedback.langsmith_client', unreachable)
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid = investigated(db)
        saved = record_feedback(db, did, cid, feedback(iid, target='DRAFT'))
        assert saved['sent_to_langsmith'] is False and saved['feedback']['target'] == 'DRAFT'


def test_feedback_is_sent_to_langsmith_run_when_configured(tmp_path, monkeypatch):
    from promisekeeper.orchestration.case_graph import run_id_for
    sent = []
    class Client:
        def create_feedback(self, run_id, key, **kw):
            sent.append((run_id, key, kw['score'], kw.get('comment')))
    monkeypatch.setenv('LANGSMITH_TRACING', 'true')
    monkeypatch.setenv('LANGSMITH_API_KEY', 'ls-test')
    monkeypatch.setattr('promisekeeper.application.feedback.langsmith_client', Client)
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid = investigated(db)
        saved = record_feedback(db, did, cid, feedback(iid, rating='DOWN', comment='Too formal'))
        assert saved['sent_to_langsmith'] is True
        assert sent == [(run_id_for(iid), 'owner_recommendation_rating', 0, 'Too formal')]


def test_feedback_rejects_investigation_from_another_case(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid = investigated(db)
        with db.connection() as con:
            other = con.execute('SELECT id FROM cases WHERE demonstration_id=? AND id<>? LIMIT 1', (did, cid)).fetchone()[0]
        with pytest.raises(CommandError) as raised:
            record_feedback(db, did, other, feedback(iid))
        assert raised.value.code == 'NOT_FOUND'


def test_approval_records_agent_vs_approved_diff(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid = investigated(db)
        original = get_case(db, did, cid)['draft']['exact_text']
        edited = edit_and_approve(db, did, cid)
        with db.connection() as con:
            row = dict(con.execute('SELECT * FROM draft_edit_feedback').fetchone())
        assert (row['agent_text'], row['approved_text'], row['changed']) == (original, edited, 1)


def test_edit_diff_failure_never_blocks_approval(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('diff store unavailable')
    monkeypatch.setattr('promisekeeper.application.reviews.record_edit_diff', broken)
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid = investigated(db)
        edit_and_approve(db, did, cid)
        assert get_case(db, did, cid)['draft_reviews'][-1]['decision'] == 'APPROVE'


def test_feedback_api_requires_mutation_header(tmp_path):
    from promisekeeper.api.app import create_app
    from promisekeeper.config import Settings
    app = create_app(Settings('STUB', 'm', tmp_path / 'api.sqlite', None))
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        did, cid, iid = investigated(app.state.db)
        url = f'/api/v1/cases/{cid}/feedback'
        assert client.post(url, params={'demonstration_id': did}, json=feedback(iid)).status_code in {400, 403}
        ok = client.post(url, params={'demonstration_id': did}, json=feedback(iid), headers={'X-PromiseKeeper-Request': '1'})
        assert ok.status_code == 201 and ok.json()['feedback']['rating'] == 'UP'
