"""Agent evaluation harness: safety, review, fallback, injection and Hinglish metrics."""
import json
from dataclasses import replace
from promisekeeper.agents.communicator import ScriptedCommunicator
from promisekeeper.agents.roster import build_agents
from promisekeeper.application.agent_evaluation import (
    ScriptedHinglishClassifier, ScriptedJudge, evaluate_agents, evaluate_hinglish, load_hinglish_set, upload_to_langsmith)
from promisekeeper.config import load_settings


def stub_agents(tmp_path):
    return build_agents(load_settings({}, workspace=tmp_path))


def test_offline_agent_evaluation_computes_metrics(tmp_path):
    report = evaluate_agents(stub_agents(tmp_path), repeats=2, judge=ScriptedJudge())
    metrics = report['metrics']
    assert report['suite'] == 'agents' and report['live_qualified'] is False and len(report['runs']) == 16
    assert metrics['safety_pass_rate'] == 1.0 and metrics['reviewer_accept_rate'] == 1.0
    assert metrics['fallback_rate'] == 0.0 and metrics['injection_blocked_rate'] == 1.0
    assert metrics['judge_mean_tone'] == 4.0 and metrics['latency_ms_p95'] == 0


def test_unsafe_notes_fall_back_and_count_against_safety(tmp_path):
    agents = replace(stub_agents(tmp_path), communicator=ScriptedCommunicator(['A late fee of INR 500 applies.']))
    metrics = evaluate_agents(agents, repeats=1, judge=None)['metrics']
    assert metrics['safety_pass_rate'] == 0.0 and metrics['fallback_rate'] == 1.0
    assert metrics['injection_blocked_rate'] == 1.0 and metrics['judge_mean_tone'] is None


def test_injection_steering_is_counted_not_blocked(tmp_path):
    agents = replace(stub_agents(tmp_path), communicator=ScriptedCommunicator(['We have verified everything on our side.']))
    report = evaluate_agents(agents, repeats=1, judge=None)
    steered = [run['case_id'] for run in report['runs'] if run['steered']]
    assert steered == ['INJ-RECEIVED'] and report['metrics']['injection_blocked_rate'] == 0.8


def test_hinglish_scoring_matches_expected_fields():
    items = load_hinglish_set()['items']
    perfect = evaluate_hinglish(ScriptedHinglishClassifier())
    assert perfect['metrics']['accuracy'] == 1.0 and len(perfect['items']) == len(items) == 8

    class AlwaysNone:
        model = 'none'
        def classify(self, message, *, timeout):
            return {'kind': 'NONE', 'amount_text': None, 'date_text': None}
    weak = evaluate_hinglish(AlwaysNone())['metrics']
    assert weak['accuracy'] == 1 / 8 and weak['kind_accuracy'] == 1 / 8


def test_langsmith_upload_skipped_without_key(tmp_path):
    assert upload_to_langsmith(evaluate_agents(stub_agents(tmp_path), repeats=1, judge=None), 'pk-agents') is False


def test_cli_runs_offline_agent_suite(tmp_path, monkeypatch):
    from promisekeeper import cli
    monkeypatch.setenv('PK_AGENT_MODE', 'STUB')
    output = tmp_path / 'agents.json'
    cli.main(['evaluate', '--suite', 'agents', '--catalogue', 'release-0.1', '--repeats', '1', '--output', str(output)])
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['suite'] == 'agents' and report['live_qualified'] is False and len(report['runs']) == 8
