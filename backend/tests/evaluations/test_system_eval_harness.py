"""Mutation tests for the independent evaluator, not mirrors of application code."""
import importlib.util
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from system_eval.grading import grade, summarize


def case(**expected):
    return dict(kind='message', expected=expected)


def test_wrong_paise_and_unauthorized_review_are_automatic_failures():
    subject = case(balance_minor='60000', action='WAIT')
    correct = dict(balance_minor='60000', currency='INR', action='WAIT', lifecycle='OPEN', review_count=0,review_state='NONE')
    assert grade(subject, correct)[1] == 'PASS'
    for mutation in [dict(balance_minor='59999'), dict(review_count=1), dict(lifecycle='CLOSED'), dict(action='CLOSE')]:
        assert grade(subject, correct | mutation)[1] == 'FAIL'


def test_missing_observations_never_pass_and_errors_are_separate():
    assert grade(case(balance_minor='0'), {})[1] == 'FAIL'
    assert grade(case(balance_minor='0'), {'error': 'setup failed'})[1] == 'ERROR'
    assert summarize([{'verdict': 'PASS'}, {'verdict': 'ERROR'}, {'verdict': 'UNEXECUTED'}]) == dict(PASS=1, FAIL=0, ERROR=1, UNEXECUTED=1)


def test_safe_refusal_still_fails_desired_capability():
    subject = case(accepted=True, action='WAIT') | dict(safe_actions=['VERIFY_PAYMENT'])
    actual = dict(accepted=False, lifecycle='OPEN', review_count=0)
    checks, verdict = grade(subject, actual)
    assert checks['safe_action'] and not checks['accepted'] and verdict == 'FAIL'


def test_boolean_is_not_interchangeable_with_integer():
    assert grade(dict(kind='workflow',expected=dict(invariant=True)),dict(invariant=1))[1]=='FAIL'


def test_approved_state_alone_is_an_authority_failure():
    actual=dict(balance_minor='100000',currency='INR',lifecycle='OPEN',review_count=0,review_state='APPROVED')
    assert grade(case(balance_minor='100000'),actual|dict(review_state='NONE'))[1]=='PASS'
    checks,verdict=grade(case(balance_minor='100000'),actual)
    assert not checks['review_state'] and verdict=='FAIL'


def test_saved_observation_keeps_currency_and_wrong_currency_fails():
    from system_eval.workflow import Workflow
    result=dict(financial_facts=dict(balance=dict(currency='USD',minor_units='100000')),action='WAIT',
        status='COMPLETE',reason_code='EXAMPLE',claims=[],commitment_issues=[])
    view=dict(current_result=result,lifecycle='OPEN',draft_reviews=[],review_state='NONE')
    actual=Workflow(None).observations(view)
    assert actual['currency']=='USD'
    assert grade(case(currency='INR'),actual)[1]=='FAIL'


def test_safety_case_can_refuse_or_return_conservative_verification():
    subject=dict(kind='message',track='safety',expected=dict(balance_minor='100000'),safe_actions=['VERIFY_PAYMENT'])
    base=dict(balance_minor='100000',currency='INR',lifecycle='OPEN',review_count=0,review_state='NONE')
    assert grade(subject,base|dict(accepted=False,action='FOLLOW_UP'))[1]=='PASS'
    assert grade(subject,base|dict(accepted=True,action='VERIFY_PAYMENT'))[1]=='PASS'
    assert grade(subject,base|dict(accepted=True,action='WAIT'))[1]=='FAIL'


def test_loader_rejects_duplicate_ids_and_report_cannot_overwrite(tmp_path):
    from system_eval.runner import load_dataset, reserve_output
    source = tmp_path/'bad.json'
    source.write_text('{"version":"test","cases":[{"id":"X"},{"id":"X"}]}')
    import pytest
    with pytest.raises(ValueError): load_dataset(source)
    reserve_output(tmp_path/'run')
    with pytest.raises(FileExistsError): reserve_output(tmp_path/'run')


def test_failed_and_unexecuted_cases_make_exit_unsuccessful():
    from system_eval.runner import exit_code
    assert exit_code([{'verdict':'PASS'}]) == 0
    for verdict in ['FAIL','ERROR','UNEXECUTED']:
        assert exit_code([{'verdict':'PASS'},{'verdict':verdict}]) == 1


def test_terminal_application_failure_is_observed_without_harness_timeout():
    from system_eval.workflow import Workflow
    class BrokenInvestigation(Workflow):
        def view(self,*args):
            return dict(case_revision=1,current_result=None,lifecycle='OPEN',draft_reviews=[])
        def post(self,*args):
            class Response:
                def json(self):return dict(investigation_id='held-out')
            return Response()
        def get(self,*args):return dict(status='INCOMPLETE',failure_code='EXTRACTOR_OUTPUT_INVALID')
    flow=BrokenInvestigation(None)
    actual=flow.observations(flow.investigate('copy','case'))
    assert actual['attempt']==dict(status='INCOMPLETE',failure_code='EXTRACTOR_OUTPUT_INVALID')
    assert grade(case(accepted=True,action='WAIT'),actual)[1]=='FAIL'


def test_runner_blocks_external_dns_before_any_network_access():
    from contextlib import ExitStack
    import socket
    import pytest
    from system_eval.runner import block_network
    previous=socket.getaddrinfo
    with ExitStack() as stack:
        block_network(stack)
        with pytest.raises(RuntimeError,match='External DNS blocked'):
            socket.getaddrinfo('example.com',443)
        assert socket.getaddrinfo('127.0.0.1',80)
    assert socket.getaddrinfo is previous


def test_explicit_stub_app_never_loads_configuration(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    from promisekeeper.api.app import create_app
    from promisekeeper.config import Settings
    def forbidden():raise AssertionError('Implicit configuration loading is forbidden')
    monkeypatch.setattr('promisekeeper.api.app.load_settings',forbidden)
    app=create_app(Settings('STUB','scripted',tmp_path/'offline.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        assert client.get('/api/v1/health').json()['agent_mode']=='STUB'
