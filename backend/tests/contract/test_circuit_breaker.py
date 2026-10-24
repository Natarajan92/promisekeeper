"""Per-model circuit breaker: provider outages fail fast instead of burning the case deadline."""
from types import SimpleNamespace
import httpx
import pytest
from openai import APIConnectionError
from pydantic import BaseModel, ConfigDict
from promisekeeper.agents.llm_client import CircuitBreaker, chat_structured
from promisekeeper.agents.protocol import InvestigatorFailure


class Out(BaseModel):
    model_config = ConfigDict(extra='forbid')
    note: str


class Clock:
    now = 1000.0

    def __call__(self):
        return self.now


def client(outcomes):
    calls = []

    class Completions:
        def create(self, **kw):
            calls.append(kw)
            outcome = outcomes[min(len(calls) - 1, len(outcomes) - 1)]
            if outcome == 'down':
                raise APIConnectionError(request=httpx.Request('POST', 'https://provider.test/v1/chat/completions'))
            return SimpleNamespace(id='r', model=kw['model'], usage=None,
                                   choices=[SimpleNamespace(message=SimpleNamespace(content=outcome, refusal=None), finish_reason='stop')])
    return SimpleNamespace(chat=SimpleNamespace(completions=Completions())), calls


def call(fake, breaker, model='m'):
    return chat_structured(fake, model=model, system='s', user={}, schema_model=Out, timeout=5, breaker=breaker)


def test_circuit_opens_after_three_transient_failures_and_fails_fast():
    clock, fake_calls = Clock(), None
    breaker = CircuitBreaker(threshold=3, cooldown=60, clock=clock)
    fake, fake_calls = client(['down'])
    for _ in range(3):
        with pytest.raises(InvestigatorFailure) as raised:
            call(fake, breaker)
        assert raised.value.code == 'AGENT_UNAVAILABLE'
    with pytest.raises(InvestigatorFailure) as raised:
        call(fake, breaker)
    assert raised.value.code == 'PROVIDER_CIRCUIT_OPEN' and raised.value.transient is False
    assert len(fake_calls) == 3


def test_circuit_half_opens_after_cooldown_and_closes_on_success():
    clock = Clock()
    breaker = CircuitBreaker(threshold=3, cooldown=60, clock=clock)
    fake, calls = client(['down', 'down', 'down', '{"note":"ok"}'])
    for _ in range(3):
        with pytest.raises(InvestigatorFailure):
            call(fake, breaker)
    clock.now += 61
    assert call(fake, breaker).value == {'note': 'ok'}
    assert breaker.state('m') == 'CLOSED'


def test_invalid_output_does_not_open_the_circuit():
    breaker = CircuitBreaker(threshold=3, cooldown=60, clock=Clock())
    fake, calls = client(['not json'])
    for _ in range(4):
        with pytest.raises(InvestigatorFailure) as raised:
            call(fake, breaker)
        assert raised.value.code == 'AGENT_INVALID_OUTPUT'
    assert len(calls) == 4 and breaker.state('m') == 'CLOSED'


def test_circuits_are_independent_per_model():
    breaker = CircuitBreaker(threshold=3, cooldown=60, clock=Clock())
    down, _ = client(['down'])
    for _ in range(3):
        with pytest.raises(InvestigatorFailure):
            call(down, breaker, model='nebius-model')
    healthy, _ = client(['{"note":"ok"}'])
    assert call(healthy, breaker, model='fireworks-model').value == {'note': 'ok'}
    assert breaker.state('nebius-model') == 'OPEN'
