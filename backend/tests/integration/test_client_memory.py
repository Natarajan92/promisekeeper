"""Per-client payment memory: written only from deterministic results, used only for note tone."""
import httpx
from support.lifecycle import command, create_case
from promisekeeper.agents.briefing import ScriptedBriefing
from promisekeeper.agents.communicator import ScriptedCommunicator
from promisekeeper.agents.memory import LocalMemory, Mem0Memory, facts_from_result
from promisekeeper.agents.reviewer import ScriptedReviewer
from promisekeeper.agents.roster import AgentSet
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.application.agent_activity import list_agent_activity
from promisekeeper.application.cases import get_case
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.orchestration.investigate import investigate
from promisekeeper.persistence.sqlite import Database


class RecordingCommunicator(ScriptedCommunicator):
    def __init__(self):
        super().__init__()
        self.memories = []

    def write_note(self, ctx, *, timeout):
        self.memories.append(ctx.memory)
        return super().write_note(ctx, timeout=timeout)


def run_once(db, did, cid, agent_set):
    iid = start_investigation(db, did, cid, command(get_case(db, did, cid), retry_of=None))['investigation_id']
    assert investigate(db, iid, agent_set.investigator, agents=agent_set)
    return iid


def memory_rows(db, iid):
    with db.connection() as con:
        return [r for r in list_agent_activity(con, investigation_id=iid) if r['agent'] == 'MEMORY']


def test_missed_promise_is_remembered_and_recalled_for_next_note(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        communicator = RecordingCommunicator()
        agent_set = AgentSet(ScriptedInvestigator(), communicator, ScriptedReviewer(), ScriptedBriefing())
        did, cid = create_case(db, catalogue_case_id='PK-001')
        first = run_once(db, did, cid, agent_set)
        assert LocalMemory(db).recall('Northstar Analytics') == 'Missed a promise to pay INR 80,000.00 by 20 Oct 2026.'
        assert memory_rows(db, first)[0]['outcome'] == 'SUCCEEDED'
        run_once(db, did, cid, agent_set)
        assert communicator.memories[-1] == 'Missed a promise to pay INR 80,000.00 by 20 Oct 2026.'
        assert LocalMemory(db).recall('Northstar Analytics').count('Missed') == 1


def test_memory_never_changes_recommendation(tmp_path):
    results = []
    for seeded in (False, True):
        with Database(tmp_path / f'db-{seeded}.sqlite') as db:
            if seeded:
                LocalMemory(db).remember('Northstar Analytics', 'Kept every promise on time.')
            did, cid = create_case(db, catalogue_case_id='PK-001')
            run_once(db, did, cid, AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), ScriptedBriefing()))
            result = get_case(db, did, cid)['current_result']
            results.append((result['action'], result['financial_facts'], result['reason_code']))
    assert results[0] == results[1]


def test_memory_failure_continues_without_context(tmp_path):
    class Broken:
        def recall(self, client):
            raise RuntimeError('memory store down')

        def remember(self, client, fact):
            raise RuntimeError('memory store down')
    with Database(tmp_path / 'db.sqlite') as db:
        communicator = RecordingCommunicator()
        did, cid = create_case(db, catalogue_case_id='PK-001')
        iid = run_once(db, did, cid, AgentSet(ScriptedInvestigator(), communicator, ScriptedReviewer(), ScriptedBriefing(), memory=Broken()))
        assert memory_rows(db, iid)[0]['outcome'] == 'FAILED'
        assert communicator.memories == [None]
        assert get_case(db, did, cid)['draft']['validation_status'] == 'VALID'


def test_unverified_payment_claim_is_remembered():
    result = dict(evaluation_at='2026-10-23T10:00:00+05:30', commitments=[],
                  claims=[dict(source_id='PK-003-M1', resolved=False, customer_clarification=False)])
    assert facts_from_result(result) == ['Said a payment was made that is not yet verified.']


def test_mem0_adapter_sends_and_reads_client_scoped_memories():
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path, request.headers['Authorization'], request.content))
        if request.method == 'GET':
            return httpx.Response(200, json=[{'memory': 'Missed a promise to pay INR 80,000.00 by 20 Oct 2026.'}])
        return httpx.Response(200, json=[{'id': 'm1'}])
    memory = Mem0Memory('m0-key', client=httpx.Client(transport=httpx.MockTransport(handler)))
    memory.remember('Northstar Analytics', 'Kept a promise.')
    assert memory.recall('Northstar Analytics') == 'Missed a promise to pay INR 80,000.00 by 20 Oct 2026.'
    assert seen[0][0] == 'POST' and seen[0][2] == 'Token m0-key' and b'client:Northstar Analytics' in seen[0][3]
    assert seen[1][0] == 'GET'


def test_memory_is_scoped_to_its_demonstration_copy(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        communicator = RecordingCommunicator()
        agent_set = AgentSet(ScriptedInvestigator(), communicator, ScriptedReviewer(), ScriptedBriefing())
        did_a, cid_a = create_case(db, catalogue_case_id='PK-001')
        run_once(db, did_a, cid_a, agent_set)
        did_b, cid_b = create_case(db, catalogue_case_id='PK-001')
        assert LocalMemory(db).recall('Northstar Analytics', scope=did_b) is None
        run_once(db, did_b, cid_b, agent_set)
        assert LocalMemory(db).recall('Northstar Analytics', scope=did_b) == 'Missed a promise to pay INR 80,000.00 by 20 Oct 2026.'
        from promisekeeper.application.cases import delete_demonstration
        from uuid import uuid4
        delete_demonstration(db, did_a, dict(schema_version='1', operation_id=str(uuid4()), confirmed_demonstration_id=did_a, confirm=True))
        assert LocalMemory(db).recall('Northstar Analytics', scope=did_b) == 'Missed a promise to pay INR 80,000.00 by 20 Oct 2026.'
