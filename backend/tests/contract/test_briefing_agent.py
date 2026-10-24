"""The Briefing agent may summarise but never introduce numbers absent from the case facts."""
from types import SimpleNamespace
from promisekeeper.agents.briefing import NebiusBriefing, ScriptedBriefing, briefing_numbers_supported, deterministic_briefing
from promisekeeper.config import load_settings

FACTS = [
    dict(client='Northstar Analytics', invoice_id='NS-104', action='FOLLOW_UP', balance_text='INR 80,000.00', review_at_text=None,
         draft_ready=True, outcome='INVESTIGATED'),
    dict(client='Meridian Studio', invoice_id='MS-221', action='WAIT', balance_text='INR 50,000.00', review_at_text='26 Oct 2026, 00:00 IST',
         draft_ready=False, outcome='INVESTIGATED'),
    dict(client='Cedar Works', invoice_id='CW-310', action='VERIFY_PAYMENT', balance_text=None, review_at_text=None,
         draft_ready=True, outcome='SKIPPED'),
]


def test_briefing_rejects_invented_numbers():
    assert briefing_numbers_supported('INR 1,20,000 is overdue for Northstar.', FACTS) is False
    assert briefing_numbers_supported('Northstar owes INR 80,000.00 on NS-104; review Meridian on 26 Oct 2026.', FACTS) is True
    assert briefing_numbers_supported('Northstar owes INR 80,000 now.', FACTS) is True


def test_deterministic_briefing_mentions_every_case_and_only_supported_numbers():
    text = deterministic_briefing(FACTS)
    for fact in FACTS:
        assert fact['client'] in text and fact['invoice_id'] in text
    assert briefing_numbers_supported(text, FACTS)


def test_scripted_briefing_uses_deterministic_text():
    assert ScriptedBriefing().summarize(FACTS, timeout=1).value == {'briefing': deterministic_briefing(FACTS)}


def test_nebius_briefing_parses_strict_output(tmp_path):
    calls = []

    class Completions:
        def create(self, **kw):
            calls.append(kw)
            return SimpleNamespace(id='r', model=kw['model'], usage=SimpleNamespace(prompt_tokens=30, completion_tokens=12),
                                   choices=[SimpleNamespace(message=SimpleNamespace(content='{"briefing":"All good."}', refusal=None), finish_reason='stop')])
    settings = load_settings({'PK_AGENT_MODE': 'LIVE', 'NEBIUS_API_KEY': 'k'}, workspace=tmp_path)
    call = NebiusBriefing(settings, client=SimpleNamespace(chat=SimpleNamespace(completions=Completions()))).summarize(FACTS, timeout=5)
    assert call.value == {'briefing': 'All good.'} and calls[0]['response_format']['json_schema']['strict'] is True
