"""Graph 2: the Morning Review supervisor.

The supervisor decides on its own which open cases need work (never investigated, evidence
changed, or review date reached), runs the case graph for each one, then asks the Briefing
agent for an owner summary. It never sends messages, approves drafts or closes cases: those
remain owner decisions. A briefing that states an unsupported number is replaced by the
deterministic briefing.
"""
from datetime import datetime
import json
import time
from typing import TypedDict
from uuid import UUID, uuid4, uuid5

from langgraph.graph import END, START, StateGraph

from promisekeeper.agents.briefing import briefing_numbers_supported, deterministic_briefing
from promisekeeper.application.agent_activity import list_agent_activity, record_agent
from promisekeeper.application.cases import get_case, list_cases
from promisekeeper.application.draft_templates import _amount
from promisekeeper.application.operations import CommandError, instant, utcnow
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.domain.dates import IST
from promisekeeper.orchestration.deadlines import bounded_call
from promisekeeper.persistence.repositories import demonstration

BRIEFING_TIMEOUT_SECONDS = 20


class ReviewState(TypedDict, total=False):
    morning_review_id: str
    demonstration_id: str
    queue: list
    outcomes: list
    briefing: str
    briefing_source: str


def _view(con, row):
    return dict(schema_version='1', id=row['id'], demonstration_id=row['demonstration_id'], status=row['status'],
                started_at=row['started_at'], terminal_at=row['terminal_at'], briefing=row['briefing'],
                briefing_source=row['briefing_source'], failure_code=row['failure_code'], outcomes=json.loads(row['outcomes_json']),
                agent_activity=list_agent_activity(con, morning_review_id=row['id']))


def start_morning_review(db, did, request):
    with db.transaction() as con:
        demonstration(con, did)
        saved = con.execute('SELECT * FROM morning_reviews WHERE operation_id=?', (request['operation_id'],)).fetchone()
        if saved is not None:
            if saved['demonstration_id'] != did:
                raise CommandError('OPERATION_PAYLOAD_MISMATCH', 409)
            return _view(con, saved)
        if con.execute("SELECT 1 FROM morning_reviews WHERE demonstration_id=? AND status='RUNNING'", (did,)).fetchone():
            raise CommandError('MORNING_REVIEW_RUNNING', 409)
        mid = str(uuid4())
        con.execute("INSERT INTO morning_reviews (id,demonstration_id,operation_id,status,started_at) VALUES (?,?,?,'RUNNING',?)",
                    (mid, did, request['operation_id'], instant(utcnow())))
        return _view(con, con.execute('SELECT * FROM morning_reviews WHERE id=?', (mid,)).fetchone())


def get_morning_review(db, did, mid):
    with db.connection() as con:
        row = con.execute('SELECT * FROM morning_reviews WHERE id=? AND demonstration_id=?', (mid, did)).fetchone()
        if row is None:
            raise CommandError('NOT_FOUND', 404)
        return _view(con, row)


def latest_morning_review(db, did):
    with db.connection() as con:
        row = con.execute('SELECT * FROM morning_reviews WHERE demonstration_id=? ORDER BY started_at DESC, rowid DESC LIMIT 1', (did,)).fetchone()
        return dict(schema_version='1', morning_review=_view(con, row) if row else None)


def _needs_work(summary, running, evaluated_at):
    if summary['lifecycle'] != 'OPEN':
        return 'Case is closed; reopening is your decision.'
    if running:
        return 'An investigation is already running.'
    if summary['recommended_action'] is None:
        return None
    if summary['review_required']:
        return None
    if summary['review_at'] and datetime.fromisoformat(summary['review_at']) <= evaluated_at:
        return None
    return 'The saved recommendation is still current.'


def _fact(summary, outcome, reason=None, draft_ready=False):
    review_at = summary['review_at']
    return dict(case_id=summary['id'], client=summary['client'], invoice_id=summary['invoice_id'], outcome=outcome,
                action=summary['recommended_action'], reason=reason,
                balance_text=_amount(summary['balance']) if summary['balance'] else None,
                review_at_text=datetime.fromisoformat(review_at).astimezone(IST).strftime('%d %b %Y, %H:%M IST') if review_at else None,
                draft_ready=draft_ready)


def build_morning_review_graph(db, agents):
    from promisekeeper.orchestration.investigate import investigate

    def record(state, agent, event, outcome, note=None, call=None, case_id=None, started=None, to=None, kind=None):
        record_agent(db, demonstration_id=state['demonstration_id'], case_id=case_id, morning_review_id=state['morning_review_id'],
                     agent=agent, event=event, outcome=outcome, note=note, model=getattr(call, 'model', None), to=to, kind=kind,
                     input_tokens=getattr(call, 'input_tokens', None), output_tokens=getattr(call, 'output_tokens', None),
                     latency_ms=call.latency_ms if call else (int((time.monotonic() - started) * 1000) if started else None))

    def select_cases(state):
        started = time.monotonic()
        did = state['demonstration_id']
        listing = list_cases(db, did)
        evaluated_at = datetime.fromisoformat(listing['evaluation_at'])
        queue, outcomes = [], []
        with db.connection() as con:
            running = {row[0] for row in con.execute("SELECT case_id FROM investigations WHERE demonstration_id=? AND status='RUNNING'", (did,))}
        for summary in listing['cases']:
            reason = _needs_work(summary, summary['id'] in running, evaluated_at)
            if reason is None:
                queue.append(summary['id'])
            else:
                outcomes.append(_fact(summary, 'SKIPPED', reason))
                record(state, 'SUPERVISOR', f"Skip {summary['client']}", 'SKIPPED', note=reason, case_id=summary['id'])
        record(state, 'SUPERVISOR', 'Choose which cases need work', 'SUCCEEDED',
               note=f'{len(queue)} of {len(listing["cases"])} cases need a fresh investigation.', started=started,
               to='INTAKE', kind='CASE_SELECTION')
        return {'queue': queue, 'outcomes': outcomes}

    def investigate_next(state):
        started = time.monotonic()
        did, mid = state['demonstration_id'], state['morning_review_id']
        cid, rest = state['queue'][0], state['queue'][1:]
        view = get_case(db, did, cid)
        try:
            response = start_investigation(db, did, cid, dict(schema_version='1', operation_id=str(uuid5(UUID(mid), cid)),
                                                              expected_case_revision=view['case_revision'], retry_of=None))
            completed = investigate(db, response['investigation_id'], agents.investigator, agents=agents)
            outcome, reason = ('INVESTIGATED', None) if completed else ('FAILED', 'The investigation did not complete; retry it from the case.')
        except CommandError as exc:
            outcome, reason = 'FAILED', f'Could not start: {exc.code}.'
        summary = next(item for item in list_cases(db, did)['cases'] if item['id'] == cid)
        draft_ready = bool(get_case(db, did, cid).get('draft'))
        fact = _fact(summary, outcome, reason, draft_ready)
        record(state, 'SUPERVISOR', f"Investigate {summary['client']}", 'SUCCEEDED' if outcome == 'INVESTIGATED' else 'FAILED',
               note=reason or f"Recommended {summary['recommended_action']}.", case_id=cid, started=started,
               to='BRIEFING', kind='CASE_OUTCOME')
        return {'queue': rest, 'outcomes': state['outcomes'] + [fact]}

    def briefing(state):
        facts = sorted(state['outcomes'], key=lambda fact: fact['outcome'] != 'INVESTIGATED')
        fallback = deterministic_briefing(facts)
        if agents is None or agents.briefing is None:
            record(state, 'BRIEFING', 'Write your morning briefing', 'SKIPPED', note='No briefing agent configured; a plain summary is used.')
            return {'briefing': fallback, 'briefing_source': 'DETERMINISTIC'}
        public = [{k: fact[k] for k in ('client', 'invoice_id', 'action', 'balance_text', 'review_at_text', 'draft_ready', 'outcome')} for fact in facts]
        try:
            call = bounded_call(lambda: agents.briefing.summarize(public, timeout=BRIEFING_TIMEOUT_SECONDS), BRIEFING_TIMEOUT_SECONDS)
        except Exception as exc:
            record(state, 'BRIEFING', 'Write your morning briefing', 'FAILED',
                   note=f"{getattr(exc, 'code', type(exc).__name__)}; a plain summary is used.")
            return {'briefing': fallback, 'briefing_source': 'DETERMINISTIC'}
        text = call.value['briefing']
        if not briefing_numbers_supported(text, public):
            record(state, 'BRIEFING', 'Write your morning briefing', 'FALLBACK', call=call,
                   note='The briefing stated a number that is not in your case facts; a plain summary is used.')
            return {'briefing': fallback, 'briefing_source': 'DETERMINISTIC'}
        record(state, 'BRIEFING', 'Write your morning briefing', 'SUCCEEDED', call=call, note='Every number matches your case facts.')
        return {'briefing': text, 'briefing_source': 'AGENT'}

    def next_step(state):
        return 'investigate_next' if state['queue'] else 'briefing'

    graph = StateGraph(ReviewState)
    graph.add_node('select_cases', select_cases)
    graph.add_node('investigate_next', investigate_next)
    graph.add_node('briefing', briefing)
    graph.add_edge(START, 'select_cases')
    graph.add_conditional_edges('select_cases', next_step, ['investigate_next', 'briefing'])
    graph.add_conditional_edges('investigate_next', next_step, ['investigate_next', 'briefing'])
    graph.add_edge('briefing', END)
    return graph.compile()


def run_morning_review(db, agents, mid):
    with db.connection() as con:
        row = con.execute("SELECT * FROM morning_reviews WHERE id=? AND status='RUNNING'", (mid,)).fetchone()
    if row is None:
        return False
    try:
        state = build_morning_review_graph(db, agents).invoke(
            dict(morning_review_id=mid, demonstration_id=row['demonstration_id'], queue=[], outcomes=[]),
            {'run_name': 'promisekeeper-morning-review', 'metadata': {'morning_review_id': mid}, 'recursion_limit': 50})
        with db.transaction() as con:
            con.execute("UPDATE morning_reviews SET status='COMPLETE',terminal_at=?,briefing=?,briefing_source=?,outcomes_json=? WHERE id=? AND status='RUNNING'",
                        (instant(utcnow()), state['briefing'], state['briefing_source'], json.dumps(state['outcomes']), mid))
        return True
    except Exception as exc:
        with db.transaction() as con:
            con.execute("UPDATE morning_reviews SET status='FAILED',terminal_at=?,failure_code=? WHERE id=? AND status='RUNNING'",
                        (instant(utcnow()), getattr(exc, 'code', 'MORNING_REVIEW_FAILED'), mid))
        return False
