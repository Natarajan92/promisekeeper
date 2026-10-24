"""LIVE is opt-in and can never be satisfied by a scripted adapter."""
import pytest

def test_evaluation_manifest_covers_baseline_updates_and_both_fv18_orderings():
    from promisekeeper.application.evaluations import evaluation_manifest
    entries=evaluation_manifest()
    assert {'baseline:PK-001','baseline:PK-002','baseline:PK-003'} <= {e['id'] for e in entries}
    assert {'PK-001-U1','PK-002-U1','PK-003-U1'} <= {event for e in entries for event in e['events']}
    assert {'FV-16-LINKED','FV-16-UNLINKED','FV-18-A','FV-18-B'} <= {e['variant'] for e in entries}
    assert len([e for e in entries if e['variant']=='FV-18-A'])>=3
    assert len([e for e in entries if e['variant']=='FV-18-B'])>=3

@pytest.mark.live
def test_live_release_candidate(tmp_path):
    from promisekeeper.application.evaluations import evaluate
    from promisekeeper.config import load_settings
    settings=load_settings()
    report=evaluate(settings,catalogue='release-0.1',repeats=3,output=tmp_path/'live-evaluation.json')
    assert report['qualified'] and report['qualification_scope']=='RELEASE' and report['status'] in {'PASS','PASS_WITH_AVAILABILITY_GAPS'},report
