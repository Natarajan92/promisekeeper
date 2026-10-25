"""Graph 2: the Morning Review supervisor.

Code first decides which open cases are due (never investigated, evidence changed, or review
date reached) and which are closed or already running. A planning supervisor agent then chooses,
one step at a time, which case to investigate next or when to finish, re-planning after every
result; code validates each choice and falls back to rule order. The Briefing agent then writes
an owner summary. It never sends messages, approves drafts or closes cases: those
remain owner decisions. A briefing that states an unsupported number is replaced by the
deterministic briefing.
"""
from datetime import datetime
import json
import time
from typing import TypedDict
from uuid import UUID, uuid4, uuid5

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from promisekeeper.agents.briefing import briefing_numbers_supported, deterministic_briefing
from promisekeeper.agents.supervisor import SupervisorStep
from promisekeeper.application.agent_activity import list_agent_activity, record_agent
from promisekeeper.application.cases import get_case, list_cases
from promisekeeper.application.draft_templates import _amount
from promisekeeper.application.operations import CommandError, instant, utcnow
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.domain.dates import IST
from promisekeeper.orchestration.deadlines import bounded_call
from promisekeeper.persistence.repositories import demonstration

BRIEFING_TIMEOUT_SECONDS = 20
SUPERVISOR_TIMEOUT_SECONDS = 15
CURRENT = 'The saved recommendation is still current.'


class ReviewState(TypedDict, total=False):
    morning_review_id: str
    demonstration_id: str
    pending: list
    notes: dict
    next: str | None
    next_reason: str
    order: int
    planner_off: bool
    outcomes: list
    briefing: str
    briefing_source: str
    started_by: str


def _view(con, row):
    return dict(schema_version='1', id=row['id'], demonstration_id=row['demonstration_id'], status=row['status'],
                started_at=row['started_at'], terminal_at=row['terminal_at'], briefing=row['briefing'],
                briefing_source=row['briefing_source'], failure_code=row['failure_code'], outcomes=json.loads(row['outcomes_json']),
                started_by=row['started_by'],
                agent_activity=list_agent_activity(con, morning_review_id=row['id']))


def start_morning_review(db, did, request, *, started_by='OWNER'):
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
        con.execute("INSERT INTO morning_reviews (id,demonstration_id,operation_id,status,started_at,started_by) VALUES (?,?,?,'RUNNING',?,?)",
                    (mid, did, request['operation_id'], instant(utcnow()), started_by))
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
    return CURRENT


def case_decisions(db, did):
    """Each case summary with None when it needs a fresh investigation, else the reason to leave it."""
    listing = list_cases(db, did)
    evaluated_at = datetime.fromisoformat(listing['evaluation_at'])
    with db.connection() as con:
        running = {row[0] for row in con.execute("SELECT case_id FROM investigations WHERE demonstration_id=? AND status='RUNNING'", (did,))}
    return [(summary, _needs_work(summary, summary['id'] in running, evaluated_at)) for summary in listing['cases']]


def _fact(summary, outcome, reason=None, draft_ready=False):
    review_at = summary['review_at']
    return dict(case_id=summary['id'], client=summary['client'], invoice_id=summary['invoice_id'], outcome=outcome,
                action=summary['recommended_action'], reason=reason,
                balance_text=_amount(summary['balance']) if summary['balance'] else None,
                review_at_text=datetime.fromisoformat(review_at).astimezone(IST).strftime('%d %b %Y, %H:%M IST') if review_at else None,
                draft_ready=draft_ready)


def _days_overdue(summary, evaluated_at):
    if not summary['due_at']:
        return 0
    return max(0, (evaluated_at - datetime.fromisoformat(summary['due_at'])).days)


def _candidate(summary, reason, evaluated_at):
    """Structured facts only: the supervisor never sees customer message text."""
    review_at = summary['review_at']
    return dict(case=summary['catalogue_case_id'], client=summary['client'], invoice_id=summary['invoice_id'],
                balance_text=_amount(summary['balance']) if summary['balance'] else None, due_text=summary['due_text'],
                days_overdue=_days_overdue(summary, evaluated_at), recommended_action=summary['recommended_action'],
                review_required=summary['review_required'],
                review_at_text=datetime.fromisoformat(review_at).astimezone(IST).strftime('%d %b %Y, %H:%M IST') if review_at else None,
                must_investigate=reason is None, rule_note=reason)


def rule_choice(pending):
    """Fallback when the planner is absent, fails or proposes something invalid: rule order, due cases only."""
    due = [item for item in pending if item['must_investigate']]
    if due:
        return dict(action='INVESTIGATE', case=due[0]['case'], reason='Taken in rule order.')
    return dict(action='FINISH', case=None, reason='Every case that needed work is done.')


def check_choice(choice, pending):
    """Guardrails on a planner choice; returns the problem, or None when the choice may run."""
    try:
        step = SupervisorStep.model_validate(choice)
    except ValidationError:
        return 'the choice did not match the allowed format'
    codes = {item['case'] for item in pending}
    if step.action == 'INVESTIGATE':
        return None if step.case in codes else 'it named a case that is not waiting in this review'
    if step.case is not None:
        return 'a finish choice must not name a case'
    if any(item['must_investigate'] for item in pending):
        return 'it tried to finish while a due case was still waiting'
    return None


def build_morning_review_graph(db, agents):
    from promisekeeper.orchestration.investigate import investigate
    planner = getattr(agents, 'supervisor', None) if agents is not None else None

    def record(state, agent, event, outcome, note=None, call=None, case_id=None, started=None, to=None, kind=None):
        record_agent(db, demonstration_id=state['demonstration_id'], case_id=case_id, morning_review_id=state['morning_review_id'],
                     agent=agent, event=event, outcome=outcome, note=note, model=getattr(call, 'model', None), to=to, kind=kind,
                     input_tokens=getattr(call, 'input_tokens', None), output_tokens=getattr(call, 'output_tokens', None),
                     latency_ms=call.latency_ms if call else (int((time.monotonic() - started) * 1000) if started else None))

    def summaries(state):
        listing = list_cases(db, state['demonstration_id'])
        return datetime.fromisoformat(listing['evaluation_at']), {summary['id']: summary for summary in listing['cases']}

    def select_cases(state):
        started = time.monotonic()
        did = state['demonstration_id']
        decisions = case_decisions(db, did)
        outcomes, pending, notes = [], [], {}
        for summary, reason in decisions:
            # Closed and running cases are never handed to the planner; current ones are optional re-checks.
            if reason is not None and reason != CURRENT:
                outcomes.append(_fact(summary, 'SKIPPED', reason))
                record(state, 'SUPERVISOR', f"Skip {summary['client']}", 'SKIPPED', note=reason, case_id=summary['id'])
                continue
            pending.append(summary['id'])
            notes[summary['id']] = reason
        due = sum(1 for cid in pending if notes[cid] is None)
        prefix = 'Started automatically because cases were due. ' if state.get('started_by') == 'AUTONOMOUS' else ''
        mode = ('The planner chooses the order and re-plans after each result.' if planner
                else 'No planning supervisor is configured; rule order is used.')
        record(state, 'SUPERVISOR', 'Choose which cases need work', 'SUCCEEDED',
               note=f'{prefix}{due} of {len(decisions)} cases need a fresh investigation; {len(pending) - due} more can be re-checked. {mode}',
               started=started, to='INTAKE', kind='CASE_SELECTION')
        return {'pending': pending, 'notes': notes, 'outcomes': outcomes, 'order': 0, 'planner_off': planner is None}

    def decide(state):
        started = time.monotonic()
        evaluated_at, by_id = summaries(state)
        pending = [_candidate(by_id[cid], state['notes'].get(cid), evaluated_at) for cid in state['pending']]
        context = dict(pending=pending, steps_left=len(pending),
                       done=[{k: fact.get(k) for k in ('client', 'outcome', 'action', 'draft_ready')}
                             for fact in state['outcomes'] if fact['outcome'] != 'SKIPPED'])
        choice, call, problem = None, None, None
        if not state['planner_off']:
            try:
                call = bounded_call(lambda: planner.next_step(context, timeout=SUPERVISOR_TIMEOUT_SECONDS), SUPERVISOR_TIMEOUT_SECONDS)
                choice = call.value
                problem = check_choice(choice, pending)
            except Exception as exc:
                problem = f"the planner was unavailable ({getattr(exc, 'code', type(exc).__name__)})"
        if choice is None or problem:
            choice = rule_choice(pending)
        target = next((cid for cid in state['pending'] if by_id[cid]['catalogue_case_id'] == choice['case']), None)
        finishing = choice['action'] == 'FINISH'
        event = 'Finish the review and brief you' if finishing else f"Investigate {by_id[target]['client']} next"
        to, kind = ('BRIEFING', 'CASE_OUTCOME') if finishing else ('INTAKE', 'CASE_SELECTION')
        if problem:
            record(state, 'SUPERVISOR', event, 'FALLBACK', note=f"Planner choice not used because {problem}. {choice['reason']}",
                   call=call, case_id=target, started=None if call else started, to=to, kind=kind)
        elif not state['planner_off']:
            record(state, 'SUPERVISOR', event, 'SUCCEEDED', note=choice['reason'], call=call, case_id=target, to=to, kind=kind)
        # An unavailable planner is not asked again in this run, so a provider outage cannot stall the review.
        return {'next': None if finishing else target, 'next_reason': choice['reason'],
                'planner_off': state['planner_off'] or bool(problem and call is None)}

    def investigate_next(state):
        started = time.monotonic()
        did, mid, cid = state['demonstration_id'], state['morning_review_id'], state['next']
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
        order = state['order'] + 1
        fact = dict(_fact(summary, outcome, reason, draft_ready), priority=order, supervisor_reason=state['next_reason'])
        record(state, 'SUPERVISOR', f"Investigate {summary['client']}", 'SUCCEEDED' if outcome == 'INVESTIGATED' else 'FAILED',
               note=reason or f"Recommended {summary['recommended_action']}.", case_id=cid, started=started,
               to='BRIEFING', kind='CASE_OUTCOME')
        return {'pending': [item for item in state['pending'] if item != cid], 'outcomes': state['outcomes'] + [fact], 'order': order}

    def briefing(state):
        _, by_id = summaries(state)
        leftover = [_fact(by_id[cid], 'SKIPPED', state['notes'].get(cid) or CURRENT) for cid in state['pending']]
        worked = sorted((fact for fact in state['outcomes'] if fact['outcome'] != 'SKIPPED'), key=lambda fact: fact['priority'])
        outcomes = worked + [fact for fact in state['outcomes'] if fact['outcome'] == 'SKIPPED'] + leftover
        facts = sorted(outcomes, key=lambda fact: fact['outcome'] != 'INVESTIGATED')
        fallback = deterministic_briefing(facts)
        if agents is None or agents.briefing is None:
            record(state, 'BRIEFING', 'Write your morning briefing', 'SKIPPED', note='No briefing agent configured; a plain summary is used.')
            return {'outcomes': outcomes, 'briefing': fallback, 'briefing_source': 'DETERMINISTIC'}
        public = [{k: fact[k] for k in ('client', 'invoice_id', 'action', 'balance_text', 'review_at_text', 'draft_ready', 'outcome')} for fact in facts]
        try:
            call = bounded_call(lambda: agents.briefing.summarize(public, timeout=BRIEFING_TIMEOUT_SECONDS), BRIEFING_TIMEOUT_SECONDS)
        except Exception as exc:
            record(state, 'BRIEFING', 'Write your morning briefing', 'FAILED',
                   note=f"{getattr(exc, 'code', type(exc).__name__)}; a plain summary is used.")
            return {'outcomes': outcomes, 'briefing': fallback, 'briefing_source': 'DETERMINISTIC'}
        text = call.value['briefing']
        if not briefing_numbers_supported(text, public):
            record(state, 'BRIEFING', 'Write your morning briefing', 'FALLBACK', call=call,
                   note='The briefing stated a number that is not in your case facts; a plain summary is used.')
            return {'outcomes': outcomes, 'briefing': fallback, 'briefing_source': 'DETERMINISTIC'}
        record(state, 'BRIEFING', 'Write your morning briefing', 'SUCCEEDED', call=call, note='Every number matches your case facts.')
        return {'outcomes': outcomes, 'briefing': text, 'briefing_source': 'AGENT'}

    def after_select(state):
        return 'decide' if state['pending'] else 'briefing'

    def after_decide(state):
        return 'investigate_next' if state['next'] else 'briefing'

    graph = StateGraph(ReviewState)
    graph.add_node('select_cases', select_cases)
    graph.add_node('decide', decide)
    graph.add_node('investigate_next', investigate_next)
    graph.add_node('briefing', briefing)
    graph.add_edge(START, 'select_cases')
    graph.add_conditional_edges('select_cases', after_select, ['decide', 'briefing'])
    graph.add_conditional_edges('decide', after_decide, ['investigate_next', 'briefing'])
    # Every INVESTIGATE removes one pending case, so the loop is bounded by the number of open cases.
    graph.add_conditional_edges('investigate_next', after_select, ['decide', 'briefing'])
    graph.add_edge('briefing', END)
    return graph.compile()


def run_morning_review(db, agents, mid):
    with db.connection() as con:
        row = con.execute("SELECT * FROM morning_reviews WHERE id=? AND status='RUNNING'", (mid,)).fetchone()
    if row is None:
        return False
    try:
        state = build_morning_review_graph(db, agents).invoke(
            dict(morning_review_id=mid, demonstration_id=row['demonstration_id'], pending=[], notes={}, outcomes=[], started_by=row['started_by']),
            {'run_name': 'promisekeeper-morning-review', 'metadata': {'morning_review_id': mid}, 'recursion_limit': 100})
        with db.transaction() as con:
            con.execute("UPDATE morning_reviews SET status='COMPLETE',terminal_at=?,briefing=?,briefing_source=?,outcomes_json=? WHERE id=? AND status='RUNNING'",
                        (instant(utcnow()), state['briefing'], state['briefing_source'], json.dumps(state['outcomes']), mid))
        return True
    except Exception as exc:
        with db.transaction() as con:
            con.execute("UPDATE morning_reviews SET status='FAILED',terminal_at=?,failure_code=? WHERE id=? AND status='RUNNING'",
                        (instant(utcnow()), getattr(exc, 'code', 'MORNING_REVIEW_FAILED'), mid))
        return False
