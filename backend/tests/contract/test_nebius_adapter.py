import json
from types import SimpleNamespace
import pytest
from promisekeeper.config import load_settings

def test_selected_nebius_configuration_loads_repo_env_without_exposing_key(tmp_path):
    (tmp_path/'.env').write_text('NEBIUS_API_KEY=fictional-test-key\nPK_AGENT_MODE=LIVE\nPK_NEBIUS_MODEL=Qwen/Qwen3-235B-A22B-Instruct-2507\n',encoding='utf-8')
    settings=load_settings({},workspace=tmp_path)
    assert settings.agent_mode=='LIVE'
    assert settings.provider=='NEBIUS'
    assert settings.model=='Qwen/Qwen3-235B-A22B-Instruct-2507'
    assert settings.capability_available
    assert 'fictional-test-key' not in repr(settings)
    assert 'fictional-test-key' not in json.dumps(settings.safe_summary())
    override=load_settings({'PK_AGENT_MODE':'STUB','NEBIUS_API_KEY':'process-key'},workspace=tmp_path)
    assert override.agent_mode=='STUB' and override.api_key=='process-key'

def test_adapter_uses_structured_output_exact_model_and_no_tools_or_repair(tmp_path):
    from promisekeeper.agents.nebius import NebiusInvestigator
    settings=load_settings({'PK_AGENT_MODE':'LIVE','NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path)
    calls=[]
    class Completions:
        def create(self,**kw):
            calls.append(kw)
            return SimpleNamespace(id='response-1',model=settings.model,usage=SimpleNamespace(model_dump=lambda:{'prompt_tokens':12,'completion_tokens':4,'total_tokens':16}),choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(dict(schema_version='1',snapshot_id='snapshot',commitments=[],payment_claims=[],contradictions=[],unresolved=[])),refusal=None),finish_reason='stop')])
    fake=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    source=dict(id='source',stable_source_id='message-source',kind='MESSAGE',availability='AVAILABLE',original_content='😀 Pay INR 10 tomorrow.',commitment_anchors=[])
    response=NebiusInvestigator(settings,client=fake).extract(dict(snapshot_id='snapshot',packet={'evidence':[source]}),timeout=10)
    assert calls[0]['model']==settings.model
    assert calls[0]['timeout']==10
    assert calls[0]['response_format']['type']=='json_schema'
    assert calls[0]['response_format']['json_schema']['schema']['additionalProperties'] is False
    assert 'tools' not in calls[0]
    assert response.returned_model==settings.model and response.response_id=='response-1'
    assert response.usage['total_tokens']==16
    sent=json.loads(calls[0]['messages'][1]['content'])
    assert sent['packet']['evidence'][0]['exact_quote_options']==[dict(evidence_version_id='source',source_id='message-source',start=0,end=22,quote='😀 Pay INR 10 tomorrow.')]
    assert calls[0]['response_format']['json_schema']['schema']['$defs']['Span']['enum']==sent['packet']['evidence'][0]['exact_quote_options']
    assert 'exact_quote_options' not in source

@pytest.mark.parametrize('status,transient',[(529,True),(500,True),(503,True),(400,False),(401,False),(402,False),(404,False),(422,False),(408,True),(429,True)])
def test_provider_status_classification_retries_only_transient_failures(tmp_path,status,transient):
    import httpx
    from openai import APIStatusError
    from promisekeeper.agents.nebius import NebiusInvestigator
    from promisekeeper.agents.protocol import InvestigatorFailure
    settings=load_settings({'NEBIUS_API_KEY':'fictional-test-key'},workspace=tmp_path)
    class Completions:
        def create(self,**kwargs):
            response=httpx.Response(status,request=httpx.Request('POST','https://api.tokenfactory.nebius.com/v1/chat/completions'))
            raise APIStatusError('fictional status response',response=response,body=None)
    client=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))
    with pytest.raises(InvestigatorFailure) as caught:
        NebiusInvestigator(settings,client=client).extract(dict(snapshot_id='snapshot',packet={'evidence':[]}),timeout=20)
    assert caught.value.code=='PROVIDER_REJECTED_REQUEST'
    assert caught.value.transient is transient

@pytest.mark.parametrize('model,effort',[('zai-org/GLM-5.3-Flash','low'),('Qwen/Qwen3-235B-A22B-Instruct-2507',None),('zai-org/GLM-5.3',None)])
def test_reasoning_effort_is_explicit_only_for_qualified_glm_candidate(tmp_path,model,effort):
    from promisekeeper.agents.nebius import NebiusInvestigator
    settings=load_settings({'NEBIUS_API_KEY':'fictional-test-key','PK_NEBIUS_MODEL':model},workspace=tmp_path)
    calls=[]
    class Completions:
        def create(self,**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(id='test-response',model=model,usage=None,choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{}',refusal=None))])
    NebiusInvestigator(settings,client=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))).extract(dict(snapshot_id='snapshot',packet={'evidence':[]}),timeout=20)
    if effort is None:assert 'reasoning_effort' not in calls[0]
    else:assert calls[0]['reasoning_effort']==effort


def test_uncertainty_categories_have_explicit_source_relationships_in_prompt_and_contract():
    from promisekeeper.agents.nebius import DEFINITIONS,ADAPTER_VERSION
    from promisekeeper.agents.protocol import PROMPT_VERSION
    from promisekeeper.contracts.investigations import CandidateOnlyOutput, InvestigatorOutput
    schema=CandidateOnlyOutput.model_json_schema()
    assert InvestigatorOutput.model_json_schema()['properties']['contradictions']['maxItems']==32
    from promisekeeper.agents.protocol import EXTRACTION_POLICY_VERSION
    assert PROMPT_VERSION=='candidate-extraction-7'
    assert ADAPTER_VERSION=='nebius-chat-json-schema-9'
    assert EXTRACTION_POLICY_VERSION=='candidate-only-1'
    assert 'Both findings arrays must be empty' in DEFINITIONS
    for field in ('contradictions','unresolved'):
        assert schema['properties'][field]['maxItems']==0
    assert 'missing, invalid or disputed' in schema['$defs']['Unresolved']['properties']['field']['description']
    assert 'vague' in schema['$defs']['Commitment']['properties']['date_text']['description']
    assert 'vague' in schema['$defs']['Claim']['properties']['payment_date_text']['description']
    assert 'invalid' in schema['$defs']['Claim']['properties']['amount_text']['description']
    assert 'invoice allocation' in schema['$defs']['Unresolved']['properties']['field']['description']
    assert 'reversal' in schema['$defs']['Contradiction']['properties']['kind']['description']
