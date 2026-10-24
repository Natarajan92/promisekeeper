"""Read-availability failures must be measured without replaying a command."""
from io import BytesIO
import json
from urllib.error import HTTPError

import pytest


class Clock:
    elapsed = 0.0
    def monotonic(self):
        return self.elapsed
    def sleep(self, seconds):
        self.elapsed += seconds


class StatusClient:
    def __init__(self, clock, *, failures, http_status=503, code='STORAGE_UNAVAILABLE'):
        self.clock = clock
        self.failures = failures
        self.http_status = http_status
        self.code = code
        self.post_calls = 0
        self.status_calls = 0
        self.timeouts = []
    def request(self, path, body=None, *, timeout=5):
        if body is not None:
            self.post_calls += 1
            return {'investigation_id': 'saved-attempt'}
        if path.startswith('/cases/'):
            return {'case_revision': 0}
        self.status_calls += 1
        self.timeouts.append(timeout)
        if self.status_calls <= self.failures:
            # Simulates a busy read consuming its declared request budget.
            self.clock.elapsed += min(2, timeout)
            envelope = {'schema_version': '1', 'error': {'code': self.code, 'retryable': True}}
            raise HTTPError(path, self.http_status, 'Unavailable', {}, BytesIO(json.dumps(envelope).encode()))
        return dict(status='COMPLETE', draft_status='READY', failure_code=None, result={'saved': True})


def test_status_poll_recovers_known_retryable_503_and_retains_observed_latency(monkeypatch):
    from promisekeeper.application import measurements as runner
    clock = Clock()
    monkeypatch.setattr(runner.time, 'monotonic', clock.monotonic)
    monkeypatch.setattr(runner.time, 'sleep', clock.sleep)
    client = StatusClient(clock, failures=2)
    row = runner._attempt(client, 'copy', 'case')
    assert row['status'] == 'COMPLETE'
    assert row['terminal_within_60s']
    assert row['terminal_seconds'] >= 4
    assert row['status_read_attempts'] == 3
    assert row['status_read_retry_count'] == 2
    assert [error['http_status'] for error in row['status_read_errors']] == [503, 503]
    assert [error['code'] for error in row['status_read_errors']] == ['STORAGE_UNAVAILABLE'] * 2
    assert row['status_read_errors'][1]['elapsed_seconds'] > row['status_read_errors'][0]['elapsed_seconds']
    assert client.post_calls == 1


def test_unavailable_status_reads_exhaust_original_sixty_second_deadline_without_fake_terminal(monkeypatch):
    from promisekeeper.application import measurements as runner
    clock = Clock()
    monkeypatch.setattr(runner.time, 'monotonic', clock.monotonic)
    monkeypatch.setattr(runner.time, 'sleep', clock.sleep)
    client = StatusClient(clock, failures=1000)
    row = runner._attempt(client, 'copy', 'case', replay=True)
    assert row['status'] == 'UNOBSERVED'
    assert row['terminal_within_60s'] is False
    assert row['measurement_failure_code'] == 'STATUS_READ_DEADLINE'
    assert row['result_present'] is None
    assert row['terminal_seconds'] == pytest.approx(60)
    assert clock.elapsed == pytest.approx(60)
    assert row['status_read_retry_count'] == client.status_calls
    assert client.timeouts[-1] < 2
    assert client.post_calls == 1


@pytest.mark.parametrize('status,code', [(400, 'INVALID_REQUEST'), (503, 'UNRECOGNIZED_ERROR')])
def test_status_poll_does_not_retry_unrecognized_or_nonretryable_http_failures(monkeypatch, status, code):
    from promisekeeper.application import measurements as runner
    clock = Clock()
    monkeypatch.setattr(runner.time, 'monotonic', clock.monotonic)
    monkeypatch.setattr(runner.time, 'sleep', clock.sleep)
    client = StatusClient(clock, failures=1000, http_status=status, code=code)
    with pytest.raises(HTTPError):
        runner._attempt(client, 'copy', 'case')
    assert client.post_calls == 1
    assert client.status_calls == 1
