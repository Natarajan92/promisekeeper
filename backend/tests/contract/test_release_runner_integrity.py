"""Mutations proving release checks reject wrong money and rewritten history."""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import replace
import json
import sqlite3

from fastapi.testclient import TestClient
import pytest

from promisekeeper.config import Settings


@pytest.mark.parametrize('case,field,value', [
    ('baseline:PK-001', 'invoice', {'currency': 'INR', 'minor_units': '22000000'}),
    ('baseline:PK-001', 'paid', {'currency': 'INR', 'minor_units': '14000000'}),
    ('baseline:PK-001', 'invoice', {'currency': 'USD', 'minor_units': '12000000'}),
    ('baseline:PK-001', 'paid', {'currency': 'USD', 'minor_units': '4000000'}),
    ('baseline:PK-001', 'balance', {'currency': 'USD', 'minor_units': '8000000'}),
    ('baseline:PK-001', 'invoice', None),
    ('baseline:PK-001', 'due_at', '2026-10-12T00:00:00+05:30'),
    ('baseline:PK-001', 'coordinated_offset', None),
    ('FV-05', 'paid', {'currency': 'INR', 'minor_units': '3000000'}),
    ('FV-01', 'invoice', {'currency': 'INR', 'minor_units': '12000000'}),
])
def test_fixture_evaluation_rejects_corrupt_financial_projection(tmp_path, monkeypatch, case, field, value):
    from promisekeeper.application import fixture_evaluation as runner
    from promisekeeper.application.evaluations import evaluation_manifest
    from promisekeeper.application.evaluation_findings import load_inventory
    from promisekeeper.persistence.sqlite import Database
    entries = evaluation_manifest()
    entry = next(e for e in entries if e['id'] == case)
    original = runner.get_investigation
    def corrupt(*args):
        result = deepcopy(original(*args))
        facts = result['result']['financial_facts']
        if field == 'coordinated_offset':
            # Arithmetic remains internally consistent and all currencies INR;
            # only an independent numeric oracle can reject this paired lie.
            facts['invoice']['minor_units'] = '22000000'
            facts['paid']['minor_units'] = '14000000'
        else:
            facts[field] = value
        return result
    monkeypatch.setattr(runner, 'get_investigation', corrupt)
    with Database(tmp_path / 'mutation.sqlite') as db:
        row = runner._run_entry(db, entry, load_inventory(entries)['entries'][case])
    assert row['checks']['financial_correct'] is False
    assert row['passed'] is False


class HTTPAdapter:
    def __init__(self, client, mutation=None):
        self.client = client
        self.mutation = mutation
    def request(self, path, body=None, **kwargs):
        response = self.client.request('GET' if body is None else 'POST', '/api/v1' + path,
            json=body, headers={'X-PromiseKeeper-Request': '1', 'Content-Type': 'application/json'})
        response.raise_for_status()
        result = response.json()
        if self.mutation:
            self.mutation(path, body)
        return result


def _mutate(path, table):
    with sqlite3.connect(path) as con:
        # Deliberately bypass the isolated test DB's storage fence: this tests
        # whether the acceptance runner independently notices rewritten rows.
        con.execute(f'DROP TRIGGER IF EXISTS immutable_{table}_update')
        if table == 'investigation_results':
            row = con.execute('SELECT investigation_id,result_json FROM investigation_results ORDER BY rowid LIMIT 1').fetchone()
            result = json.loads(row[1]); result['financial_facts']['invoice']['minor_units'] = '99000000'
            con.execute('UPDATE investigation_results SET result_json=? WHERE investigation_id=?', (json.dumps(result), row[0]))
        elif table == 'draft_reviews':
            con.execute("UPDATE draft_reviews SET exact_text=exact_text || ' tampered' WHERE rowid=(SELECT min(rowid) FROM draft_reviews)")
        else:
            con.execute("UPDATE case_events SET payload_json=json_set(payload_json,'$.tampered',1) WHERE rowid=(SELECT min(rowid) FROM case_events)")


@pytest.mark.parametrize('table', ['investigation_results', 'draft_reviews', 'case_events'])
def test_preservation_rejects_prior_immutable_rows_rewritten_during_next_investigation(tmp_path, monkeypatch, table):
    from promisekeeper.application import measurements as runner
    from promisekeeper.api.app import create_app
    dbpath = tmp_path / 'history.sqlite'
    settings = Settings('STUB', 'test-model', dbpath, None)
    starts = set()
    def mutation(path, body):
        if body is not None and '/investigations?' in path:
            is_new = body['operation_id'] not in starts
            starts.add(body['operation_id'])
            if is_new and len(starts) == 3:
                _mutate(dbpath, table)
    @contextmanager
    def server(settings, path):
        with TestClient(create_app(replace(settings, db_path=path)), base_url='http://127.0.0.1') as client:
            yield HTTPAdapter(client, mutation)
    monkeypatch.setattr(runner, '_server', server)
    report = {'runs': []}
    runner._preservation(settings, tmp_path / 'report.json', report, dbpath)
    assert report['passed'] is False
    assert report['runs'][1]['prior_immutable_rows_preserved'] is False


@pytest.mark.parametrize('operation,table', [('review', 'draft_reviews'), ('closure', 'case_events')])
def test_review_and_closure_replays_reject_mutated_saved_state(tmp_path, operation, table):
    from promisekeeper.application import measurements as runner
    from promisekeeper.api.app import create_app
    dbpath = tmp_path / 'replay.sqlite'
    settings = Settings('STUB', 'test-model', dbpath, None)
    replays = 0
    def mutation(path, body):
        nonlocal replays
        endpoint = '/draft-reviews?' if operation == 'review' else '/closure?'
        if body is not None and endpoint in path:
            replays += 1
            if replays == 2:
                _mutate(dbpath, table)
    with TestClient(create_app(settings), base_url='http://127.0.0.1') as browser:
        client = HTTPAdapter(browser, mutation)
        did, cases = runner._seed(client)
        if operation == 'review':
            runner._attempt(client, did, cases['PK-001'])
            correct = runner._review(client, did, cases['PK-001'], dbpath=dbpath)
        else:
            correct = runner._settle_and_close(client, did, cases['PK-003'], dbpath=dbpath)
    assert correct is False
