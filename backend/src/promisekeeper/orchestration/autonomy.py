"""Opt-in autonomy: the Morning Review supervisor starts itself when cases are due.

Enabled only with PK_AUTONOMOUS_REVIEW_MINUTES (default off). Autonomous runs do exactly what
an owner-started Morning Review does: they read evidence, investigate and prepare drafts. They
never send, approve, close or change money; every such step stays with the owner.
"""
import logging
import threading
from uuid import uuid4

from promisekeeper.application.cases import list_demonstrations
from promisekeeper.application.operations import CommandError
from promisekeeper.orchestration.morning_review import case_decisions, run_morning_review, start_morning_review

_log = logging.getLogger(__name__)


def autonomous_pass(db, agents):
    """Start and run a review for every copy with due cases and no review in progress."""
    started = []
    for demo in list_demonstrations(db)['demonstrations']:
        did = demo['id']
        if not any(reason is None for _, reason in case_decisions(db, did)):
            continue
        try:
            view = start_morning_review(db, did, dict(schema_version='1', operation_id=str(uuid4())), started_by='AUTONOMOUS')
        except CommandError:
            continue
        run_morning_review(db, agents, view['id'])
        started.append(view['id'])
    return started


class AutonomyScheduler:
    def __init__(self, db, agents, *, interval_seconds):
        self.db, self.agents, self.interval = db, agents, interval_seconds
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self._loop, name='promisekeeper-autonomy', daemon=True)

    def _loop(self):
        while not self.stopping.wait(self.interval):
            try:
                autonomous_pass(self.db, self.agents)
            except Exception:
                _log.warning('Autonomous morning review pass failed; the next pass will try again.')

    def start(self):
        self.thread.start()

    def stop(self):
        self.stopping.set()
        self.thread.join(timeout=30)
