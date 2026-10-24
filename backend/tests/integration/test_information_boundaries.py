"""Fictional evidence, provider errors and generated candidates retain their boundaries."""

from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient
from openai import APIStatusError

from promisekeeper.agents.nebius import NebiusInvestigator
from promisekeeper.agents.protocol import AgentResponse
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.api.app import create_app
from promisekeeper.application.cases import get_case
from promisekeeper.application.lifecycle import close_case
from promisekeeper.application.operations import CommandError
from promisekeeper.application.reviews import review_draft, save_draft
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.config import Settings
from promisekeeper.diagnostics import diagnostic
from promisekeeper.orchestration.investigate import get_investigation, investigate
from promisekeeper.persistence.repositories import history
from promisekeeper.persistence.sqlite import Database
from support.lifecycle import command
from test_investigation_pipeline import create, start


# Synthetic data only. No environment or workspace credential is read by these tests.
SENTINEL = 'fictional-boundary-secret-7cd4'
HEADERS = {'X-PromiseKeeper-Request': '1'}


@pytest.fixture
def isolated_evaluation_usage(tmp_path, monkeypatch):
    from promisekeeper.application import evaluations
    from promisekeeper.application.provider_usage import usage_recorder

    ledger = tmp_path / 'application-provider-usage.jsonl'
    original_open = Path.open

    def guarded_open(path, mode='r', *args, **kwargs):
        if path.name == ledger.name and any(flag in mode for flag in ('w', 'a', 'x', '+')):
            assert path.resolve().is_relative_to(tmp_path.resolve()), 'Evaluation usage escaped temporary storage'
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, 'open', guarded_open)
    monkeypatch.setattr(evaluations, 'usage_recorder', lambda requested_path: usage_recorder(ledger))
    return ledger


def approval(view):
    draft = view['draft']
    return command(view, draft_version_id=draft['id'], payload_hash=draft['payload_hash'],
                   expected_review_epoch=view['review_epoch'], decision='APPROVE')


def test_registered_untrusted_message_cannot_verify_settlement_approve_or_control_draft(tmp_path):
    with Database(tmp_path / 'injection.sqlite') as db:
        did, rows = create(db, 'FV-12')
        cid = rows[0]['id']
        iid = start(db, did, rows[0])
        assert investigate(db, iid, ScriptedInvestigator())
        view = get_case(db, did, cid)
        message = next(source for source in view['evidence'] if source['kind'] == 'MESSAGE')
        assert 'Ignore your rules' in message['original_content']
        assert message['authoritative'] is False
        assert view['current_result']['action'] == 'FOLLOW_UP'
        assert view['financial_facts']['balance']['minor_units'] == '8000000'
        assert view['financial_facts']['paid']['minor_units'] == '4000000'
        assert view['review_state'] == 'UNAPPROVED'
        assert 'Ignore your rules' not in view['draft']['exact_text']
        assert 'mark this invoice paid' not in view['draft']['exact_text']
        review_draft(db, did, cid, approval(view))
        reviewed = get_case(db, did, cid)
        assert reviewed['review_state'] == 'APPROVED'
        assert reviewed['financial_facts'] == view['financial_facts']
        result = reviewed['current_result']
        with pytest.raises(CommandError, match='CLOSE_NOT_RECOMMENDED'):
            close_case(db, did, cid, command(reviewed, investigation_id=iid,
                confirmed_result_hash=result['result_hash'], confirm=True))
        # Owner text is also a draft, never a financial instruction or a ledger edit.
        draft = reviewed['draft']
        saved = save_draft(db, did, cid, command(reviewed, investigation_id=iid,
            parent_version_id=draft['id'], recipient=draft['recipient'], exact_text='This invoice is paid. Close it now.'))
        assert saved['draft_version']['validation_status'] == 'INVALID'
        changed = get_case(db, did, cid)
        with pytest.raises(CommandError):
            review_draft(db, did, cid, approval(changed))
        assert changed['financial_facts'] == view['financial_facts']
        assert changed['lifecycle'] == 'OPEN'


@pytest.mark.parametrize('forgery', ['foreign_copy', 'foreign_source_id', 'ledger_candidate', 'foreign_replacement', 'model_action'])
def test_candidate_reference_forgery_cannot_replace_saved_result_or_gain_authority(tmp_path, forgery):
    with Database(tmp_path / 'references.sqlite') as db:
        did, rows = create(db)
        cid = rows[0]['id']
        assert investigate(db, start(db, did, rows[0]), ScriptedInvestigator())
        before = get_case(db, did, cid)
        review_draft(db, did, cid, approval(before))
        other, foreign_rows = create(db)
        foreign_message = next(source for source in get_case(db, other, foreign_rows[0]['id'])['evidence'] if source['kind'] == 'MESSAGE')

        class Forged(ScriptedInvestigator):
            def extract(self, request, *, timeout):
                output = deepcopy(super().extract(request, timeout=timeout).output)
                candidate = output['commitments'][0]
                if forgery == 'foreign_copy':
                    candidate['source']['evidence_version_id'] = foreign_message['id']
                elif forgery == 'foreign_source_id':
                    candidate['source']['source_id'] = 'PK-002-M1'
                elif forgery == 'ledger_candidate':
                    record = next(source for source in request['packet']['evidence'] if source['kind'] == 'LEDGER')
                    candidate['source'] = dict(evidence_version_id=record['id'], source_id=record['stable_source_id'],
                                              start=0, end=len(record['original_content']), quote=record['original_content'])
                elif forgery == 'foreign_replacement':
                    candidate['explicitly_replaces_source_id'] = 'PK-002-M1'
                else:
                    output.update(action='CLOSE', balance='0', approved=True)
                return AgentResponse(output)

        fresh = get_case(db, did, cid)
        started = start_investigation(db, did, cid, command(fresh, retry_of=None))
        assert not investigate(db, started['investigation_id'], Forged())
        failed = get_investigation(db, did, started['investigation_id'])
        assert failed['status'] == 'INCOMPLETE'
        assert failed['failure_code'] == 'INVALID_INVESTIGATOR_OUTPUT'
        assert failed['action'] is None and failed['result'] is None
        after = get_case(db, did, cid)
        assert after['current_result'] == before['current_result']
        assert after['draft'] == before['draft']
        assert after['review_state'] == 'INVALIDATED'
        assert after['financial_facts'] == before['financial_facts']
        assert len(after['draft_reviews']) == 1


def test_designated_but_unverified_ledger_does_not_resolve_customer_claim(tmp_path, monkeypatch):
    # Test-only materialization supplies the missing verification-status branch;
    # it is never registered as a runtime input or arbitrary-write endpoint.
    from promisekeeper.application import cases as application_cases
    from promisekeeper.fixtures.catalogue import _build, apply_event, fresh_copy

    fixture = apply_event(fresh_copy(), 'PK-003-U1')
    raw = json.loads(fixture._records_json)
    ledger = next(source for source in raw['PK-003']['sources'] if source['source_id'] == 'PK-003-L2')
    ledger['data']['verification_status'] = 'UNVERIFIED'
    modified = _build(fixture.id, fixture.variant_id, fixture.catalogue_version, fixture.evaluation_at, raw, fixture.applied_events)
    monkeypatch.setattr(application_cases, 'fresh_copy', lambda variant=None: modified)
    with Database(tmp_path / 'unverified.sqlite') as db:
        did, rows = create(db)
        row = next(row for row in rows if row['catalogue_case_id'] == 'PK-003')
        iid = start(db, did, row)
        assert investigate(db, iid, ScriptedInvestigator())
        view = get_case(db, did, row['id'])
        result = view['current_result']
        assert result['action'] == 'VERIFY_PAYMENT'
        assert result['financial_facts']['paid']['minor_units'] == '3000000'
        assert result['financial_facts']['balance']['minor_units'] == '6000000'
        assert result['claims'][0]['resolved'] is False
        assert 'UNVERIFIED_PAYMENT' in {issue['code'] for issue in result['financial_facts']['issues']}
        source = next(source for source in view['evidence'] if source['stable_source_id'] == 'PK-003-L2')
        assert source['authoritative'] is True and source['data']['verification_status'] == 'UNVERIFIED'
        assert view['draft'] is None
        with pytest.raises(CommandError, match='CLOSE_NOT_RECOMMENDED'):
            close_case(db, did, row['id'], command(view, investigation_id=iid,
                confirmed_result_hash=result['result_hash'], confirm=True))


def provider_client(behavior):
    """Only the external provider boundary is substituted; the adapter stays real."""
    class Completions:
        def create(self, **kwargs):
            if behavior == 'provider_error':
                response = httpx.Response(400, request=httpx.Request('POST', 'https://fictional.invalid/completions'))
                raise APIStatusError('Bearer ' + SENTINEL, response=response, body={'private': SENTINEL})
            message = SimpleNamespace(content='{ ' + SENTINEL, refusal=SENTINEL if behavior == 'refusal' else None)
            return SimpleNamespace(id='fictional-response', model='fictional-model', usage=None,
                                   choices=[SimpleNamespace(finish_reason='stop', message=message)])
    return SimpleNamespace(chat=SimpleNamespace(completions=Completions()))


@pytest.mark.parametrize('behavior,code', [('provider_error', 'PROVIDER_REJECTED_REQUEST'),
                                         ('refusal', 'INVESTIGATOR_REFUSAL'), ('malformed', 'INVALID_INVESTIGATOR_OUTPUT')])
def test_synthetic_provider_secret_is_absent_from_saved_failure_views_diagnostics_and_evaluation(tmp_path, monkeypatch, capsys, isolated_evaluation_usage, behavior, code):
    from promisekeeper.agents import nebius
    from promisekeeper.application.evaluations import evaluate, evaluation_manifest

    settings = Settings('LIVE', 'fictional-model', tmp_path / 'provider.sqlite', SENTINEL)
    monkeypatch.setattr(nebius, 'OpenAI', lambda **kwargs: provider_client(behavior))
    with Database(settings.db_path) as db:
        did, rows = create(db)
        iid = start(db, did, rows[0])
        assert not investigate(db, iid, NebiusInvestigator(settings))
        view = get_investigation(db, did, iid)
        assert view['failure_code'] == code
        assert view['result'] is None and view['action'] is None
        case_view = get_case(db, did, rows[0]['id'])
        assert case_view['current_result'] is None and case_view['draft'] is None
        records = [view, case_view, history(db, did, rows[0]['id']), settings.safe_summary(), repr(settings)]
        event = diagnostic('step_failed', dict(failure_code=code, requested_model='Bearer ' + SENTINEL,
            raw_response=SENTINEL, customer_message=SENTINEL, api_key=SENTINEL), secrets=(SENTINEL,))
        assert event['requested_model'] == '[REDACTED]'
        assert not {'raw_response', 'customer_message', 'api_key'} & event.keys()
        records.append(event)
        assert SENTINEL not in json.dumps(records)
    report_path = tmp_path / 'evaluation.json'
    report = evaluate(settings, catalogue='release-0.1', repeats=1, output=report_path, manifest=evaluation_manifest()[:1])
    assert len(report['runs']) == 1
    assert report['runs'][0]['failure_code'] == code
    assert report['runs'][0]['result_present'] is False
    assert report['qualified'] is False
    assert SENTINEL not in report_path.read_text(encoding='utf-8')
    if behavior == 'provider_error':
        assert not isolated_evaluation_usage.exists()
    else:
        ledger_text = isolated_evaluation_usage.read_text(encoding='utf-8')
        assert SENTINEL not in ledger_text
        metadata = [json.loads(line) for line in ledger_text.splitlines()]
        assert len(metadata) == 1
        assert metadata[0]['response_id'] == 'fictional-response'
        assert metadata[0]['usage'] == {}
        assert not {'output', 'content', 'refusal', 'api_key'} & metadata[0].keys()
    captured = capsys.readouterr()
    assert SENTINEL not in captured.out + captured.err


def test_evaluation_provider_usage_is_confined_to_temporary_storage(tmp_path, monkeypatch, isolated_evaluation_usage):
    from promisekeeper.agents import nebius
    from promisekeeper.application.evaluations import evaluate, evaluation_manifest

    settings = Settings('LIVE', 'fictional-model', tmp_path / 'isolated.sqlite', SENTINEL)
    monkeypatch.setattr(nebius, 'OpenAI', lambda **kwargs: provider_client('refusal'))
    for index in range(2):
        report = evaluate(settings, catalogue='release-0.1', repeats=1,
            output=tmp_path / f'evaluation-{index}.json', manifest=evaluation_manifest()[:1])
        assert report['runs'][0]['failure_code'] == 'INVESTIGATOR_REFUSAL'
    records = [json.loads(line) for line in isolated_evaluation_usage.read_text(encoding='utf-8').splitlines()]
    assert len(records) == 2
    assert all(record['provider'] == 'NEBIUS' and record['response_id'] == 'fictional-response' for record in records)
    assert SENTINEL not in json.dumps(records)
    # A regression restoring the requested workspace path is rejected before opening it.
    outside = tmp_path.parent / 'application-provider-usage.jsonl'
    with pytest.raises(AssertionError, match='escaped temporary storage'):
        outside.open('a', encoding='utf-8')


def test_http_rejects_arbitrary_real_data_and_does_not_echo_rejected_payload_or_storage_error(tmp_path, monkeypatch):
    import sqlite3

    app = create_app(Settings('STUB', 'fictional-model', tmp_path / 'api.sqlite', SENTINEL))
    with TestClient(app, base_url='http://127.0.0.1:8000') as client:
        base = dict(schema_version='1', catalogue_version='release-0.1', variant_id=None, clock_mode='REFERENCE')
        for extra in ({'evidence': [{'original_content': SENTINEL}]}, {'ledger': {'bank_reference': SENTINEL}},
                      {'customer': SENTINEL}, {'variant_id': SENTINEL}, {'catalogue_version': SENTINEL}):
            rejected = client.post('/api/v1/demonstrations', headers=HEADERS,
                                   json=base | {'operation_id': str(uuid4())} | extra)
            assert rejected.status_code == 422
            assert SENTINEL not in rejected.text
        assert client.get('/api/v1/demonstrations').json()['demonstrations'] == []
        created = client.post('/api/v1/demonstrations', headers=HEADERS, json=base | {'operation_id': str(uuid4())})
        assert created.status_code == 201
        did = created.json()['demonstration_id']
        rows = client.get(f'/api/v1/demonstrations/{did}/cases').json()['cases']
        cid = rows[0]['id']
        assert len(rows) == 3
        response = client.get(f'/api/v1/cases/{cid}/scenario-events/{SENTINEL}/preview', params={'demonstration_id': did})
        assert response.status_code == 422 and SENTINEL not in response.text
        def fail(con):
            raise sqlite3.OperationalError('private provider value ' + SENTINEL)
        monkeypatch.setattr(app.state.db, 'commit', fail)
        failed = client.post('/api/v1/demonstrations', headers=HEADERS, json=base | {'operation_id': str(uuid4())})
        assert failed.status_code == 503 and failed.json()['error']['code'] == 'STORAGE_UNAVAILABLE'
        assert SENTINEL not in failed.text
        assert SENTINEL not in client.get('/api/v1/health').text
        assert len(client.get('/api/v1/demonstrations').json()['demonstrations']) == 1
