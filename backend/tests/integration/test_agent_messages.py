"""Typed agent-to-agent hand-offs follow one explicit protocol and are visible in the trace."""
from uuid import uuid4
import pytest
from support.lifecycle import command, create_case
from promisekeeper.agents.briefing import ScriptedBriefing
from promisekeeper.agents.communicator import ScriptedCommunicator
from promisekeeper.agents.messages import AgentMessage, route_for
from promisekeeper.agents.reviewer import ReviewVerdict, ScriptedReviewer
from promisekeeper.agents.roster import AgentSet
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.agent_activity import list_agent_activity
from promisekeeper.application.cases import create_demonstration, get_case
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.orchestration.investigate import investigate
from promisekeeper.orchestration.morning_review import get_morning_review, run_morning_review, start_morning_review
from promisekeeper.persistence.sqlite import Database


def test_protocol_rejects_unlisted_handoffs():
    with pytest.raises(ValueError):
        route_for('COMMUNICATOR', 'SUCCEEDED', to='OWNER', kind='DRAFT_FOR_APPROVAL')
    with pytest.raises(ValueError):
        route_for('BRIEFING', 'SUCCEEDED', to='COMMUNICATOR', kind='BRIEFING')
    assert route_for('TONE_REVIEWER', 'REVISE') == AgentMessage(sender='TONE_REVIEWER', recipient='COMMUNICATOR', kind='REVISION_REQUEST')
    assert route_for('OWNER', 'WAITING') is None


def test_case_run_hands_off_per_protocol(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        agent_set = AgentSet(ScriptedInvestigator(), ScriptedCommunicator(['First.', 'Thanks for the update.']),
                             ScriptedReviewer([ReviewVerdict(False, 'Warmer please'), ReviewVerdict(True, 'ok')]), ScriptedBriefing())
        did, cid = create_case(db, catalogue_case_id='PK-001')
        iid = start_investigation(db, did, cid, command(get_case(db, did, cid), retry_of=None))['investigation_id']
        assert investigate(db, iid, agent_set.investigator, agents=agent_set)
        with db.connection() as con:
            rows = [r for r in list_agent_activity(con, investigation_id=iid) if r['agent'] != 'OWNER']
        assert [(r['agent'], r['recipient'], r['message_kind']) for r in rows] == [
            ('INTAKE', 'EXTRACTOR', 'EVIDENCE_PACKET'), ('EXTRACTOR', 'RULES_ENGINE', 'PAYMENT_CANDIDATES'),
            ('RULES_ENGINE', 'MEMORY', 'DECISION'), ('MEMORY', 'COMMUNICATOR', 'CLIENT_HISTORY'),
            ('COMMUNICATOR', 'SAFETY_CHECK', 'NOTE_DRAFT'), ('SAFETY_CHECK', 'TONE_REVIEWER', 'NOTE_DRAFT'),
            ('TONE_REVIEWER', 'COMMUNICATOR', 'REVISION_REQUEST'), ('COMMUNICATOR', 'SAFETY_CHECK', 'NOTE_DRAFT'),
            ('SAFETY_CHECK', 'TONE_REVIEWER', 'NOTE_DRAFT'), ('TONE_REVIEWER', 'OWNER', 'DRAFT_FOR_APPROVAL')]


def test_wait_decision_goes_straight_to_owner(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        agent_set = AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), ScriptedBriefing())
        did, cid = create_case(db, catalogue_case_id='PK-002')
        iid = start_investigation(db, did, cid, command(get_case(db, did, cid), retry_of=None))['investigation_id']
        assert investigate(db, iid, agent_set.investigator, agents=agent_set)
        with db.connection() as con:
            rules = next(r for r in list_agent_activity(con, investigation_id=iid) if r['agent'] == 'RULES_ENGINE')
        assert (rules['recipient'], rules['message_kind']) == ('OWNER', 'DECISION')


def test_morning_review_hands_off_per_protocol(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = create_demonstration(db, dict(schema_version='1', operation_id=str(uuid4()), catalogue_version='release-0.1',
                                            variant_id=None, clock_mode='REFERENCE'))['demonstration_id']
        started = start_morning_review(db, did, dict(schema_version='1', operation_id=str(uuid4())))
        run_morning_review(db, AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), ScriptedBriefing()), started['id'])
        rows = get_morning_review(db, did, started['id'])['agent_activity']
        assert (rows[0]['recipient'], rows[0]['message_kind']) == ('INTAKE', 'CASE_SELECTION')
        assert {(r['recipient'], r['message_kind']) for r in rows[1:-1]} == {('BRIEFING', 'CASE_OUTCOME')}
        assert (rows[-1]['agent'], rows[-1]['recipient'], rows[-1]['message_kind']) == ('BRIEFING', 'OWNER', 'BRIEFING')
