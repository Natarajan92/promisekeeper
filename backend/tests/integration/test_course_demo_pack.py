"""Course-demo upload pack: independent outcomes through the real intake API in STUB.

The imported workspace clock is the real upload time, so every journey here runs
against the real clock. For the fixed anchor (2026-10-26) a later real day can
legitimately expire the future promise; the oracle below applies only that
documented, independently computed drift (WAIT -> FOLLOW_UP once the promise day
has passed). Balances never drift. The "today" anchor asserts the manifest exactly.
"""
from datetime import date, datetime, time, timedelta
import json
import time as clock
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from promisekeeper.api.app import create_app
from promisekeeper.config import Settings
from support.intake import HEADERS, allocate, commit, operation, overview, preview

IST = ZoneInfo('Asia/Kolkata')
FIXED = date(2026, 10, 26)


def today():
    return datetime.now(IST).date()


def generate(folder, as_of):
    from promisekeeper.fixtures.course_demo_pack import generate_course_demo
    return generate_course_demo(folder, as_of)


def read(folder, relative):
    return (folder / relative).read_text(encoding='utf-8')


def snapshot(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in folder.rglob('*') if p.is_file()}


def test_course_demo_generation_is_deterministic_and_relative(tmp_path):
    for as_of in (FIXED, today()):
        a, b = tmp_path / f'{as_of}-a', tmp_path / f'{as_of}-b'
        left, right = generate(a, as_of), generate(b, as_of)
        assert left == right
        assert snapshot(a) == snapshot(b)
        assert sorted(snapshot(a)) == sorted(left['files'])
        assert {'01-customers.csv', '02-invoices.csv', '03-bank-statement.csv', '05-later/payments-later.csv',
                '06-refused/patel-conditional.txt', 'START-HERE.md', 'EXPECTED-RESULTS.json'} <= set(left['files'])
        assert json.loads(read(a, 'EXPECTED-RESULTS.json')) == left
        invoices = read(a, '02-invoices.csv').splitlines()[1:]
        assert len(invoices) == 6 == len(left['customers']) == len(left['expected'])
        for line in invoices:
            issued, due = line.split(',')[-2:]
            assert date.fromisoformat(issued) < as_of and date.fromisoformat(due) < as_of
        for line in read(a, '03-bank-statement.csv').splitlines()[1:]:
            assert date.fromisoformat(line.split(',')[0]) < as_of
        # Independent expectation: the future promise is a week ahead and the
        # Hinglish promise four days before the anchor (both by name, not by index).
        def long(d): return f'{d.day} {d.strftime("%B")} {d.year}'
        assert f'we will pay INR 75000 by {long(as_of + timedelta(days=7))}.' in read(a, '04-messages/kaveri-promise.eml')
        assert f'Hum ₹48000 {long(as_of - timedelta(days=8))} ko payment kar denge.' in read(a, '04-messages/meera-whatsapp-hinglish.txt')
        assert {e['invoice_id']: e['action'] for e in left['expected']} == {
            'MT-1001': 'FOLLOW_UP', 'AT-1002': 'VERIFY_PAYMENT', 'SF-1003': 'CLOSE',
            'KP-1004': 'WAIT', 'LE-1005': 'FOLLOW_UP', 'PH-1006': 'FOLLOW_UP'}
        start = read(a, 'START-HERE.md')
        assert start.index('course_demo_pack') < start.index('Clean up')
        for phrase in ('STUB', 'LIVE', 'INR', '₹', 'Assistant', 'Approvals', 'Dashboard', 'payments-later.csv', 'patel-conditional.txt'):
            assert phrase in start, phrase
    # Dates move with the anchor.
    generate(tmp_path / 'shifted', FIXED - timedelta(days=1))
    assert read(tmp_path / f'{FIXED}-a', '02-invoices.csv') != read(tmp_path / 'shifted', '02-invoices.csv')


def test_generator_writes_only_named_files_and_keeps_existing_notes(tmp_path):
    folder = tmp_path / 'pack'
    folder.mkdir()
    (folder / 'presenter-note.txt').write_text('keep me', encoding='utf-8')
    manifest = generate(folder, FIXED)
    assert (folder / 'presenter-note.txt').read_text(encoding='utf-8') == 'keep me'
    assert 'presenter-note.txt' not in manifest['files']


def expected_action(item, as_of):
    """Independent real-clock drift: a 'by' promise is active through its whole IST day."""
    if item['action'] == 'WAIT' and today() > date.fromisoformat(item['promise_by']):
        return 'FOLLOW_UP'
    return item['action']


def coverage(client, did):
    for row in overview(client, did)['cases']:
        state = overview(client, did)
        current = next(c for c in state['cases'] if c['id'] == row['id'])
        response = client.post(f'/api/v1/demonstrations/{did}/intake/ledger-reviews',
                               json=operation(case_id=current['id'], expected_case_revision=current['case_revision'],
                                              reviewed_through=state['as_of'], complete=True, confirm=True), headers=HEADERS)
        assert response.status_code == 200, response.text


def apply_allocations(client, did, allocations):
    for item in allocations:
        state = overview(client, did)
        payment = next(p for p in state['payments'] if p['transaction_ref'] == item['transaction_ref'])
        row = next(c for c in state['cases'] if c['invoice_id'] == item['invoice_id'])
        if item.get('hint_required'):
            assert row['id'] in [c['case_id'] for c in payment['candidates']], payment['candidates']
        response, _ = allocate(client, did, payment, row, item['amount'])
        assert response.status_code == 200, response.text


def morning_review(client, did):
    started = client.post(f'/api/v1/demonstrations/{did}/morning-reviews',
                          json=dict(schema_version='1', operation_id=str(uuid4())), headers=HEADERS)
    assert started.status_code == 202, started.text
    for _ in range(200):
        view = client.get(f"/api/v1/morning-reviews/{started.json()['id']}", params={'demonstration_id': did}).json()
        if view['status'] != 'RUNNING':
            return view
        clock.sleep(0.05)
    raise AssertionError('Morning review did not reach a terminal state')


def cases(client, did):
    response = client.get(f'/api/v1/demonstrations/{did}/cases')
    assert response.status_code == 200, response.text
    return {c['invoice_id']: c for c in response.json()['cases']}


def journey(client, folder, manifest):
    saved, _ = commit(client, 'customers', read(folder, '01-customers.csv'))
    did = saved['demonstration_id']
    commit(client, 'invoices', read(folder, '02-invoices.csv'), did)
    _, bank = preview(client, 'payments', read(folder, '03-bank-statement.csv'), did)
    assert any('Skipped' in w for w in bank['warnings'])
    commit(client, 'payments', read(folder, '03-bank-statement.csv'), did)
    ids = {c['invoice_id']: c['id'] for c in overview(client, did)['cases']}
    for item in manifest['documents']:
        assert item['sender_role'] == 'CUSTOMER'
        commit(client, item['kind'], read(folder, item['path']), did, case_id=ids[item['invoice_id']], sender_role='CUSTOMER')
    apply_allocations(client, did, manifest['allocations'])
    coverage(client, did)
    return did, ids


def app_for(tmp_path, name):
    return create_app(Settings('STUB', 'scripted', tmp_path / f'{name}.sqlite', None))


@pytest.mark.parametrize('anchor', ['fixed', 'today'])
def test_course_demo_journey_produces_every_outcome(tmp_path, anchor):
    as_of = FIXED if anchor == 'fixed' else today()
    folder = tmp_path / 'pack'
    manifest = generate(folder, as_of)
    app = app_for(tmp_path, anchor)
    with TestClient(app, base_url='http://127.0.0.1') as client:
        did, ids = journey(client, folder, manifest)
        review = morning_review(client, did)
        assert review['status'] == 'COMPLETE', review
        listed = cases(client, did)
        observed = {}
        for item in manifest['expected']:
            row = listed[item['invoice_id']]
            observed[item['invoice_id']] = (row['recommended_action'], row['balance'])
            assert row['client'] == item['customer_name']
            assert row['recommended_action'] == expected_action(item, as_of), (item, row)
            assert row['balance'] == dict(currency='INR', minor_units=item['balance_minor']), (item, row)
            assert row['lifecycle'] == 'OPEN'
            view = client.get(f"/api/v1/cases/{ids[item['invoice_id']]}", params={'demonstration_id': did}).json()
            assert view['current_result']['status'] == 'COMPLETE', view['current_result']
            if row['recommended_action'] == 'WAIT':
                boundary = datetime.combine(date.fromisoformat(item['promise_by']) + timedelta(days=1), time.min, IST)
                assert datetime.fromisoformat(row['review_at']) == boundary, row['review_at']
        # START-HERE: Approvals shows Lotus's reminder; drafts keep backend "INR" text.
        lotus = client.get(f"/api/v1/cases/{ids['LE-1005']}", params={'demonstration_id': did}).json()
        assert 'INR 80,000.00' in lotus['draft']['exact_text']
        assert review['briefing'] and 'INR' in review['briefing']
        assert {a for a, _ in observed.values()} >= {'FOLLOW_UP', 'VERIFY_PAYMENT', 'CLOSE'}
        if anchor == 'today':
            assert {a for a, _ in observed.values()} == {'FOLLOW_UP', 'VERIFY_PAYMENT', 'CLOSE', 'WAIT'}

        # The refused conditional message previews with an error and saves nothing.
        refused = manifest['refused'][0]
        before = overview(client, did)
        command, view = preview(client, refused['kind'], read(folder, refused['path']), did,
                                case_id=ids[refused['invoice_id']], sender_role='CUSTOMER')
        assert view['errors'] and 'conditional' in view['errors'][0]['message'].lower(), view['errors']
        command.update(confirmed_preview_hash=view['preview_hash'], confirm=True, fictional_data=True)
        assert client.post('/api/v1/intake/commits', json=command, headers=HEADERS).status_code == 422
        assert overview(client, did) == before
        assert cases(client, did) == listed


def investigate(client, did, cid):
    view = client.get(f'/api/v1/cases/{cid}', params={'demonstration_id': did}).json()
    started = client.post(f'/api/v1/cases/{cid}/investigations', params={'demonstration_id': did}, headers=HEADERS,
                          json=dict(schema_version='1', operation_id=str(uuid4()), expected_case_revision=view['case_revision'], retry_of=None))
    assert started.status_code == 202, started.text
    for _ in range(200):
        view = client.get(f'/api/v1/cases/{cid}', params={'demonstration_id': did}).json()
        if not view['running_attempt']:
            return view
        clock.sleep(0.05)
    raise AssertionError('Investigation did not finish')


def test_course_demo_finale_closes_after_later_statement(tmp_path):
    as_of = today()
    folder = tmp_path / 'pack'
    manifest = generate(folder, as_of)
    app = app_for(tmp_path, 'finale')
    with TestClient(app, base_url='http://127.0.0.1') as client:
        did, ids = journey(client, folder, manifest)
        assert morning_review(client, did)['status'] == 'COMPLETE'
        cid = ids[manifest['finale']['invoice_id']]
        first = client.get(f'/api/v1/cases/{cid}', params={'demonstration_id': did}).json()['latest_completed_result']
        assert first['action'] == 'VERIFY_PAYMENT'
        commit(client, 'payments', read(folder, manifest['finale']['path']), did)
        apply_allocations(client, did, manifest['finale']['allocations'])
        coverage(client, did)
        after = investigate(client, did, cid)
        result = after['current_result']
        assert result['action'] == manifest['finale']['action'] == 'CLOSE'
        assert result['financial_facts']['balance']['minor_units'] == manifest['finale']['balance_minor'] == '0'
        assert all(c['resolved'] for c in result['claims'])
        assert after['latest_completed_result']['investigation_id'] == result['investigation_id'] != first['investigation_id']
        assert after['lifecycle'] == 'OPEN'
        historical = client.get(f"/api/v1/investigations/{first['investigation_id']}", params={'demonstration_id': did}).json()
        assert historical['result'] == first
        assert cases(client, did)[manifest['finale']['invoice_id']]['has_previous_investigation'] is True
        events = client.get(f'/api/v1/cases/{cid}/history', params={'demonstration_id': did, 'limit': 100}).json()['events']
        mentioned = {json.dumps(e['payload']) for e in events}
        assert any(first['investigation_id'] in text for text in mentioned)


def test_checked_in_copy_matches_the_generator_for_its_anchor(tmp_path):
    from pathlib import Path
    checked = Path(__file__).resolve().parents[3] / 'docs/demo-import/course-demo'
    manifest = json.loads(read(checked, 'EXPECTED-RESULTS.json'))
    regenerated = generate(tmp_path / 'pack', date.fromisoformat(manifest['as_of']))
    assert regenerated == manifest
    assert {name: (checked / name).read_bytes() for name in manifest['files']} == snapshot(tmp_path / 'pack')
