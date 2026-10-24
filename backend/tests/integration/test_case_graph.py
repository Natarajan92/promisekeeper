"""LangGraph case graph: agent hand-offs, safe drafting fallbacks and owner pause/resume."""
import pytest
from support.lifecycle import command, create_case
from promisekeeper.agents.briefing import ScriptedBriefing
from promisekeeper.agents.communicator import ScriptedCommunicator
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.agents.reviewer import ReviewVerdict, ScriptedReviewer
from promisekeeper.agents.roster import AgentSet
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.agent_activity import list_agent_activity
from promisekeeper.application.cases import get_case
from promisekeeper.application.reviews import review_draft
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.orchestration.case_graph import resume_owner_review
from promisekeeper.orchestration.investigate import get_investigation, investigate
from promisekeeper.persistence.sqlite import Database

NOTE = 'Thank you for keeping us informed about the project.'


def agents(communicator=None, reviewer=None, **kw):
    return AgentSet(ScriptedInvestigator(), communicator or ScriptedCommunicator(), reviewer or ScriptedReviewer(), ScriptedBriefing(), **kw)


def run(db, catalogue_case_id='PK-001', agent_set=None):
    did, cid = create_case(db, catalogue_case_id=catalogue_case_id)
    agent_set = agent_set or agents()
    iid = start_investigation(db, did, cid, command(get_case(db, did, cid), retry_of=None))['investigation_id']
    assert investigate(db, iid, agent_set.investigator, agents=agent_set) is True
    return did, cid, iid, agent_set


def activity(db, iid):
    with db.connection() as con:
        return list_agent_activity(con, investigation_id=iid)


def draft_text(db, did, cid):
    return get_case(db, did, cid)['draft']['exact_text']


def approve(db, did, cid):
    view = get_case(db, did, cid)
    draft = view['draft']
    review_draft(db, did, cid, command(view, draft_version_id=draft['id'], payload_hash=draft['payload_hash'],
                                       expected_review_epoch=view['review_epoch'], decision='APPROVE'))
    return draft['id']


def template(db, did, cid):
    from promisekeeper.application.reviews import plan_for
    from promisekeeper.persistence.repositories import case
    with db.connection() as con:
        return plan_for(con, case(con, did, cid)).exact_text


def test_follow_up_case_runs_all_agents_and_waits_for_owner(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, _ = run(db)
        view = get_case(db, did, cid)
        assert view['draft']['exact_text'].split('\n\n')[1] == NOTE
        assert view['draft']['validation_status'] == 'VALID'
        rows = activity(db, iid)
        assert [r['agent'] for r in rows if r['outcome'] != 'STARTED'] == [
            'INTAKE', 'EXTRACTOR', 'RULES_ENGINE', 'MEMORY', 'COMMUNICATOR', 'SAFETY_CHECK', 'TONE_REVIEWER', 'OWNER']
        assert rows[-1]['outcome'] == 'WAITING'
        rules = next(r for r in rows if r['agent'] == 'RULES_ENGINE')
        assert rules['note'] == 'Follow up: verified overdue balance.'
        detail = get_investigation(db, did, iid)
        assert [r['agent'] for r in detail['agent_activity']] == [r['agent'] for r in rows]
        assert detail['agent_totals']['cost_usd'] is None


def test_wait_case_skips_drafting_agents(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, _ = run(db, 'PK-002')
        agents_seen = {r['agent'] for r in activity(db, iid)}
        assert 'COMMUNICATOR' not in agents_seen and 'OWNER' not in agents_seen
        assert get_case(db, did, cid)['current_result']['action'] == 'WAIT'


def test_reviewer_revision_loop_then_accept(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        reviewer = ScriptedReviewer([ReviewVerdict(False, 'Too blunt'), ReviewVerdict(True, 'ok')])
        did, cid, iid, _ = run(db, agent_set=agents(ScriptedCommunicator(['First try.', NOTE]), reviewer))
        rows = activity(db, iid)
        assert len([r for r in rows if r['agent'] == 'COMMUNICATOR' and r['outcome'] == 'SUCCEEDED']) == 2
        assert [(r['outcome'], r['note']) for r in rows if r['agent'] == 'TONE_REVIEWER'] == [('REVISE', 'Too blunt'), ('SUCCEEDED', 'ok')]
        assert draft_text(db, did, cid).split('\n\n')[1] == NOTE


def test_reviewer_exhaustion_falls_back_to_template(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, _ = run(db, agent_set=agents(reviewer=ScriptedReviewer([ReviewVerdict(False, 'Still too blunt')])))
        assert draft_text(db, did, cid) == template(db, did, cid)
        assert any(r['outcome'] == 'FALLBACK' for r in activity(db, iid))


def test_communicator_failure_falls_back_to_template(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        failing = ScriptedCommunicator([InvestigatorFailure('AGENT_UNAVAILABLE', transient=True)])
        did, cid, iid, _ = run(db, agent_set=agents(failing))
        view = get_case(db, did, cid)
        assert view['draft']['exact_text'] == template(db, did, cid)
        assert view['current_result']['action'] == 'FOLLOW_UP'
        assert any(r['agent'] == 'COMMUNICATOR' and r['outcome'] == 'FAILED' for r in activity(db, iid))


def test_unsafe_note_is_never_saved(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, _ = run(db, agent_set=agents(ScriptedCommunicator(['A late fee of INR 500 applies.'])))
        assert 'late fee' not in draft_text(db, did, cid)
        checks = [r['outcome'] for r in activity(db, iid) if r['agent'] == 'SAFETY_CHECK']
        assert checks[0] == 'REVISE' and 'FALLBACK' in [r['outcome'] for r in activity(db, iid)]


def test_missing_reviewer_records_skipped_and_keeps_safe_note(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        agent_set = AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), None, ScriptedBriefing())
        did, cid, iid, _ = run(db, agent_set=agent_set)
        assert draft_text(db, did, cid).split('\n\n')[1] == NOTE
        assert [r['outcome'] for r in activity(db, iid) if r['agent'] == 'TONE_REVIEWER'] == ['SKIPPED']


def test_legacy_call_without_agents_keeps_template_draft(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid = create_case(db, catalogue_case_id='PK-001')
        iid = start_investigation(db, did, cid, command(get_case(db, did, cid), retry_of=None))['investigation_id']
        assert investigate(db, iid, ScriptedInvestigator()) is True
        assert draft_text(db, did, cid) == template(db, did, cid)


def test_owner_approval_resumes_and_finishes_graph(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, agent_set = run(db)
        version = approve(db, did, cid)
        assert resume_owner_review(db, agent_set, iid, 'APPROVE', version) is True
        last = activity(db, iid)[-1]
        assert (last['agent'], last['outcome']) == ('OWNER', 'SUCCEEDED')
        assert resume_owner_review(db, agent_set, iid, 'APPROVE', version) is False


def test_rejection_keeps_the_graph_waiting(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, agent_set = run(db)
        version = get_case(db, did, cid)['draft']['id']
        assert resume_owner_review(db, agent_set, iid, 'REJECT', version) is True
        assert activity(db, iid)[-1]['outcome'] == 'WAITING'
        assert resume_owner_review(db, agent_set, iid, 'APPROVE', version) is True


def test_resume_survives_new_database_instance(tmp_path):
    path = tmp_path / 'db.sqlite'
    with Database(path) as db:
        did, cid, iid, agent_set = run(db)
        version = approve(db, did, cid)
    with Database(path) as db:
        assert resume_owner_review(db, agent_set, iid, 'APPROVE', version) is True


def test_resume_failure_never_breaks_recorded_approval(tmp_path, monkeypatch):
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, agent_set = run(db)
        def broken(_db):
            raise RuntimeError('checkpoint store unavailable')
        monkeypatch.setattr('promisekeeper.orchestration.case_graph.graph_checkpointer', broken)
        version = approve(db, did, cid)
        assert get_case(db, did, cid)['draft_reviews'][-1]['decision'] == 'APPROVE'
        assert resume_owner_review(db, agent_set, iid, 'APPROVE', version) is False


def test_internal_drafting_error_falls_back_to_template(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('unexpected validator fault')
    monkeypatch.setattr('promisekeeper.orchestration.case_graph.validate_draft', broken)
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, _ = run(db)
        view = get_case(db, did, cid)
        assert view['draft']['exact_text'] == template(db, did, cid)
        assert any(r['agent'] == 'SAFETY_CHECK' and r['outcome'] == 'FAILED' for r in activity(db, iid))


def test_save_failure_marks_draft_attempt_failed_not_running(tmp_path, monkeypatch):
    def broken(*args, **kwargs):
        raise RuntimeError('unexpected save fault')
    monkeypatch.setattr('promisekeeper.orchestration.drafts.generate_draft', broken)
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, _ = run(db)
        view = get_case(db, did, cid)
        assert view['current_result']['action'] == 'FOLLOW_UP'
        assert view['draft_generation_attempt']['status'] == 'FAILED'


def test_reviewer_error_drops_unreviewed_note(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        broken = ScriptedReviewer([InvestigatorFailure('AGENT_UNAVAILABLE', transient=True)])
        did, cid, iid, _ = run(db, agent_set=agents(reviewer=broken))
        assert draft_text(db, did, cid) == template(db, did, cid)
        assert [r['outcome'] for r in activity(db, iid) if r['agent'] == 'TONE_REVIEWER'] == ['FAILED']


def test_graph_fault_after_commit_never_leaves_draft_running(tmp_path, monkeypatch):
    from promisekeeper.orchestration import drafts
    real_failure, calls = drafts.failure, []

    def flaky_failure(db, aid, code):
        calls.append(code)
        if len(calls) == 1:
            raise RuntimeError('database busy')
        return real_failure(db, aid, code)

    def broken_save(*args, **kwargs):
        raise RuntimeError('unexpected save fault')
    monkeypatch.setattr(drafts, 'generate_draft', broken_save)
    monkeypatch.setattr(drafts, 'failure', flaky_failure)
    with Database(tmp_path / 'db.sqlite') as db:
        did, cid, iid, _ = run(db)
        view = get_case(db, did, cid)
        assert view['current_result']['action'] == 'FOLLOW_UP'
        assert view['draft_generation_attempt']['status'] == 'FAILED'
