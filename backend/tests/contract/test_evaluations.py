def test_missing_credentials_returns_blocked_report_without_substituting_stub(tmp_path):
    from promisekeeper.application.evaluations import evaluate
    from promisekeeper.config import load_settings
    settings=load_settings({},workspace=tmp_path)
    report=evaluate(settings,catalogue='release-0.1',repeats=3,output=tmp_path/'report.json')
    assert report['status']=='BLOCKED'
    assert report['agent_mode']=='LIVE'
    assert report['blocking_reason']=='CAPABILITY_UNAVAILABLE'
    assert report['runs']==[]
    assert report['request_parameters']==dict(temperature=0,max_tokens=8000)

def test_fabricated_model_question_is_policy_rejected_with_unknown_product_checks(tmp_path,monkeypatch):
    from promisekeeper.application.evaluations import evaluate,evaluation_manifest
    from promisekeeper.agents.nebius import NebiusInvestigator
    from promisekeeper.agents.scripted import ScriptedInvestigator
    from promisekeeper.config import load_settings
    def fake(self,request,*,timeout):
        response=ScriptedInvestigator().extract(request,timeout=timeout)
        span=response.output['commitments'][0]['source']
        response.output['unresolved']=[dict(field='AMOUNT',sources=[span])]
        return response
    monkeypatch.setattr(NebiusInvestigator,'extract',fake)
    report=evaluate(load_settings({'NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path),catalogue='release-0.1',repeats=1,output=tmp_path/'report.json',manifest=evaluation_manifest()[:1])
    assert report['status']=='FAIL'
    assert report['runs'][0]['extraction_policy_correct'] is False
    assert report['runs'][0]['source_validation_correct'] is True
    assert report['runs'][0]['validated_uncertainty']['unresolved'][0]['field']=='AMOUNT'
    assert report['runs'][0]['result_present'] is False
    assert report['runs'][0]['actual_findings'] is None
    assert all(report['runs'][0][key] is None for key in ('findings_source_validation_correct','findings_soundness_correct','findings_completeness_correct','findings_duplicates_correct'))
    assert report['evaluator_version']=='5'
    assert report['criteria_version']=='gate-iii-live-4'


def test_safe_provider_unavailability_retains_unknown_checks_and_persisted_retry_evidence(tmp_path,monkeypatch):
    from promisekeeper.application.evaluations import evaluate,evaluation_manifest
    from promisekeeper.agents.nebius import NebiusInvestigator
    from promisekeeper.agents.protocol import InvestigatorFailure
    from promisekeeper.config import load_settings
    def fake(self,request,*,timeout):raise InvestigatorFailure('PROVIDER_REJECTED_REQUEST',transient=True)
    monkeypatch.setattr(NebiusInvestigator,'extract',fake)
    report=evaluate(load_settings({'NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path),catalogue='release-0.1',repeats=1,output=tmp_path/'report.json',manifest=evaluation_manifest()[:1])
    row=report['runs'][0]
    assert report['status']=='BLOCKED'
    assert row['status']=='INCOMPLETE_PROVIDER'
    assert row['attempt_status']=='INCOMPLETE' and row['action'] is None
    assert row['validated_uncertainty'] is None
    assert row['actual_candidate_facts'] is None
    assert row['expected_candidate_facts']['commitments']
    from promisekeeper.application.evaluation_qualification import QUALITY_FIELDS
    assert all(row[key] is None for key in QUALITY_FIELDS)
    assert [s['invocation_kind'] for s in row['progress'] if s['step_name']=='EXTRACTION']==['INITIAL','AUTO_RETRY']


def test_validated_empty_findings_are_empty_arrays_instead_of_unknown(tmp_path,monkeypatch):
    from promisekeeper.application.evaluations import evaluate,evaluation_manifest
    from promisekeeper.agents.nebius import NebiusInvestigator
    from promisekeeper.agents.scripted import ScriptedInvestigator
    from promisekeeper.config import load_settings
    from dataclasses import replace
    def fake(self,request,*,timeout):
        return replace(ScriptedInvestigator().extract(request,timeout=timeout),returned_model=self.model,response_id='offline-representative-response')
    monkeypatch.setattr(NebiusInvestigator,'extract',fake)
    report=evaluate(load_settings({'NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path),catalogue='release-0.1',repeats=1,output=tmp_path/'report.json',manifest=evaluation_manifest()[:1])
    assert report['status']=='PASS'
    assert report['runs'][0]['validated_uncertainty']==dict(contradictions=[],unresolved=[])
    row=report['runs'][0]
    assert row['model_policy_evidence']==dict(contradictions=[],unresolved=[])
    assert row['actual_findings']['unresolved_questions'][0]['field']=='ATTRIBUTION'
    assert row['expected_findings']['unresolved_questions']==[dict(field='ATTRIBUTION',sources=['PK-001-M1'])]
    from promisekeeper.application.evaluation_qualification import QUALITY_FIELDS
    assert all(row[key] is True for key in QUALITY_FIELDS)


def test_failing_fact_comparison_retains_exact_actual_and_expected_fields(tmp_path,monkeypatch):
    from promisekeeper.application.evaluations import evaluate,evaluation_manifest
    from promisekeeper.agents.nebius import NebiusInvestigator
    from promisekeeper.agents.scripted import ScriptedInvestigator
    from promisekeeper.config import load_settings
    def fake(self,request,*,timeout):
        response=ScriptedInvestigator().extract(request,timeout=timeout)
        response.output['commitments'][0]['date_text']=None
        return response
    monkeypatch.setattr(NebiusInvestigator,'extract',fake)
    entry=next(entry for entry in evaluation_manifest() if entry['id']=='FV-08-SOON')
    report=evaluate(load_settings({'NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path),catalogue='release-0.1',repeats=1,output=tmp_path/'report.json',manifest=[entry])
    row=report['runs'][0]
    assert report['status']=='FAIL' and row['extraction_correct'] is False
    actual=row['actual_candidate_facts']['commitments'][0]
    expected=row['expected_candidate_facts']['commitments'][0]
    assert actual['date_text'] is None and expected['date_text']=='soon'
    assert {k:v for k,v in actual.items() if k!='date_text'}=={k:v for k,v in expected.items() if k!='date_text'}
    assert actual['source_id']=='PK-002-M1' and actual['commitment_key']=='PK-002-M1-C1'
    assert report['evaluator_version']=='5'


def test_supported_by_deadline_keeps_literal_report_fields_and_passes_independent_checks(tmp_path,monkeypatch):
    from dataclasses import replace
    import json
    from promisekeeper.application.evaluations import evaluate,evaluation_manifest
    from promisekeeper.agents.nebius import NebiusInvestigator
    from promisekeeper.agents.scripted import ScriptedInvestigator
    from promisekeeper.config import load_settings
    def replay(self,request,*,timeout):
        response=ScriptedInvestigator().extract(request,timeout=timeout)
        response.output['commitments'][0]['date_text']='by 20 October 2026'
        return replace(response,returned_model=self.model,response_id='offline-by-deadline-replay')
    monkeypatch.setattr(NebiusInvestigator,'extract',replay)
    entry=next(e for e in evaluation_manifest() if e['id']=='FV-10-EVIDENCE')
    path=tmp_path/'report.json'
    report=evaluate(load_settings({'NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path),catalogue='release-0.1',repeats=1,output=path,manifest=[entry])
    row=report['runs'][0]
    assert row['actual_candidate_facts']['commitments'][0]['date_text']=='by 20 October 2026'
    assert row['expected_candidate_facts']['commitments'][0]['date_text']=='20 October 2026'
    assert row['returned_outputs'][0]['candidate_facts']==row['actual_candidate_facts']
    assert json.loads(path.read_text(encoding='utf-8'))==report
    assert row['extraction_correct'] is True
    assert row['status']=='PASS' and row['action']=='FOLLOW_UP'
    assert report['temporal_policy_version']=='deadline-by-1'
    assert report['evaluator_version']=='5' and report['criteria_version']=='gate-iii-live-4'

def test_attribution_uncertainty_accepts_unlinked_and_rejects_fulfilled_linked():
    from uuid import uuid4
    from promisekeeper.application.evaluations import _uncertainty_correct
    from promisekeeper.fixtures.catalogue import fresh_copy
    from promisekeeper.contracts.investigations import InvestigatorOutput
    for variant,expected in [('FV-16-UNLINKED',True),('FV-16-LINKED',False)]:
        fixture=fresh_copy(variant);oracle=fixture.cases['PK-002'];c=oracle.extraction.commitments[0]
        span=dict(evidence_version_id=str(c.source.id),source_id=c.source.source_id,start=c.start,end=c.end,quote=c.quote)
        output=InvestigatorOutput.model_validate(dict(schema_version='1',snapshot_id=str(uuid4()),commitments=[],payment_claims=[],contradictions=[],unresolved=[dict(field='ATTRIBUTION',sources=[span])]))
        assert _uncertainty_correct(output,oracle,fixture.evaluation_at) is expected
