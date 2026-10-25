"""Append-only agent activity with per-step usage."""
import sqlite3
from uuid import uuid4
import pytest
from promisekeeper.application.agent_activity import activity_totals, list_agent_activity, record_agent
from promisekeeper.application.cases import create_demonstration
from promisekeeper.persistence.sqlite import Database


def demo(db):
    return create_demonstration(db, dict(schema_version='1', operation_id=str(uuid4()), catalogue_version='release-0.1',
                                         variant_id=None, clock_mode='REFERENCE'))['demonstration_id']


def test_agent_activity_is_append_only_and_ordered(tmp_path):
    with Database(tmp_path/'db.sqlite') as db:
        did = demo(db)
        record_agent(db, demonstration_id=did, case_id=None, agent='SUPERVISOR', event='select', outcome='STARTED', morning_review_id='m1')
        record_agent(db, demonstration_id=did, case_id=None, agent='BRIEFING', event='write', outcome='SUCCEEDED', model='m',
                     input_tokens=10, output_tokens=5, latency_ms=120, morning_review_id='m1')
        with db.connection() as con:
            rows = list_agent_activity(con, morning_review_id='m1')
            assert [r['agent'] for r in rows] == ['SUPERVISOR', 'BRIEFING']
            assert rows[1]['input_tokens'] == 10 and rows[1]['latency_ms'] == 120
            with pytest.raises(sqlite3.IntegrityError):
                con.execute("UPDATE agent_activity SET note='x'")


def test_record_agent_never_raises_into_callers(tmp_path):
    with Database(tmp_path/'db.sqlite') as db:
        record_agent(db, demonstration_id='missing', case_id=None, agent='NOT_AN_AGENT', event='x', outcome='STARTED')


def test_activity_totals_cost_only_with_rates():
    rows = [dict(model='m', input_tokens=1_000_000, output_tokens=500_000, latency_ms=900),
            dict(model=None, input_tokens=None, output_tokens=None, latency_ms=100)]
    assert activity_totals(rows, {'m': (1.0, 2.0)}) == dict(input_tokens=1_000_000, output_tokens=500_000, latency_ms=1000, cost_usd=2.0)
    assert activity_totals(rows, {})['cost_usd'] is None
    assert activity_totals([], {})['cost_usd'] is None


def test_deleting_a_copy_removes_its_agent_activity(tmp_path):
    from promisekeeper.application.cases import delete_demonstration
    with Database(tmp_path/'db.sqlite') as db:
        did = demo(db)
        record_agent(db, demonstration_id=did, case_id=None, agent='SUPERVISOR', event='select', outcome='STARTED', morning_review_id='m1')
        delete_demonstration(db, did, dict(schema_version='1', operation_id=str(uuid4()), confirmed_demonstration_id=did, confirm=True))
        with db.connection() as con:
            assert con.execute('SELECT COUNT(*) FROM agent_activity WHERE demonstration_id=?', (did,)).fetchone()[0] == 0
