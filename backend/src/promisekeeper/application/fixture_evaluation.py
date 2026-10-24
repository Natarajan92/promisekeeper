"""Offline release catalogue evaluation through the saved application workflow.

This is scripted evidence, never LIVE extraction qualification. The reviewed
finding inventory is loaded independently of the product finding derivation.
"""
from copy import deepcopy
from datetime import datetime
import json
import hashlib
from pathlib import Path
import tempfile
import time
from uuid import uuid4

from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.cases import create_demonstration, get_case
from promisekeeper.application.evaluation_findings import load_inventory, score_findings, findings_view, INVENTORY_HASH
from promisekeeper.application.evaluations import evaluation_manifest
from promisekeeper.application.operations import instant, utcnow
from promisekeeper.application.reviews import review_draft
from promisekeeper.application.scenario_updates import preview_event, confirm_event
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.fixtures.catalogue import fresh_copy, apply_event
from promisekeeper.orchestration.investigate import investigate, get_investigation
from promisekeeper.persistence.sqlite import Database

FINANCIAL_INVENTORY_HASH = 'f8b7c6949682569f69f70a6e3fdcda797b27fdd40dd4417186128f8c832fbe9f'
FINANCIAL_INVENTORY_PATH = Path(__file__).resolve().parents[3] / 'tests' / 'evaluations' / 'expected_financial.json'


def load_financial_inventory(entries):
    """Pinned literals authored independently from approved financial sources."""
    raw = FINANCIAL_INVENTORY_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest() != FINANCIAL_INVENTORY_HASH:
        raise ValueError('Expected financial inventory bytes differ from reviewed pin')
    inventory = json.loads(raw)
    if (inventory['inventory_version'] != 'gate-v-financial-1' or inventory['catalogue_version'] != 'release-0.1'
            or len(entries) != 51 or set(inventory['entries']) != {entry['id'] for entry in entries}):
        raise ValueError('Expected financial inventory identity mismatch')
    return inventory['entries']


def financial_correct(actual, expected):
    try:
        if any(actual[key] != expected[key] for key in ('certainty', 'invoice', 'paid', 'balance')):
            return False
        if actual['due_at'] is None or expected['due_at'] is None:
            return actual['due_at'] is expected['due_at']
        return datetime.fromisoformat(actual['due_at']) == datetime.fromisoformat(expected['due_at'])
    except (KeyError, ValueError, TypeError):
        return False


def reserve_report(path):
    """Exclusive creation prevents erasing earlier acceptance evidence."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open('x', encoding='utf-8') as stream:
            stream.write('{}\n')
    except FileExistsError:
        raise ValueError('Report path already exists; choose a new report path') from None
    return path


def write_report(path, report):
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


def command(revision=None, **fields):
    value = dict(schema_version='1', operation_id=str(uuid4()), **fields)
    if revision is not None:
        value['expected_case_revision'] = revision
    return value


class CapturingScripted(ScriptedInvestigator):
    def extract(self, request, *, timeout):
        self.packet = deepcopy(request['packet'])
        return super().extract(request, timeout=timeout)


def _run_entry(db, entry, inventory, financial_inventory=None):
    fixture = fresh_copy(entry['variant'])
    for event in entry['events']:
        fixture = apply_event(fixture, event)
    expected = dict(fixture.cases[entry['case_id']].expected)
    expected['financial_facts'] = (financial_inventory or load_financial_inventory(evaluation_manifest()))[entry['id']]
    did = create_demonstration(db, command(catalogue_version='release-0.1', variant_id=entry['variant'], clock_mode='REFERENCE'))['demonstration_id']
    with db.connection() as con:
        cid = con.execute('SELECT id FROM cases WHERE demonstration_id=? AND catalogue_case_id=?', (did, entry['case_id'])).fetchone()[0]
    for event in entry['events']:
        preview = preview_event(db, did, cid, event)
        confirm_event(db, did, cid, command(preview['expected_case_revision'], event_id=event,
            catalogue_version='release-0.1', confirmed_preview_hash=preview['preview_hash']))
    before = get_case(db, did, cid)
    started = start_investigation(db, did, cid, command(before['case_revision'], retry_of=None), agent_mode='STUB', requested_model=None)
    worker = CapturingScripted()
    investigate(db, started['investigation_id'], worker)
    attempt = get_investigation(db, did, started['investigation_id'])
    view = get_case(db, did, cid)
    result = attempt['result']
    checks = dict(result_present=result is not None, financial_correct=False, action_correct=False,
        review_time_correct=False, draft_correct=False, approval_correct=False)
    actual = None
    if result:
        facts = result['financial_facts']
        checks.update(score_findings(result, worker.packet, inventory))
        checks['financial_correct'] = financial_correct(facts, expected['financial_facts'])
        checks['action_correct'] = result['action'] == expected['action']
        checks['review_time_correct'] = (result['review_at'] is None and expected['review_at'] is None) or (
            result['review_at'] is not None and expected['review_at'] is not None and datetime.fromisoformat(result['review_at']) == datetime.fromisoformat(expected['review_at']))
        draft = view['draft']
        wants_draft = expected['action'] == 'FOLLOW_UP' or (expected['action'] == 'VERIFY_PAYMENT' and any(c['customer_clarification'] and not c['resolved'] for c in result['claims']))
        checks['draft_correct'] = (bool(draft) == wants_draft and view['review_state'] == ('UNAPPROVED' if wants_draft else 'NONE')
            and (not draft or (draft['validation_status'] == 'VALID' and draft['recipient'] == view['client'] and draft['invoice_id'] == view['invoice_id'])))
        if draft and view['allowed_commands']['approve_draft']['allowed']:
            response = review_draft(db, did, cid, command(view['case_revision'], draft_version_id=draft['id'],
                payload_hash=draft['payload_hash'], expected_review_epoch=view['review_epoch'], decision='APPROVE'))
            saved = response['draft_review']
            checks['approval_correct'] = (saved['exact_text'] == draft['exact_text'] and saved['payload_hash'] == draft['payload_hash']
                and saved['recipient'] == draft['recipient'] and saved['draft_version_id'] == draft['id']
                and get_case(db, did, cid)['review_state'] == 'APPROVED')
        else:
            checks['approval_correct'] = not draft and not view['allowed_commands']['approve_draft']['allowed']
        actual = dict(financial_facts=facts, action=result['action'], review_at=result['review_at'],
            findings=findings_view(result), draft=draft, review_state=get_case(db, did, cid)['review_state'])
    return dict(case=entry['id'], expected=expected, actual=actual, checks=checks,
        attempt_status=attempt['status'], failure_code=attempt['failure_code'], passed=all(checks.values()))


def _failure_run(db, behavior, expected_code):
    did = create_demonstration(db, command(catalogue_version='release-0.1', variant_id=None, clock_mode='REFERENCE'))['demonstration_id']
    with db.connection() as con:
        cid = con.execute("SELECT id FROM cases WHERE demonstration_id=? AND catalogue_case_id='PK-001'", (did,)).fetchone()[0]
    initial = start_investigation(db, did, cid, command(get_case(db, did, cid)['case_revision'], retry_of=None), agent_mode='STUB', requested_model=None)
    investigate(db, initial['investigation_id'], ScriptedInvestigator())
    saved = get_case(db, did, cid)['latest_completed_result']
    started = start_investigation(db, did, cid, command(get_case(db, did, cid)['case_revision'], retry_of=None), agent_mode='STUB', requested_model=None)
    begin = time.monotonic()
    worker = ScriptedInvestigator(behavior)
    investigate(db, started['investigation_id'], worker)
    elapsed = time.monotonic() - begin
    attempt = get_investigation(db, did, started['investigation_id'])
    current = get_case(db, did, cid)
    preserved = current['latest_completed_result'] == saved
    safe = attempt['status'] == 'INCOMPLETE' and attempt['result'] is None and attempt['failure_code'] == expected_code
    return dict(preset=behavior, expected_failure_code=expected_code, failure_code=attempt['failure_code'],
        status=attempt['status'], result_present=attempt['result'] is not None, saved_result_preserved=preserved,
        retry_invocations=worker.calls, elapsed_seconds=round(elapsed, 6),
        passed=safe and preserved and elapsed <= 60 and worker.calls <= 2)


def evaluate_fixtures(settings=None, *, catalogue='release-0.1', output):
    if catalogue != 'release-0.1':
        raise ValueError('Unsupported catalogue')
    entries = evaluation_manifest()
    inventory = load_inventory(entries)
    financial_inventory = load_financial_inventory(entries)
    path = reserve_report(output)
    report = dict(schema_version='1', suite='fixtures', catalogue_version=catalogue, agent_mode='STUB',
        inventory_hash=INVENTORY_HASH, started_at=instant(utcnow()), live_qualified=False,
        financial_inventory_hash=FINANCIAL_INVENTORY_HASH,
        qualification_scope='SCRIPTED_CATALOGUE_ONLY', status='RUNNING', passed=False, runs=[], failure_runs=[])
    write_report(path, report)
    root = Path(__file__).resolve().parents[4] / '.runtime' / 'gate-v'
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='fixtures-', dir=root) as directory:
        for number, entry in enumerate(entries):
            with Database(Path(directory) / f'case-{number}.sqlite') as db:
                try:
                    row = _run_entry(db, entry, inventory['entries'][entry['id']], financial_inventory)
                except Exception as exc:
                    row = dict(case=entry['id'], passed=False, error_type=type(exc).__name__, checks={})
                report['runs'].append(row)
                write_report(path, report)
        for behavior, code in [('timeout', 'INVESTIGATOR_TIMEOUT'), ('unavailable', 'INVESTIGATOR_UNAVAILABLE'),
                               ('refusal', 'INVESTIGATOR_REFUSAL'), ('malformed', 'INVALID_INVESTIGATOR_OUTPUT')]:
            with Database(Path(directory) / f'failure-{behavior}.sqlite') as db:
                report['failure_runs'].append(_failure_run(db, behavior, code))
                write_report(path, report)
    report.update(status='COMPLETE', passed=all(row['passed'] for row in [*report['runs'], *report['failure_runs']]), finished_at=instant(utcnow()))
    write_report(path, report)
    return report
