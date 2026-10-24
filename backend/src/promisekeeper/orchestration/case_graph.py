"""Graph 1: one case investigation as a LangGraph multi-agent graph.

Evidence Intake -> Promise Extractor (LLM) -> Rules Engine (code) -> [draft needed?]
  -> Client Memory -> Communicator (LLM) -> Safety Check (code) -> Tone Reviewer (LLM) -> save draft -> Owner review (pause).

Nodes reuse the persisted step machinery (run_step, deadlines, fencing), so recovery and
idempotency rules are unchanged. Code owns money, actions and eligibility; LLM agents only
extract, write one personal note and critique tone. Every hand-off is recorded in agent_activity.
"""
import json
import sqlite3
import threading
import time
from typing import TypedDict
from uuid import NAMESPACE_URL, uuid5

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from promisekeeper.agents.communicator import NoteContext
from promisekeeper.agents.memory import LocalMemory, facts_from_result
from promisekeeper.agents.protocol import EXTRACTION_POLICY_VERSION, PROMPT_VERSION, InvestigatorFailure
from promisekeeper.agents.validation import validate_output
from promisekeeper.application.agent_activity import record_agent
from promisekeeper.application.derived_findings import derive_findings
from promisekeeper.application.findings import result_view
from promisekeeper.application.operations import canonical, instant, utcnow
from promisekeeper.contracts.investigations import Result
from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.domain.draft_validation import validate_draft
from promisekeeper.domain.personal_note import compose_with_note
from promisekeeper.domain.recommendations import recommend
from promisekeeper.domain.untrusted import screen_message
from promisekeeper.orchestration.deadlines import Budget, bounded_call
from promisekeeper.orchestration.retries import run_step
from promisekeeper.persistence.repositories import append_event, case
from promisekeeper.tools.evidence import read_snapshot, snapshot_case

MAX_NOTE_ATTEMPTS = 2
DRAFTING_RESERVE_SECONDS = 8
_checkpointer_lock = threading.Lock()


class CaseState(TypedDict, total=False):
    investigation_id: str
    demonstration_id: str
    case_id: str
    packet: dict
    raw_output: object
    response: dict
    committed: bool
    action: str | None
    draft_attempt_id: str | None
    note: str | None
    feedback: str | None
    memory: str | None
    client: str
    revisions: int
    final_text: str | None
    draft_version_id: str | None
    decision: str | None
    route: str


def customer_messages(packet):
    return [r['original_content'] for r in packet['evidence']
            if r.get('kind') == 'MESSAGE' and r.get('availability') == 'AVAILABLE' and r.get('original_content')]


def graph_checkpointer(db):
    """One SQLite checkpoint store per database, beside it, so paused reviews survive restarts."""
    with _checkpointer_lock:
        saver = getattr(db, 'graph_checkpointer', None)
        if saver is None:
            path = db.path.with_name(db.path.stem + '-graph.sqlite')
            saver = SqliteSaver(sqlite3.connect(path, check_same_thread=False))
            db.graph_checkpointer = saver
        return saver


def run_id_for(investigation_id):
    return uuid5(NAMESPACE_URL, 'promisekeeper:' + investigation_id)


def graph_config(investigation_id):
    return {'configurable': {'thread_id': investigation_id}, 'run_id': run_id_for(investigation_id),
            'run_name': 'promisekeeper-case-investigation', 'metadata': {'investigation_id': investigation_id}}


def _attempt(db, investigation_id):
    with db.connection() as con:
        row = con.execute('SELECT * FROM investigations WHERE id=?', (investigation_id,)).fetchone()
    if row is None:
        raise InvestigatorFailure('TERMINAL_ATTEMPT')
    return dict(row)


def _remaining(db, state):
    try:
        return Budget(_attempt(db, state['investigation_id'])['deadline_at']).remaining()
    except InvestigatorFailure:
        return 0


def build_case_graph(db, agents, *, draft_generator=None, pause_for_owner=True):
    def record(state, agent, event, outcome, note=None, call=None, started=None, to=None, kind=None):
        record_agent(db, demonstration_id=state['demonstration_id'], case_id=state['case_id'], investigation_id=state['investigation_id'],
                     agent=agent, event=event, outcome=outcome, note=note, model=getattr(call, 'model', None), to=to, kind=kind,
                     input_tokens=getattr(call, 'input_tokens', None), output_tokens=getattr(call, 'output_tokens', None),
                     latency_ms=call.latency_ms if call else (int((time.monotonic() - started) * 1000) if started else None))

    def plan(state):
        from promisekeeper.application.reviews import plan_for
        with db.connection() as con:
            return plan_for(con, case(con, state['demonstration_id'], state['case_id']))

    def note_context(state, draft_plan):
        messages = tuple(screen_message(text)[0] for text in customer_messages(state['packet']))
        return NoteContext(client=draft_plan.recipient, invoice_id=draft_plan.invoice_id, action=state.get('action') or '',
                           customer_messages=messages, draft_text=draft_plan.exact_text, reviewer_feedback=state.get('feedback'),
                           memory=state.get('memory'))

    def evidence_intake(state):
        started = time.monotonic()
        attempt = _attempt(db, state['investigation_id'])
        with db.connection() as con:
            raw = json.loads(con.execute('SELECT packet_json FROM evidence_snapshots WHERE id=?', (attempt['snapshot_id'],)).fetchone()[0])
        packet = run_step(db, attempt, 'EVIDENCE_LOOKUP', Budget(attempt['deadline_at']), lambda: read_snapshot(
            db, dict(schema_version='1', snapshot_id=attempt['snapshot_id'], evidence_version_ids=[r['id'] for r in raw['evidence']])))
        flagged = sum(screen_message(text)[1] for text in customer_messages(packet))
        note = f"{len(packet['evidence'])} evidence records"
        if flagged:
            note += (f'; {flagged} customer message(s) contain instruction-like text, treated as evidence only and hidden '
                     'from the writing agents')
        record(state, 'INTAKE', 'Read the saved evidence snapshot', 'SUCCEEDED', note=note + '.', started=started)
        return {'packet': packet}

    def promise_extractor(state):
        started = time.monotonic()
        attempt = _attempt(db, state['investigation_id'])
        budget, packet = Budget(attempt['deadline_at']), state['packet']
        snapshot_case(packet)
        request = dict(schema_version='1', investigation_id=state['investigation_id'], snapshot_id=attempt['snapshot_id'],
                       snapshot_hash=packet['snapshot_hash'], packet=packet, prompt_version=PROMPT_VERSION,
                       extraction_policy_version=EXTRACTION_POLICY_VERSION)

        def extraction():
            timeout = min(20, budget.remaining())
            return bounded_call(lambda: agents.investigator.extract(request, timeout=timeout), timeout)
        response = run_step(db, attempt, 'EXTRACTION', budget, extraction)
        with db.transaction() as con:
            con.execute("UPDATE investigations SET returned_model=?,response_id=?,prompt_version=?,schema_version=?,adapter_version=? WHERE id=? AND status='RUNNING'",
                        (response.returned_model, response.response_id, PROMPT_VERSION, '1', response.adapter_version, state['investigation_id']))
        usage = response.usage or {}
        record_agent(db, demonstration_id=state['demonstration_id'], case_id=state['case_id'], investigation_id=state['investigation_id'],
                     agent='EXTRACTOR', event='Extract customer promises and payment claims', outcome='SUCCEEDED',
                     note='Quotes are checked against the exact source text next.', model=response.returned_model or 'scripted',
                     input_tokens=usage.get('prompt_tokens'), output_tokens=usage.get('completion_tokens'),
                     latency_ms=int((time.monotonic() - started) * 1000))
        return {'raw_output': response.output, 'response': dict(returned_model=response.returned_model, response_id=response.response_id,
                                                                adapter_version=response.adapter_version)}

    def rules_engine(state):
        started = time.monotonic()
        iid = state['investigation_id']
        attempt = _attempt(db, iid)
        budget, packet, meta = Budget(attempt['deadline_at']), state['packet'], state['response']
        evidence = snapshot_case(packet)
        output, extracted = run_step(db, attempt, 'VALIDATION', budget, lambda: validate_output(state['raw_output'], packet, evidence))
        from datetime import datetime
        recommendation = run_step(db, attempt, 'RECONCILIATION', budget,
                                  lambda: recommend(evidence, extracted, datetime.fromisoformat(attempt['evaluation_at'])))
        commitment_facts = reconcile_commitments(evidence, extracted, recommendation.financial)
        limitations = sorted({i.code for i in (*recommendation.financial.issues, *commitment_facts.issues)}) if recommendation.status == 'LIMITED' else []
        derived = derive_findings(evidence, extracted, recommendation, commitment_facts, packet)
        result = result_view(attempt, packet, recommendation, derived, limitations=limitations)
        Result.model_validate(result)
        budget.remaining()
        from promisekeeper.application.draft_retry import reserve_initial
        with db.transaction() as con:
            current = con.execute('SELECT status,deadline_at FROM investigations WHERE id=?', (iid,)).fetchone()
            if current is None or current['status'] != 'RUNNING':
                return {'committed': False}
            if utcnow() >= datetime.fromisoformat(current['deadline_at']):
                raise InvestigatorFailure('INVESTIGATION_DEADLINE')
            con.execute("UPDATE investigations SET status=?,terminal_at=?,returned_model=?,response_id=?,prompt_version=?,schema_version=?,adapter_version=? WHERE id=? AND status='RUNNING'",
                        (recommendation.status, instant(utcnow()), meta['returned_model'], meta['response_id'], PROMPT_VERSION, '1', meta['adapter_version'], iid))
            con.execute('INSERT INTO investigation_results VALUES (?,?,?,?,?,?,?,?)',
                        (iid, attempt['demonstration_id'], attempt['case_id'], result['action'], result['review_at'], canonical(result), result['result_hash'], 'rules-1'))
            con.execute('UPDATE cases SET latest_completed_investigation_id=?,current_draft_version_id=NULL,case_revision=case_revision+1 WHERE id=?', (iid, attempt['case_id']))
            append_event(con, dict(id=attempt['case_id'], demonstration_id=attempt['demonstration_id']), 'INVESTIGATION_COMPLETED', attempt['operation_id'],
                         dict(investigation_id=iid, status=recommendation.status, result_hash=result['result_hash']))
            aid = reserve_initial(con, iid)
            drafting = aid is not None and con.execute('SELECT status FROM draft_generation_attempts WHERE id=?', (aid,)).fetchone()[0] == 'RUNNING'
        db.capacity.release(iid)
        db.reservations.discard(iid)
        record(state, 'RULES_ENGINE', 'Apply payment rules and choose one action', 'SUCCEEDED',
               note=f"{result['action']}: {recommendation.reason_code}", started=started,
               to='MEMORY' if drafting else 'OWNER', kind='DECISION')
        try:
            store = memory_store()
            for fact in facts_from_result(result):
                store.remember(evidence.client, fact, scope=state['demonstration_id'])
        except Exception as exc:
            record(state, 'MEMORY', 'Remember payment history', 'FAILED',
                   note=f"{getattr(exc, 'code', type(exc).__name__)}; the recommendation is saved without updating memory.")
        return {'committed': True, 'action': result['action'], 'draft_attempt_id': aid, 'client': evidence.client}

    def after_rules(state):
        aid = state.get('draft_attempt_id')
        if not state.get('committed') or not aid:
            return END
        with db.connection() as con:
            row = con.execute('SELECT status FROM draft_generation_attempts WHERE id=?', (aid,)).fetchone()
        return 'client_memory' if row is not None and row['status'] == 'RUNNING' else END

    def memory_store():
        return agents.memory if agents.memory is not None else LocalMemory(db)

    def client_memory(state):
        started = time.monotonic()
        try:
            remembered = memory_store().recall(state['client'])
        except Exception as exc:
            record(state, 'MEMORY', 'Recall payment history', 'FAILED',
                   note=f"{getattr(exc, 'code', type(exc).__name__)}; the note is written without history.", started=started,
                   to='COMMUNICATOR', kind='CLIENT_HISTORY')
            return {'memory': None, 'route': 'communicator'}
        if not remembered:
            record(state, 'MEMORY', 'Recall payment history', 'SKIPPED', note='No earlier payment history for this client.', started=started)
            return {'memory': None, 'route': 'communicator'}
        record(state, 'MEMORY', 'Recall payment history', 'SUCCEEDED', note=remembered, started=started)
        return {'memory': remembered, 'route': 'communicator'}

    def communicator(state):
        revisions = state.get('revisions', 0)
        event = 'Write a personal note' if revisions == 0 else 'Revise the personal note'
        if agents.communicator is None:
            record(state, 'COMMUNICATOR', event, 'SKIPPED', note='No communicator configured; the standard template is used.')
            return {'note': None, 'final_text': None, 'route': 'save_draft'}
        remaining = _remaining(db, state)
        if remaining < DRAFTING_RESERVE_SECONDS:
            record(state, 'COMMUNICATOR', event, 'FALLBACK', note='Not enough time left; the standard template is used.')
            return {'note': None, 'final_text': None, 'route': 'save_draft'}
        timeout = min(15, remaining - 5)
        try:
            call = bounded_call(lambda: agents.communicator.write_note(note_context(state, plan(state)), timeout=timeout), timeout)
        except Exception as exc:
            record(state, 'COMMUNICATOR', event, 'FAILED', note=f"{getattr(exc, 'code', 'AGENT_FAILED')}; the standard template is used.")
            return {'note': None, 'final_text': None, 'route': 'save_draft'}
        record(state, 'COMMUNICATOR', event, 'SUCCEEDED', note=call.value['note'], call=call)
        return {'note': call.value['note'], 'revisions': revisions + 1, 'route': 'safety_check'}

    def safety_check(state):
        started = time.monotonic()
        draft_plan = plan(state)
        text = compose_with_note(draft_plan.exact_text, state['note'])
        reasons = validate_draft(draft_plan, text, draft_plan.recipient)
        if not reasons:
            record(state, 'SAFETY_CHECK', 'Check the note against money and safety rules', 'SUCCEEDED',
                   note='No amounts, fees, payment claims or instructions.', started=started)
            return {'final_text': text, 'route': 'tone_reviewer'}
        blocked = ', '.join(reasons)
        if state.get('revisions', 0) < MAX_NOTE_ATTEMPTS:
            record(state, 'SAFETY_CHECK', 'Check the note against money and safety rules', 'REVISE', note=f'Blocked: {blocked}', started=started)
            return {'feedback': f'The safety check blocked the note ({blocked}). Remove any numbers, fees, payment claims or instructions.',
                    'final_text': None, 'route': 'communicator'}
        record(state, 'SAFETY_CHECK', 'Check the note against money and safety rules', 'FALLBACK',
               note=f'Blocked again ({blocked}); the standard template is used.', started=started)
        return {'note': None, 'final_text': None, 'route': 'save_draft'}

    def tone_reviewer(state):
        event = 'Review the note tone'
        if agents.reviewer is None:
            record(state, 'TONE_REVIEWER', event, 'SKIPPED', note='No tone reviewer configured; the note passed the safety check.')
            return {'route': 'save_draft'}
        remaining = _remaining(db, state)
        if remaining < DRAFTING_RESERVE_SECONDS:
            record(state, 'TONE_REVIEWER', event, 'FALLBACK', note='Not enough time to review; the standard template is used.')
            return {'note': None, 'final_text': None, 'route': 'save_draft'}
        timeout = min(15, remaining - 5)
        try:
            verdict, call = bounded_call(lambda: agents.reviewer.review(note_context(state, plan(state)), state['note'], timeout=timeout), timeout)
        except Exception as exc:
            record(state, 'TONE_REVIEWER', event, 'FAILED',
                   note=f"{getattr(exc, 'code', 'AGENT_FAILED')}; the note passed the safety check and still needs your review.")
            return {'route': 'save_draft'}
        if verdict.accepted:
            record(state, 'TONE_REVIEWER', event, 'SUCCEEDED', note=verdict.feedback, call=call)
            return {'route': 'save_draft'}
        if state.get('revisions', 0) < MAX_NOTE_ATTEMPTS:
            record(state, 'TONE_REVIEWER', event, 'REVISE', note=verdict.feedback, call=call)
            return {'feedback': verdict.feedback, 'final_text': None, 'route': 'communicator'}
        record(state, 'TONE_REVIEWER', event, 'FALLBACK', note=f'{verdict.feedback} The standard template is used.', call=call)
        return {'note': None, 'final_text': None, 'route': 'save_draft'}

    def save_draft(state):
        from promisekeeper.orchestration import drafts
        aid, final = state['draft_attempt_id'], state.get('final_text')
        try:
            if draft_generator is not None:
                drafts.generate_draft(db, aid, draft_generator)
            elif final:
                drafts.generate_draft(db, aid, lambda draft_plan: final)
            else:
                drafts.generate_draft(db, aid)
        except Exception as exc:
            # A saved recommendation never waits on a stuck draft: mark the attempt failed (retryable).
            drafts.failure(db, aid, getattr(exc, 'code', 'DRAFT_FAILED'))
        with db.connection() as con:
            status = con.execute('SELECT status FROM draft_generation_attempts WHERE id=?', (aid,)).fetchone()
            current = case(con, state['demonstration_id'], state['case_id'])['current_draft_version_id']
        if status is None or status['status'] != 'READY' or not pause_for_owner:
            return {'route': END}
        record(state, 'OWNER', 'Review the draft', 'WAITING', note='The draft is ready for your review. Nothing is sent.')
        return {'draft_version_id': current, 'route': 'owner_review'}

    def owner_review(state):
        decision = interrupt({'investigation_id': state['investigation_id'], 'draft_version_id': state.get('draft_version_id')})
        return {'decision': decision.get('decision'), 'draft_version_id': decision.get('draft_version_id') or state.get('draft_version_id')}

    def record_decision(state):
        if state.get('decision') == 'APPROVE':
            record(state, 'OWNER', 'Review the draft', 'SUCCEEDED', note='You approved this exact draft. Nothing is sent automatically.')
            return {'route': END}
        record(state, 'OWNER', 'Review the draft', 'WAITING', note='You rejected this draft; it stays in history. Edit it or investigate again.')
        return {'route': 'owner_review'}

    def by_route(state):
        return state['route']

    def guarded(agent, node):
        """Drafting runs after the recommendation is saved: an unexpected fault means the template, never a stuck case."""
        def run(state):
            try:
                return node(state)
            except Exception as exc:
                record(state, agent, 'Unexpected drafting fault', 'FAILED',
                       note=f"{getattr(exc, 'code', type(exc).__name__)}; the standard template is used.")
                return {'note': None, 'final_text': None, 'route': 'save_draft'}
        return run

    graph = StateGraph(CaseState)
    for name, node in (('evidence_intake', evidence_intake), ('promise_extractor', promise_extractor), ('rules_engine', rules_engine),
                       ('client_memory', guarded('MEMORY', client_memory)), ('communicator', guarded('COMMUNICATOR', communicator)), ('safety_check', guarded('SAFETY_CHECK', safety_check)),
                       ('tone_reviewer', guarded('TONE_REVIEWER', tone_reviewer)),
                       ('save_draft', save_draft), ('owner_review', owner_review), ('record_decision', record_decision)):
        graph.add_node(name, node)
    graph.add_edge(START, 'evidence_intake')
    graph.add_edge('evidence_intake', 'promise_extractor')
    graph.add_edge('promise_extractor', 'rules_engine')
    graph.add_conditional_edges('rules_engine', after_rules, ['client_memory', END])
    graph.add_conditional_edges('client_memory', by_route, ['communicator', 'save_draft'])
    graph.add_conditional_edges('communicator', by_route, ['safety_check', 'save_draft'])
    graph.add_conditional_edges('safety_check', by_route, ['tone_reviewer', 'communicator', 'save_draft'])
    graph.add_conditional_edges('tone_reviewer', by_route, ['save_draft', 'communicator'])
    graph.add_conditional_edges('save_draft', by_route, ['owner_review', END])
    graph.add_edge('owner_review', 'record_decision')
    graph.add_conditional_edges('record_decision', by_route, ['owner_review', END])
    checkpointer = graph_checkpointer(db) if pause_for_owner else None
    return graph.compile(checkpointer=checkpointer)


def resume_owner_review(db, agents, investigation_id, decision, draft_version_id):
    """Best-effort: the owner's recorded review is authoritative; the graph only follows it."""
    try:
        graph = build_case_graph(db, agents)
        config = graph_config(investigation_id)
        if not graph.get_state(config).next:
            return False
        graph.invoke(Command(resume={'decision': decision, 'draft_version_id': draft_version_id}), config)
        return True
    except Exception:
        return False
