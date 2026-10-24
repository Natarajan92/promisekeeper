"""Reproducible local HTTP timing and exact subprocess restart measurements.

Release runs require the frozen LIVE provider. Offline tests may exercise the
same private harness with STUB; those runs are never acceptance reports.
"""
from contextlib import closing, contextmanager
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from promisekeeper.application.fixture_evaluation import command, reserve_report, write_report
from promisekeeper.application.operations import instant, utcnow

FROZEN_MODEL = 'zai-org/GLM-5.3-Flash'
ROOT = Path(__file__).resolve().parents[4]
TABLES = ('demonstrations', 'cases', 'evidence_versions', 'evidence_snapshots', 'investigations',
          'investigation_results', 'step_attempts', 'draft_generation_attempts', 'draft_versions',
          'draft_reviews', 'owner_dispositions', 'case_events', 'operation_receipts', 'operation_tombstones',
          'invoice_projections', 'payment_projections', 'commitment_anchors', 'commitment_attributions')


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def _snapshot(path):
    """Read complete canonical saved rows; counts alone cannot prove integrity."""
    with closing(sqlite3.connect(f'{Path(path).as_uri()}?mode=ro', uri=True)) as con:
        con.row_factory = sqlite3.Row
        con.execute('BEGIN')
        return {table: [dict(row) for row in con.execute(f'SELECT * FROM {table} ORDER BY rowid')] for table in TABLES}


def _counts(snapshot):
    return {table: len(rows) for table, rows in snapshot.items()}


MUTABLE_CASE_COLUMNS = frozenset({'lifecycle', 'case_revision', 'evidence_revision', 'review_epoch',
    'latest_completed_investigation_id', 'current_draft_version_id', 'next_event_sequence'})


def _prior_immutable_rows_preserved(previous, current):
    """Existing saved rows remain byte-exact while legitimate rows append.

    Only explicitly mutable case state/revision/head columns may evolve. All
    previously terminal attempts, source projections, results, exact reviews,
    closure events, operation receipts and their ordering remain immutable.
    """
    for table in TABLES:
        before, after = previous[table], current[table]
        if len(after) < len(before):
            return False
        if table == 'cases':
            before = [{k: v for k, v in row.items() if k not in MUTABLE_CASE_COLUMNS} for row in before]
            after = [{k: v for k, v in row.items() if k not in MUTABLE_CASE_COLUMNS} for row in after]
        if before != after[:len(before)]:
            return False
    return True


def _replay_unchanged(before, dbpath):
    return before == _snapshot(dbpath)


class LocalHTTP:
    def __init__(self, port):
        self.base = f'http://127.0.0.1:{port}/api/v1'

    def request(self, path, body=None, *, timeout=5):
        data = None if body is None else json.dumps(body).encode()
        request = Request(self.base + path, data=data, headers={
            'Content-Type': 'application/json', 'X-PromiseKeeper-Request': '1'})
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)


@contextmanager
def _server(settings, dbpath):
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    # No credential is placed in argv or written to a temporary configuration.
    env = dict(os.environ)
    env['PYTHONPATH'] = str(ROOT / 'backend' / 'src')
    process = subprocess.Popen([sys.executable, '-m', __name__, '--child-server', str(dbpath),
        str(port), settings.agent_mode, settings.model], cwd=ROOT, env=env,
        stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    client = LocalHTTP(port)
    try:
        deadline = time.monotonic() + 20
        while True:
            if process.poll() is not None:
                raise RuntimeError('Isolated service failed to start')
            try:
                health = client.request('/health', timeout=1)
                if health['ready']:
                    if health['agent_mode'] != settings.agent_mode or health['configuration']['model'] != settings.model:
                        raise RuntimeError('Isolated service configuration differs')
                    break
            except (URLError, TimeoutError):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError('Isolated service readiness timeout')
            time.sleep(.05)
        yield client
    finally:
        if process.stdin:
            try:
                process.stdin.write(b'stop\n')
                process.stdin.flush()
            except (BrokenPipeError, OSError):
                pass
            process.stdin.close()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def _seed(client):
    did = client.request('/demonstrations', command(catalogue_version='release-0.1', variant_id=None, clock_mode='REFERENCE'))['demonstration_id']
    cases = client.request(f'/demonstrations/{did}/cases')['cases']
    return did, {row['catalogue_case_id']: row['id'] for row in cases}


def _case(client, did, cid):
    return client.request(f'/cases/{cid}?demonstration_id={did}')


def _attempt(client, did, cid, *, replay=False, dbpath=None):
    view = _case(client, did, cid)
    request = command(view['case_revision'], retry_of=None)
    begin = time.monotonic()
    receipt = client.request(f'/cases/{cid}/investigations?demonstration_id={did}', request)
    acknowledgement = time.monotonic() - begin
    iid = receipt['investigation_id']
    duplicate_ok = True
    terminal = None
    status_errors = []
    read_attempts = 0
    deadline = begin + 60
    observed_terminal = False
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        timeout = min(2, remaining)
        read_attempts += 1
        try:
            terminal = client.request(f'/investigations/{iid}?demonstration_id={did}', timeout=timeout)
        except HTTPError as exc:
            # A busy local read is not a failed or missing saved command. Only
            # typed transient GET errors may be retried within the original
            # deadline; no command is automatically submitted again.
            if exc.code != 503:
                raise
            try:
                error = json.loads(exc.read(4096))['error']
            except (ValueError, KeyError, TypeError):
                raise exc
            if error.get('retryable') is not True or error.get('code') not in {'STORAGE_UNAVAILABLE', 'RECOVERY_IN_PROGRESS'}:
                raise
            status_errors.append(dict(http_status=exc.code, code=error['code'], retryable=True,
                elapsed_seconds=round(time.monotonic() - begin, 6), poll_timeout_seconds=round(timeout, 6)))
        else:
            if terminal['status'] in {'COMPLETE', 'LIMITED', 'INCOMPLETE'} and terminal['draft_status'] != 'RUNNING':
                observed_terminal = True
                break
        remaining = deadline - time.monotonic()
        if remaining > 0:
            time.sleep(min(.05, remaining))
    elapsed = time.monotonic() - begin
    replayed_mutations = 0
    if replay and observed_terminal:
        before_replay = _snapshot(dbpath) if dbpath else None
        duplicate_ok = client.request(f'/cases/{cid}/investigations?demonstration_id={did}', request) == receipt
        if dbpath:
            after_replay = _snapshot(dbpath)
            replayed_mutations = sum(before_replay[table] != after_replay[table] for table in TABLES)
    elif replay:
        duplicate_ok = False
    provenance = {}
    if dbpath and observed_terminal:
        saved = next(row for row in _snapshot(dbpath)['investigations'] if row['id'] == iid)
        provenance = dict(returned_model=saved['returned_model'], response_id=saved['response_id'])
    return dict(investigation_id=iid, acknowledgement_seconds=round(acknowledgement, 6),
        terminal_seconds=round(elapsed, 6), status=terminal['status'] if terminal else 'UNOBSERVED',
        failure_code=terminal['failure_code'] if terminal else None,
        result_present=terminal['result'] is not None if observed_terminal else None, duplicate_receipt_correct=duplicate_ok,
        replayed_mutations=replayed_mutations,
        status_read_attempts=read_attempts, status_read_retry_count=len(status_errors), status_read_errors=status_errors,
        measurement_failure_code=None if observed_terminal and elapsed <= 60 else 'STATUS_READ_DEADLINE',
        **provenance,
        terminal_within_60s=observed_terminal and elapsed <= 60)


def _responsiveness(settings, path, report, dbpath):
    with _server(settings, dbpath) as client:
        did, cases = _seed(client)
        for cid, identifier in cases.items():
            for trial in range(1, 11):
                begin = time.monotonic()
                view = _case(client, did, identifier)
                opened = time.monotonic() - begin
                row = dict(case=cid, trial=trial, open_seconds=round(opened, 6),
                    saved_information_present=bool(view['evidence']))
                try:
                    row.update(_attempt(client, did, identifier))
                    saved = next(r for r in _snapshot(dbpath)['investigations'] if r['id'] == row['investigation_id'])
                    row.update(returned_model=saved['returned_model'], response_id=saved['response_id'],
                        provider_model_correct=saved['returned_model'] is None or saved['returned_model'] == settings.model)
                except Exception as exc:
                    row.update(error_type=type(exc).__name__, terminal_within_60s=False)
                report['runs'].append(row)
                write_report(path, report)
    opens = sum(r['open_seconds'] <= 3 and r['saved_information_present'] for r in report['runs'])
    acks = sum(r.get('acknowledgement_seconds', float('inf')) <= 2 for r in report['runs'])
    report.update(opens_within_3s=opens, acknowledgements_within_2s=acks,
        passed=len(report['runs']) == 30 and opens >= 29 and acks >= 29 and all(r['terminal_within_60s'] and r.get('provider_model_correct', False) for r in report['runs']))
    report['measurement_scope'] = 'LOCAL_HTTP_SAVED_DATA_AND_ACKNOWLEDGEMENT'
    report['browser_paint_measured'] = False


def _review(client, did, cid, *, dbpath):
    view = _case(client, did, cid)
    draft = view['draft']
    if not draft or not view['allowed_commands']['approve_draft']['allowed']:
        return False
    request = command(view['case_revision'], draft_version_id=draft['id'], payload_hash=draft['payload_hash'],
        expected_review_epoch=view['review_epoch'], decision='APPROVE')
    response = client.request(f'/cases/{cid}/draft-reviews?demonstration_id={did}', request)
    before_replay = _snapshot(dbpath)
    replay = client.request(f'/cases/{cid}/draft-reviews?demonstration_id={did}', request)
    replay_preserved = _replay_unchanged(before_replay, dbpath)
    return replay_preserved and response == replay and response['draft_review']['exact_text'] == draft['exact_text'] and _case(client, did, cid)['review_state'] == 'APPROVED'


def _settle_and_close(client, did, cid, *, dbpath):
    event = 'PK-003-U1'
    preview = client.request(f'/cases/{cid}/scenario-events/{event}/preview?demonstration_id={did}')
    client.request(f'/cases/{cid}/scenario-events?demonstration_id={did}', command(preview['expected_case_revision'],
        event_id=event, catalogue_version='release-0.1', confirmed_preview_hash=preview['preview_hash']))
    outcome = _attempt(client, did, cid, replay=True, dbpath=dbpath)
    view = _case(client, did, cid)
    if not view['allowed_commands']['close']['allowed']:
        return False
    request = command(view['case_revision'], investigation_id=outcome['investigation_id'],
        confirmed_result_hash=view['current_result']['result_hash'], confirm=True)
    response = client.request(f'/cases/{cid}/closure?demonstration_id={did}', request)
    before_replay = _snapshot(dbpath)
    replay = client.request(f'/cases/{cid}/closure?demonstration_id={did}', request)
    return (_replay_unchanged(before_replay, dbpath) and outcome['replayed_mutations'] == 0
        and response == replay and _case(client, did, cid)['lifecycle'] == 'CLOSED')


def _preservation(settings, path, report, dbpath):
    with _server(settings, dbpath) as client:
        did, cases = _seed(client)
        closure = _settle_and_close(client, did, cases['PK-003'], dbpath=dbpath)
        previous = _snapshot(dbpath)
    for cycle in range(1, 11):
        with _server(settings, dbpath) as client:
            attempt = _attempt(client, did, cases['PK-001'], replay=True, dbpath=dbpath)
            approved = _review(client, did, cases['PK-001'], dbpath=dbpath)
            before_views = {cid: _case(client, did, identifier) for cid, identifier in cases.items()}
            # Leaving and reloading must preserve the complete saved projection.
            reloaded = {cid: _case(client, did, identifier) for cid, identifier in cases.items()}
            before = _snapshot(dbpath)
        with _server(settings, dbpath) as client:
            after_views = {cid: _case(client, did, identifier) for cid, identifier in cases.items()}
            after = _snapshot(dbpath)
        model_correct = all(row['returned_model'] is None or row['returned_model'] == settings.model for row in after['investigations'])
        duplicates = dict(evidence_versions=len(before['evidence_versions']) - len({(r['case_id'], r['stable_source_id'], r['version']) for r in before['evidence_versions']}),
            investigations=len(before['investigations']) - len({r['operation_id'] for r in before['investigations']}),
            reviews=len(before['draft_reviews']) - len({r['operation_id'] for r in before['draft_reviews']}),
            event_sequences=len(before['case_events']) - len({(r['case_id'], r['sequence']) for r in before['case_events']}),
            replayed_mutations=attempt['replayed_mutations'])
        row = dict(cycle=cycle, attempt=attempt, draft_review_correct=approved, closure_recorded=closure,
            leave_reload_exact=before_views == reloaded, restart_projection_exact=before_views == after_views,
            canonical_saved_rows_exact=before == after, before_hash=_digest(before), after_hash=_digest(after),
            counts=_counts(after), duplicate_counts=duplicates, provider_model_correct=model_correct)
        row['prior_immutable_rows_preserved'] = (_prior_immutable_rows_preserved(previous, before)
            and _prior_immutable_rows_preserved(previous, after))
        row['prior_immutable_hash'] = _digest(previous)
        row['expected_counts_correct'] = (len(after['evidence_versions']) == 10 and len(after['investigations']) == cycle + 1
            and len(after['investigation_results']) == cycle + 1 and len(after['draft_reviews']) == cycle
            and sum(event['event_type'] == 'CASE_CLOSED' for event in after['case_events']) == 1)
        row['passed'] = (approved and closure and attempt['terminal_within_60s'] and attempt['duplicate_receipt_correct']
            and row['leave_reload_exact'] and row['restart_projection_exact'] and row['canonical_saved_rows_exact']
            and model_correct and row['expected_counts_correct'] and row['prior_immutable_rows_preserved']
            and all(count == 0 for count in duplicates.values()))
        report['runs'].append(row)
        write_report(path, report)
        previous = after
    report.update(passed=len(report['runs']) == 10 and all(r['passed'] for r in report['runs']),
        measurement_scope='SAVED_EVIDENCE_RESULTS_DRAFT_REVIEWS_CLOSURE_EVENTS_EXACT_ROWS',
        unsaved_editor_state='EXCLUDED: browser-local unsaved text is not a saved backend object; separate UI tests required')


def measure(settings, *, suite, report, trials_per_case=10, cycles=10):
    if suite not in {'responsiveness', 'preservation'}:
        raise ValueError('Unsupported measurement suite')
    if type(trials_per_case) is not int or trials_per_case != 10 or type(cycles) is not int or cycles != 10:
        raise ValueError('Release measurements require exactly 10 trials per case and 10 cycles')
    if settings.agent_mode != 'LIVE' or settings.provider != 'NEBIUS' or settings.model != FROZEN_MODEL:
        raise ValueError('Release measurements require LIVE NEBIUS with the frozen model')
    if not settings.api_key:
        raise ValueError('LIVE capability unavailable')
    path = reserve_report(report)
    result = dict(schema_version='1', suite=suite, agent_mode='LIVE', provider='NEBIUS', requested_model=settings.model,
        catalogue_version='release-0.1', clock_mode='REFERENCE',
        workers=1, fresh_database=True, retained_database=None, transport='loopback HTTP subprocess',
        environment=dict(python=platform.python_version(), platform=platform.platform(), executable=Path(sys.executable).name),
        started_at=instant(utcnow()), status='RUNNING', passed=False, runs=[],
        thresholds=dict(opens_required=29, opens_total=30, open_seconds=3, acknowledgements_required=29,
            acknowledgements_total=30, acknowledgement_seconds=2, terminal_seconds=60, preservation_cycles=10),
        live_quality_qualified=False)
    write_report(path, result)
    runroot = ROOT / '.runtime' / 'gate-v'
    runroot.mkdir(parents=True, exist_ok=True)
    runtime_directory = None
    try:
        with tempfile.TemporaryDirectory(prefix=f'{suite}-', dir=runroot) as directory:
            runtime_directory = Path(directory)
            runner = _responsiveness if suite == 'responsiveness' else _preservation
            runner(settings, path, result, Path(directory) / 'measurement.sqlite')
            saved = _snapshot(Path(directory) / 'measurement.sqlite')
            result['provider_responses'] = [dict(investigation_id=row['id'], requested_model=row['requested_model'],
                returned_model=row['returned_model'], response_id=row['response_id'], status=row['status']) for row in saved['investigations']]
    except Exception as exc:
        result.update(status='FAILED', error_type=type(exc).__name__, passed=False)
    else:
        result['status'] = 'COMPLETE'
    result['retained_database'] = runtime_directory.exists() if runtime_directory else False
    result['finished_at'] = instant(utcnow())
    write_report(path, result)
    return result


def _child_server(dbpath, port, mode, model):
    from promisekeeper.config import Settings, load_settings
    from promisekeeper.api.app import create_app
    import uvicorn
    if mode == 'LIVE':
        settings = replace(load_settings(), agent_mode='LIVE', db_path=Path(dbpath), model=model)
        if settings.provider != 'NEBIUS' or model != FROZEN_MODEL or not settings.api_key:
            raise ValueError('LIVE configuration unavailable')
    elif mode == 'STUB':
        settings = Settings('STUB', model, Path(dbpath), None)
    else:
        raise ValueError('Invalid child mode')
    server = uvicorn.Server(uvicorn.Config(create_app(settings), host='127.0.0.1', port=int(port),
        workers=1, log_level='critical', access_log=False, timeout_graceful_shutdown=2))
    def stop_on_parent_close():
        sys.stdin.buffer.readline()
        server.should_exit = True
    threading.Thread(target=stop_on_parent_close, daemon=True).start()
    server.run()


if __name__ == '__main__':
    if len(sys.argv) != 6 or sys.argv[1] != '--child-server':
        raise SystemExit('Internal measurement service entry point')
    _child_server(*sys.argv[2:])
