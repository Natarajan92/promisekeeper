"""Opt-in autonomy: the supervisor starts a morning review by itself when cases are due."""
import time
from uuid import uuid4
import pytest
from promisekeeper.agents.briefing import ScriptedBriefing
from promisekeeper.agents.communicator import ScriptedCommunicator
from promisekeeper.agents.reviewer import ScriptedReviewer
from promisekeeper.agents.roster import AgentSet
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.cases import create_demonstration
from promisekeeper.config import load_settings
from promisekeeper.orchestration.autonomy import AutonomyScheduler, autonomous_pass
from promisekeeper.orchestration.morning_review import get_morning_review, start_morning_review
from promisekeeper.persistence.sqlite import Database


def agents():
    return AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), ScriptedBriefing())


def demo(db):
    return create_demonstration(db, dict(schema_version='1', operation_id=str(uuid4()), catalogue_version='release-0.1',
                                         variant_id=None, clock_mode='REFERENCE'))['demonstration_id']


def test_autonomous_pass_reviews_only_when_cases_are_due(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        started = autonomous_pass(db, agents())
        assert len(started) == 1
        review = get_morning_review(db, did, started[0])
        assert review['status'] == 'COMPLETE' and review['started_by'] == 'AUTONOMOUS'
        assert 'automatically' in review['agent_activity'][0]['note']
        assert autonomous_pass(db, agents()) == []


def test_autonomous_pass_never_overlaps_a_running_review(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        start_morning_review(db, did, dict(schema_version='1', operation_id=str(uuid4())))
        assert autonomous_pass(db, agents()) == []


def test_autonomy_is_off_by_default_and_validated(tmp_path):
    assert load_settings({}, workspace=tmp_path).autonomous_review_minutes == 0
    assert load_settings({'PK_AUTONOMOUS_REVIEW_MINUTES': '30'}, workspace=tmp_path).autonomous_review_minutes == 30
    for bad in ('-1', 'often', '2000'):
        with pytest.raises(ValueError):
            load_settings({'PK_AUTONOMOUS_REVIEW_MINUTES': bad}, workspace=tmp_path)
    summary = load_settings({'PK_AUTONOMOUS_REVIEW_MINUTES': '30'}, workspace=tmp_path).safe_summary()
    assert summary['autonomous_review_minutes'] == 30


def test_scheduler_runs_in_background_and_stops(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        scheduler = AutonomyScheduler(db, agents(), interval_seconds=0.05)
        scheduler.start()
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                with db.connection() as con:
                    if con.execute("SELECT 1 FROM morning_reviews WHERE demonstration_id=? AND status='COMPLETE'", (did,)).fetchone():
                        break
                time.sleep(0.05)
            else:
                pytest.fail('autonomous review did not complete')
        finally:
            scheduler.stop()
        assert not scheduler.thread.is_alive()
