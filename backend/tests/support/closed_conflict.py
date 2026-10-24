"""Test-only approved event injection; never loaded by production startup."""
from copy import deepcopy

CLOSED_CONFLICT_EVENT = dict(
    id='TEST-PK-003-CONFLICT', case_id='PK-003', kind='EVIDENCE',
    evaluation_at='2026-10-23T12:00:00+05:30',
    append=[dict(source_id='PK-003-TEST-I2', kind='INVOICE',
        original_content='Fictional conflicting invoice CR-312; client Cedar Retail Labs; INR 160,000.00; due 10 October 2026.',
        data=dict(invoice_id='CR-312', client='Cedar Retail Labs', amount_text='160,000.00', currency_text='INR', due_text='10 October 2026'),
        event_at='2026-10-23T11:30:00+05:30', arrived_at='2026-10-23T12:00:00+05:30',
        availability='AVAILABLE', authoritative=True, version=1)],
    expected=dict(action='VERIFY_PAYMENT', balance_minor=None, review_at=None))


def install_closed_conflict_event(monkeypatch=None):
    from promisekeeper.fixtures import catalogue
    from promisekeeper.application import scenario_updates
    original = catalogue._event_table
    def table(variant):
        return original(variant) | {CLOSED_CONFLICT_EVENT['id']: deepcopy(CLOSED_CONFLICT_EVENT)}
    for module in (catalogue, scenario_updates):
        if monkeypatch is None:
            module._event_table = table
        else:
            monkeypatch.setattr(module, '_event_table', table)
