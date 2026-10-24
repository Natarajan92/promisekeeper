"""Acceptance runners exercise saved product behavior, independently of LIVE quality."""
import json

import pytest

from promisekeeper.config import Settings


def test_fixture_runner_covers_every_canonical_branch_and_saved_review(tmp_path):
    from promisekeeper.application.fixture_evaluation import evaluate_fixtures
    from promisekeeper.application.evaluations import evaluation_manifest
    output = tmp_path / 'fixtures.json'
    settings = Settings('STUB', 'unused', tmp_path / 'unused.sqlite', None)
    report = evaluate_fixtures(settings, catalogue='release-0.1', output=output)
    assert report['passed'], [r for r in report['runs'] if not r['passed']]
    assert [r['case'] for r in report['runs']] == [r['id'] for r in evaluation_manifest()]
    assert len(report['runs']) == 51
    assert report['live_qualified'] is False
    assert len(report['failure_runs']) == 4
    assert all(r['passed'] and r['saved_result_preserved'] for r in report['failure_runs'])
    assert all(r['checks']['financial_correct'] and r['checks']['approval_correct'] for r in report['runs'])
    assert json.loads(output.read_text()) == report
    with pytest.raises(ValueError, match='exists'):
        evaluate_fixtures(settings, catalogue='release-0.1', output=output)


@pytest.mark.parametrize('suite,kwargs', [('responsiveness', {'trials_per_case': 9}), ('preservation', {'cycles': 9})])
def test_measurement_runner_rejects_nonrelease_sample_counts_before_network(tmp_path, suite, kwargs):
    from promisekeeper.application.measurements import measure
    settings = Settings('LIVE', 'zai-org/GLM-5.3-Flash', tmp_path / 'unused.sqlite', 'test-only')
    with pytest.raises(ValueError, match='10'):
        measure(settings, suite=suite, report=tmp_path / 'measurement.json', **kwargs)


@pytest.mark.parametrize('mode,model', [('STUB', 'zai-org/GLM-5.3-Flash'), ('LIVE', 'wrong-model')])
def test_measurement_runner_requires_declared_live_frozen_model(tmp_path, mode, model):
    from promisekeeper.application.measurements import measure
    settings = Settings(mode, model, tmp_path / 'unused.sqlite', None)
    with pytest.raises(ValueError, match='LIVE'):
        measure(settings, suite='preservation', report=tmp_path / 'measurement.json')


def test_responsiveness_harness_runs_thirty_real_http_starts_without_live_calls(tmp_path):
    from promisekeeper.application.measurements import _responsiveness
    settings = Settings('STUB', 'test-model', tmp_path / 'unused.sqlite', None)
    report = {'runs': []}
    _responsiveness(settings, tmp_path / 'report.json', report, tmp_path / 'measurement.sqlite')
    assert report['passed']
    assert len(report['runs']) == 30
    assert all(row['status'] == 'COMPLETE' for row in report['runs'])
    assert all('returned_model' in row and 'response_id' in row for row in report['runs'])
    assert report['browser_paint_measured'] is False


def test_preservation_harness_preserves_exact_saved_data_across_ten_subprocess_cycles(tmp_path):
    from promisekeeper.application.measurements import _preservation
    settings = Settings('STUB', 'test-model', tmp_path / 'unused.sqlite', None)
    report = {'runs': []}
    _preservation(settings, tmp_path / 'report.json', report, tmp_path / 'measurement.sqlite')
    assert report['passed'], report
    assert len(report['runs']) == 10
    assert all(row['before_hash'] == row['after_hash'] for row in report['runs'])
    assert all(row['duplicate_counts']['replayed_mutations'] == 0 for row in report['runs'])


def test_fixture_cli_never_loads_provider_credentials(monkeypatch, capsys):
    from promisekeeper import cli
    from promisekeeper.application import fixture_evaluation
    def forbidden():
        raise AssertionError('Offline fixture CLI must not load credentials')
    monkeypatch.setattr(cli, 'load_settings', forbidden)
    calls = []
    def evaluate(**kwargs):
        calls.append(kwargs)
        return dict(status='COMPLETE', passed=True, runs=[])
    monkeypatch.setattr(fixture_evaluation, 'evaluate_fixtures', evaluate)
    cli.main(['evaluate', '--suite', 'fixtures', '--catalogue', 'release-0.1'])
    assert calls == [dict(catalogue='release-0.1', output='reports/fixture-evaluation.json')]
    assert json.loads(capsys.readouterr().out)['live_qualified'] is False
