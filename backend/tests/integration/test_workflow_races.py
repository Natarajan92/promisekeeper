"""Whole-workflow concurrency contracts against independently opened SQLite connections."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.cases import get_case
from promisekeeper.application.lifecycle import close_case
from promisekeeper.application.operations import CommandError, lookup_receipt
from promisekeeper.application.reviews import review_draft, save_draft
from promisekeeper.application.scenario_updates import confirm_event, preview_event
from promisekeeper.application.start_investigation import finish_incomplete, start_investigation
from promisekeeper.orchestration.investigate import get_investigation, investigate
from promisekeeper.persistence.repositories import history
from promisekeeper.persistence.sqlite import Database
from support.closed_conflict import CLOSED_CONFLICT_EVENT, install_closed_conflict_event
from support.lifecycle import close_ready, closure, command
from test_investigation_pipeline import create, start


def race(*calls):
    """Release all callers together; exceptions outside the command contract fail the test."""
    barrier = Barrier(len(calls))

    def invoke(call):
        barrier.wait(timeout=10)
        try:
            return call()
        except CommandError as exc:
            return exc.code

    with ThreadPoolExecutor(len(calls)) as pool:
        futures = [pool.submit(invoke, call) for call in calls]
        return [future.result(timeout=20) for future in futures]


def ready(db):
    did, rows = create(db)
    cid = rows[0]['id']
    assert investigate(db, start(db, did, rows[0]), ScriptedInvestigator())
    return did, cid, get_case(db, did, cid)


def approval(view, **changes):
    return command(view, draft_version_id=view['draft']['id'], payload_hash=view['draft']['payload_hash'],
                   expected_review_epoch=view['review_epoch'], decision='APPROVE') | changes


def edit(view, **changes):
    draft = view['draft']
    return command(view, investigation_id=draft['investigation_id'], parent_version_id=draft['id'],
                   recipient=draft['recipient'], exact_text=draft['exact_text'].replace('Hello', 'Hi')) | changes


def evidence(db, did, cid, event='PK-001-U1'):
    preview = preview_event(db, did, cid, event)
    return dict(schema_version='1', operation_id=str(uuid4()), expected_case_revision=preview['expected_case_revision'],
                event_id=event, catalogue_version=preview['catalogue_version'], confirmed_preview_hash=preview['preview_hash'])


@pytest.mark.parametrize('contenders', [('approve', 'edit'), ('approve', 'start'), ('evidence', 'start'),
                                       ('evidence', 'edit'), ('approve', 'edit', 'evidence', 'start')])
def test_same_revision_race_has_one_durable_winner_and_no_stale_side_effects(tmp_path, contenders):
    # Removing any command's revision fence permits a second contradictory winner.
    with Database(tmp_path / 'race.sqlite') as db:
        did, cid, before = ready(db)
        old_result, old_draft = before['current_result'], before['draft']
        original_history = history(db, did, cid)['events']
        bodies = dict(approve=approval(before), edit=edit(before), evidence=evidence(db, did, cid),
                      start=command(before, retry_of=None))
        handlers = dict(approve=review_draft, edit=save_draft, evidence=confirm_event, start=start_investigation)
        outcomes = race(*(lambda name=name: handlers[name](db, did, cid, bodies[name]) for name in contenders))
        winners = [name for name, result in zip(contenders, outcomes) if isinstance(result, dict)]
        assert len(winners) == 1, outcomes
        winner = winners[0]
        assert all(result in {'REVISION_CONFLICT', 'INVESTIGATOR_BUSY'} for result in outcomes if isinstance(result, str))
        after = get_case(db, did, cid)
        assert after['case_revision'] == before['case_revision'] + 1
        assert after['latest_completed_result'] == old_result
        assert history(db, did, cid)['events'][:len(original_history)] == original_history
        for name, outcome in zip(contenders, outcomes):
            if name == winner:
                assert lookup_receipt(db, did, bodies[name]['operation_id']) == outcome
                assert handlers[name](db, did, cid, bodies[name]) == outcome
            else:
                with pytest.raises(CommandError, match='NOT_RECORDED'):
                    lookup_receipt(db, did, bodies[name]['operation_id'])
        assert len(after['draft_reviews']) == int(winner == 'approve')
        assert (after['draft']['id'] != old_draft['id']) == (winner == 'edit')
        assert after['evidence_revision'] == before['evidence_revision'] + int(winner == 'evidence')
        with db.connection() as con:
            assert con.execute("SELECT count(*) FROM investigations WHERE status='RUNNING'").fetchone()[0] == int(winner == 'start')
            assert con.execute('PRAGMA foreign_key_check').fetchall() == []
        if winner == 'start':
            started = outcomes[contenders.index('start')]
            assert finish_incomplete(db, started['investigation_id'], 'SCRIPTED_FAILURE')
        assert db.capacity.available


@pytest.mark.parametrize('op', ['approve', 'edit', 'evidence', 'close'])
def test_simultaneous_transport_replays_commit_one_receipt_and_one_domain_event(tmp_path, op):
    # Replaying only after revision checks would reject the second successful transport repeat.
    path = tmp_path / 'replay.sqlite'
    with Database(path) as db:
        did, cid, before = close_ready(db) if op == 'close' else ready(db)
        if op == 'close':
            handler, body, event_type = close_case, closure(before), 'CASE_CLOSED'
        elif op == 'approve':
            handler, body, event_type = review_draft, approval(before), 'DRAFT_REVIEWED'
        elif op == 'edit':
            handler, body, event_type = save_draft, edit(before), 'DRAFT_SAVED'
        else:
            handler, body, event_type = confirm_event, evidence(db, did, cid), 'SCENARIO_EVENT_CONFIRMED'
        results = race(lambda: handler(db, did, cid, body), lambda: handler(db, did, cid, body))
        assert isinstance(results[0], dict) and results[0] == results[1]
        after = get_case(db, did, cid)
        assert after['case_revision'] == before['case_revision'] + 1
        with db.connection() as con:
            assert con.execute('SELECT count(*) FROM operation_receipts WHERE operation_id=?', (body['operation_id'],)).fetchone()[0] == 1
            assert con.execute('SELECT count(*) FROM case_events WHERE operation_id=? AND event_type=?',
                               (body['operation_id'], event_type)).fetchone()[0] == 1
    with Database(path) as db:
        assert get_case(db, did, cid) == after
        assert handler(db, did, cid, body) == results[0]
        with pytest.raises(CommandError, match='OPERATION_PAYLOAD_MISMATCH'):
            handler(db, did, cid, body | {'expected_case_revision': after['case_revision']})


@pytest.mark.parametrize('op', ['start', 'evidence'])
def test_exact_settlement_closure_races_cannot_close_a_running_or_changed_case(tmp_path, monkeypatch, op):
    install_closed_conflict_event(monkeypatch)
    with Database(tmp_path / 'close.sqlite') as db:
        did, cid, before = close_ready(db)
        original_result = before['current_result']
        close_body = closure(before)
        if op == 'start':
            handler, other_body = start_investigation, command(before, retry_of=None)
        else:
            handler, other_body = confirm_event, evidence(db, did, cid, CLOSED_CONFLICT_EVENT['id'])
        closed, other = race(lambda: close_case(db, did, cid, close_body), lambda: handler(db, did, cid, other_body))
        assert sum(isinstance(value, dict) for value in (closed, other)) == 1
        assert (other if isinstance(closed, dict) else closed) == 'REVISION_CONFLICT'
        view = get_case(db, did, cid)
        assert view['latest_completed_result'] == original_result
        assert view['lifecycle'] == ('CLOSED' if isinstance(closed, dict) else 'OPEN')
        if isinstance(other, dict):
            with pytest.raises(CommandError, match='REVISION_CONFLICT'):
                close_case(db, did, cid, close_body)
            with pytest.raises(CommandError, match='INVESTIGATION_RUNNING' if op == 'start' else 'EVIDENCE_CHANGED'):
                close_case(db, did, cid, command(view, investigation_id=original_result['investigation_id'],
                    confirmed_result_hash=original_result['result_hash'], confirm=True))
            if op == 'start':
                finish_incomplete(db, other['investigation_id'], 'SCRIPTED_FAILURE')
                close_case(db, did, cid, closure(get_case(db, did, cid)))
            else:
                assert investigate(db, start_investigation(db, did, cid, command(view, retry_of=None))['investigation_id'], ScriptedInvestigator())
                assert get_case(db, did, cid)['current_result']['action'] == 'VERIFY_PAYMENT'
        with db.connection() as con:
            assert con.execute("SELECT count(*) FROM case_events WHERE case_id=? AND event_type='CASE_CLOSED'", (cid,)).fetchone()[0] == int(op == 'start' or isinstance(closed, dict))


def test_cross_copy_case_starts_share_one_slot_and_manual_recovery_is_a_new_attempt(tmp_path):
    path = tmp_path / 'capacity.sqlite'
    with Database(path) as db:
        a, a_rows = create(db)
        b, b_rows = create(db)
        targets = [(a, a_rows[0]['id']), (b, b_rows[1]['id'])]
        bodies = [command(get_case(db, did, cid), retry_of=None) for did, cid in targets]
        results = race(*(lambda index=index: start_investigation(db, *targets[index], bodies[index]) for index in range(2)))
        assert sum(isinstance(result, dict) for result in results) == 1
        assert [result for result in results if isinstance(result, str)] == ['INVESTIGATOR_BUSY']
        winner = next(index for index, result in enumerate(results) if isinstance(result, dict))
        did, cid = targets[winner]
        started = results[winner]
        assert start_investigation(db, did, cid, bodies[winner]) == started
        assert not investigate(db, started['investigation_id'], ScriptedInvestigator('unavailable'))
        assert get_investigation(db, did, started['investigation_id'])['status'] == 'INCOMPLETE'
        assert start_investigation(db, did, cid, bodies[winner]) == started
        recovery_body = command(get_case(db, did, cid), retry_of=started['investigation_id'])
        recovery = start_investigation(db, did, cid, recovery_body)
        assert recovery['investigation_id'] != started['investigation_id']
        assert recovery['snapshot_id'] != started['snapshot_id']
        assert investigate(db, recovery['investigation_id'], ScriptedInvestigator())
        with db.connection() as con:
            kinds = [tuple(row) for row in con.execute("SELECT investigation_id,invocation_kind FROM step_attempts WHERE step_name='EXTRACTION' ORDER BY rowid")]
        assert kinds == [(started['investigation_id'], 'INITIAL'), (started['investigation_id'], 'AUTO_RETRY'),
                         (recovery['investigation_id'], 'INITIAL')]
        other_did, other_cid = targets[1-winner]
        assert get_case(db, other_did, other_cid)['review_epoch'] == 0
        assert db.capacity.available
    with Database(path) as db:
        assert start_investigation(db, did, cid, bodies[winner]) == started
        assert start_investigation(db, did, cid, recovery_body) == recovery
        assert get_case(db, did, cid)['current_result']['investigation_id'] == recovery['investigation_id']


def test_fresh_revision_does_not_bypass_draft_payload_head_or_epoch_after_failed_rerun(tmp_path):
    with Database(tmp_path / 'fences.sqlite') as db:
        did, cid, first = ready(db)
        review_draft(db, did, cid, approval(first))
        approved = get_case(db, did, cid)
        rerun = start_investigation(db, did, cid, command(approved, retry_of=None))
        assert finish_incomplete(db, rerun['investigation_id'], 'SCRIPTED_FAILURE')
        failed = get_case(db, did, cid)
        assert failed['review_state'] == 'INVALIDATED'
        assert failed['draft'] == first['draft'] and failed['current_result'] == first['current_result']
        for changes, code in [({'payload_hash': '0'*64}, 'DRAFT_PAYLOAD_CHANGED'),
                              ({'expected_review_epoch': first['review_epoch']}, 'REVIEW_EPOCH_CHANGED')]:
            with pytest.raises(CommandError, match=code):
                review_draft(db, did, cid, approval(failed, **changes))
        save_draft(db, did, cid, edit(failed))
        edited = get_case(db, did, cid)
        with pytest.raises(CommandError, match='DRAFT_HEAD_CHANGED'):
            review_draft(db, did, cid, approval(edited, draft_version_id=first['draft']['id'], payload_hash=first['draft']['payload_hash']))
        with pytest.raises(CommandError, match='DRAFT_HEAD_CHANGED'):
            save_draft(db, did, cid, edit(edited, parent_version_id=first['draft']['id']))
        assert len(get_case(db, did, cid)['draft_reviews']) == 1
        review_draft(db, did, cid, approval(edited))
        assert get_case(db, did, cid)['review_state'] == 'APPROVED'
