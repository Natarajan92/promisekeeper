"""Shared strict-schema chat call for the drafting and briefing agents.

Every agent call is bounded (no SDK retries, explicit timeout), schema-constrained and
validated before use. Failures are classified so the graph can retry once or fall back.
"""
from dataclasses import dataclass
import json
import os
import time

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI
from pydantic import ValidationError

from promisekeeper.agents.protocol import InvestigatorFailure

NEBIUS_BASE_URL = 'https://api.tokenfactory.nebius.com/v1/'
FIREWORKS_BASE_URL = 'https://api.fireworks.ai/inference/v1'


@dataclass(frozen=True)
class AgentCall:
    value: dict
    model: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


def make_client(base_url, api_key):
    client = OpenAI(api_key=api_key, base_url=base_url, max_retries=0, timeout=20)
    if os.environ.get('LANGSMITH_TRACING') == 'true':
        from langsmith.wrappers import wrap_openai
        client = wrap_openai(client)
    return client


def model_parameters(model):
    """GLM Flash answers within the bounded budget only at low reasoning effort (see ADR-006)."""
    return {'reasoning_effort': 'low'} if model == 'zai-org/GLM-5.3-Flash' else {}


def chat_structured(client, *, model, system, user, schema_model, timeout, max_tokens=800):
    started = time.monotonic()
    try:
        completion = client.chat.completions.create(
            model=model, temperature=0.3, max_tokens=max_tokens, timeout=timeout, **model_parameters(model),
            response_format={'type': 'json_schema', 'json_schema': {
                'name': schema_model.__name__.lower(), 'schema': schema_model.model_json_schema(), 'strict': True}},
            messages=[{'role': 'system', 'content': system},
                      {'role': 'user', 'content': json.dumps(user, ensure_ascii=False)}])
    except (APIConnectionError, APITimeoutError) as exc:
        raise InvestigatorFailure('AGENT_UNAVAILABLE', transient=True) from exc
    except APIStatusError as exc:
        transient = exc.status_code in {408, 429} or 500 <= exc.status_code <= 599
        raise InvestigatorFailure('AGENT_UNAVAILABLE' if transient else 'AGENT_REQUEST_REJECTED', transient=transient) from exc
    latency_ms = int((time.monotonic() - started) * 1000)
    if not getattr(completion, 'choices', None):
        raise InvestigatorFailure('AGENT_INVALID_OUTPUT')
    message = completion.choices[0].message
    if getattr(message, 'refusal', None) or not message.content:
        raise InvestigatorFailure('AGENT_INVALID_OUTPUT')
    try:
        value = schema_model.model_validate_json(message.content).model_dump()
    except ValidationError as exc:
        raise InvestigatorFailure('AGENT_INVALID_OUTPUT') from exc
    usage = getattr(completion, 'usage', None)
    return AgentCall(value, getattr(completion, 'model', None) or model, getattr(usage, 'prompt_tokens', None),
                     getattr(usage, 'completion_tokens', None), latency_ms)


def scripted_call(value):
    return AgentCall(value, 'scripted', None, None, 0)
