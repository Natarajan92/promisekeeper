"""Registered, offline test faults. Never imported by the packaged application.

Crash hooks stop only at a fixed committed event in an owned temporary database.
No HTTP control endpoints, SQL from requests, arbitrary sleeps or provider calls.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import threading
import time

from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.agents.scripted import ScriptedInvestigator

COMMIT_BOUNDARIES = {
    'kill-after-start': 'INVESTIGATION_STARTED',
    'kill-after-result': 'INVESTIGATION_COMPLETED',
    'kill-after-draft': 'DRAFT_SAVED',
    'kill-after-approval': 'DRAFT_REVIEWED',
    'kill-after-closure': 'CASE_CLOSED',
}
PROVIDER_PRESETS = ('retry-exhaustion', 'late-provider', 'blocked-provider')
REGISTERED_PRESETS = (*COMMIT_BOUNDARIES, *PROVIDER_PRESETS)


class FaultInvestigator(ScriptedInvestigator):
    def __init__(self, preset, observe=None):
        if preset not in PROVIDER_PRESETS:
            raise ValueError('Unregistered provider fault preset')
        super().__init__()
        self.preset, self.observe = preset, observe or (lambda **fields: None)
        self.provider_calls = self.provider_returns = 0

    def extract(self, request, *, timeout):
        self.provider_calls += 1
        self.observe(provider_calls=self.provider_calls)
        if self.preset == 'retry-exhaustion':
            time.sleep(.15)
            raise InvestigatorFailure('INVESTIGATOR_UNAVAILABLE', transient=True)
        time.sleep(45 if self.preset == 'late-provider' else 65)
        response = super().extract(request, timeout=timeout)
        self.provider_returns += 1
        self.observe(provider_returns=self.provider_returns)
        return response


def install_fault_scenario(app, preset, marker_path):
    """Install a fixed preset in an isolated test process before app startup."""
    if preset not in REGISTERED_PRESETS:
        raise ValueError('Unregistered fault preset')
    marker = Path(marker_path).resolve()
    database = app.state.settings.db_path.resolve()
    if marker.parent != database.parent or database.name != 'fresh.sqlite':
        raise ValueError('Fault controls require the isolated fresh.sqlite directory')
    metadata = dict(preset=preset, provider_calls=0, provider_returns=0)
    lock = threading.Lock()

    def observe(**fields):
        with lock:
            metadata.update(fields)
            temporary = marker.with_suffix('.tmp')
            temporary.write_text(json.dumps(metadata), encoding='utf-8')
            temporary.replace(marker)

    if preset in PROVIDER_PRESETS:
        observe()
        app.state.investigator = FaultInvestigator(preset, observe)
        return
    from promisekeeper.persistence.sqlite import Database
    original = Database.transaction
    event_type = COMMIT_BOUNDARIES[preset]

    @contextmanager
    def transaction(db):
        event = None
        with original(db) as con:
            before = con.execute('SELECT COALESCE(MAX(rowid),0) FROM case_events').fetchone()[0]
            yield con
            event = con.execute('SELECT event_type FROM case_events WHERE rowid>? AND event_type=? LIMIT 1',
                                (before, event_type)).fetchone()
        # The original context returned only after synchronous=EXTRA COMMIT succeeded.
        if db.path == database and event is not None and not marker.exists():
            observe(event=event[0], committed=True)
            os._exit(87)

    Database.transaction = transaction
