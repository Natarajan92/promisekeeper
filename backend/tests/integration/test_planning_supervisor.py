"""Planning supervisor: an agent chooses the next step, code validates every choice and falls back to rule order."""
import json
from uuid import uuid4

from promisekeeper.agents.briefing import ScriptedBriefing
from promisekeeper.agents.communicator import ScriptedCommunicator
from promisekeeper.agents.reviewer import ScriptedReviewer
from promisekeeper.agents.roster import AgentSet
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.agents.supervisor import ScriptedSupervisor, scripted_choice
from promisekeeper.application.cases import create_demonstration
from promisekeeper.orchestration.morning_review import check_choice, get_morning_review, run_morning_review, start_morning_review
from promisekeeper.persistence.sqlite import Database


class Recording(ScriptedSupervisor):
    """Records every context the supervisor is shown."""
    def __init__(self, choices=()):
        super().__init__(choices)
        self.contexts = []

    def next_step(self, context, *, timeout):
        self.contexts.append(json.loads(json.dumps(context)))
        return super().next_step(context, timeout=timeout)


def agents(supervisor):
    return AgentSet(ScriptedInvestigator(), ScriptedCommunicator(), ScriptedReviewer(), ScriptedBriefing(), supervisor=supervisor)


def demo(db):
    return create_demonstration(db, dict(schema_version='1', operation_id=str(uuid4()), catalogue_version='release-0.1',
                                         variant_id=None, clock_mode='REFERENCE'))['demonstration_id']


def review(db, did, supervisor):
    started = start_morning_review(db, did, dict(schema_version='1', operation_id=str(uuid4())))
    run_morning_review(db, agents(supervisor), started['id'])
    return get_morning_review(db, did, started['id'])


def supervisor_rows(result, outcome=None):
    return [row for row in result['agent_activity'] if row['agent'] == 'SUPERVISOR' and (outcome is None or row['outcome'] == outcome)]


def test_scripted_planner_orders_by_risk_and_explains_each_choice(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        result = review(db, demo(db), ScriptedSupervisor())
        worked = [o for o in result['outcomes'] if o['outcome'] == 'INVESTIGATED']
        assert len(worked) == 6 and [o['priority'] for o in worked] == [1, 2, 3, 4, 5, 6]
        clients = [o['client'] for o in worked]
        # Largest open balance first; the fully paid ledger is confirmed last.
        assert clients[0] == 'Northstar Analytics' and clients[-1] == 'Banyan Logistics'
        assert clients != ['Northstar Analytics', 'Meridian Software', 'Cedar Retail Labs', 'Saffron Foods', 'Lotus Interiors', 'Banyan Logistics']
        assert all(o['supervisor_reason'] for o in worked)
        assert not supervisor_rows(result, 'FALLBACK')
        # Once nothing is left to choose, the review goes straight to the briefing.
        assert sum(row['event'].endswith(' next') for row in supervisor_rows(result)) == 6


def test_planner_sees_structured_facts_only_and_replans_with_outcomes(tmp_path):
    planner = Recording()
    with Database(tmp_path / 'db.sqlite') as db:
        review(db, demo(db), planner)
    shown = json.dumps(planner.contexts, ensure_ascii=False)
    for customer_text in ('pakka', 'We will pay', 'We paid the remaining', 'payment today kar diya'):
        assert customer_text not in shown
    assert [len(c['done']) for c in planner.contexts] == list(range(len(planner.contexts)))
    assert [len(c['pending']) for c in planner.contexts] == [6, 5, 4, 3, 2, 1]


def test_invalid_case_choice_falls_back_to_rule_order_and_keeps_asking(tmp_path):
    planner = Recording([dict(action='INVESTIGATE', case='PK-999', reason='Made up.')])
    with Database(tmp_path / 'db.sqlite') as db:
        result = review(db, demo(db), planner)
    fallbacks = supervisor_rows(result, 'FALLBACK')
    assert len(fallbacks) == 1 and 'not waiting in this review' in fallbacks[0]['note']
    assert result['outcomes'][0]['client'] == 'Northstar Analytics'  # rule order picked PK-001
    assert len(planner.contexts) > 1, 'an invalid choice does not switch the planner off'
    assert sum(o['outcome'] == 'INVESTIGATED' for o in result['outcomes']) == 6


def test_early_finish_with_due_cases_is_refused(tmp_path):
    finish = dict(action='FINISH', case=None, reason='Done already.')
    with Database(tmp_path / 'db.sqlite') as db:
        result = review(db, demo(db), ScriptedSupervisor([finish] * 6 + [finish]))
    assert sum(o['outcome'] == 'INVESTIGATED' for o in result['outcomes']) == 6
    assert len(supervisor_rows(result, 'FALLBACK')) == 6
    assert all('tried to finish while a due case' in row['note'] for row in supervisor_rows(result, 'FALLBACK'))


def test_unavailable_planner_is_switched_off_for_the_rest_of_the_run(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        result = review(db, demo(db), ScriptedSupervisor([RuntimeError('provider down')]))
    assert result['status'] == 'COMPLETE'
    assert len(supervisor_rows(result, 'FALLBACK')) == 1
    assert [o['client'] for o in result['outcomes']][:3] == ['Northstar Analytics', 'Meridian Software', 'Cedar Retail Labs']


def test_planner_may_recheck_a_current_case_then_finish(tmp_path):
    with Database(tmp_path / 'db.sqlite') as db:
        did = demo(db)
        review(db, did, ScriptedSupervisor())
        recheck = dict(action='INVESTIGATE', case='PK-002', reason='Review date is close; re-checking Meridian now.')
        done = dict(action='FINISH', case=None, reason='Everything else is current.')
        again = review(db, did, ScriptedSupervisor([recheck, done]))
    worked = [o for o in again['outcomes'] if o['outcome'] == 'INVESTIGATED']
    assert [o['client'] for o in worked] == ['Meridian Software']
    assert worked[0]['supervisor_reason'].startswith('Review date is close')
    assert sum(o['outcome'] == 'SKIPPED' for o in again['outcomes']) == 5
    assert not supervisor_rows(again, 'FALLBACK')


def test_check_choice_guardrails():
    pending = [dict(case='PK-001', must_investigate=True), dict(case='PK-002', must_investigate=False)]
    assert check_choice(dict(action='INVESTIGATE', case='PK-002', reason='ok'), pending) is None
    assert 'not waiting' in check_choice(dict(action='INVESTIGATE', case='PK-003', reason='x'), pending)
    assert 'due case' in check_choice(dict(action='FINISH', case=None, reason='x'), pending)
    assert check_choice(dict(action='FINISH', case=None, reason='x'), pending[1:]) is None
    assert 'must not name' in check_choice(dict(action='FINISH', case='PK-002', reason='x'), pending[1:])
    assert 'format' in check_choice(dict(action='SEND', case='PK-001', reason='x'), pending)
    assert 'format' in check_choice(dict(action='INVESTIGATE', case='PK-001', reason=''), pending)
    assert 'format' in check_choice(dict(action='INVESTIGATE', case='PK-001', reason='x', approve=True), pending)


def test_scripted_policy_prefers_review_required_then_payment_claims():
    base = dict(client='C', balance_text='INR 10.00', days_overdue=1, recommended_action=None, review_required=False, must_investigate=True)
    pending = [dict(base, case='PK-001', balance_text='INR 90,000.00'),
               dict(base, case='PK-002', recommended_action='VERIFY_PAYMENT'),
               dict(base, case='PK-003', review_required=True)]
    assert scripted_choice(dict(pending=pending))['case'] == 'PK-003'
    assert scripted_choice(dict(pending=pending[:2]))['case'] == 'PK-002'
    assert scripted_choice(dict(pending=[dict(base, case='PK-004', must_investigate=False)]))['action'] == 'FINISH'


def test_supervisor_evaluation_suite_scores_validity_and_accuracy_offline():
    from promisekeeper.agents.llm_client import scripted_call
    from promisekeeper.application.agent_evaluation import evaluate_supervisor
    scripted = evaluate_supervisor(ScriptedSupervisor())
    assert scripted['mode'] == 'OFFLINE_SCRIPTED' and scripted['live_qualified'] is False
    assert scripted['metrics']['validity'] == 1.0 and scripted['metrics']['accuracy'] == 1.0
    assert scripted['metrics']['reason_clean'] == 1.0

    class AlwaysFinish:
        model = 'test-small-model'
        def next_step(self, context, *, timeout):
            return scripted_call({'action': 'FINISH', 'case': None, 'reason': 'PK-001 is done.'})
    lazy = evaluate_supervisor(AlwaysFinish())
    assert lazy['metrics']['reason_clean'] == 0.0
    assert lazy['mode'] == 'LIVE' and lazy['model'] == 'test-small-model'
    assert lazy['metrics']['validity'] < 0.5
    assert {item['id'] for item in lazy['items'] if item['correct']} <= {'SV-04-all-current', 'SV-06-close-review-date'}


def test_cli_supervisor_suite_runs_offline_and_rejects_bad_model_names(tmp_path):
    import pytest
    from promisekeeper.cli import run_agent_suite
    from promisekeeper.config import Settings
    report = run_agent_suite(Settings('STUB', 'm', tmp_path / 'x.sqlite', None), 'supervisor', repeats=1)
    assert report['suite'] == 'supervisor' and report['metrics']['validity'] == 1.0
    with pytest.raises(ValueError):
        run_agent_suite(Settings('LIVE', 'm', tmp_path / 'x.sqlite', 'k'), 'supervisor', repeats=1, models=['bad model; rm'])
