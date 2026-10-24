"""Independent lexical comparison must not inherit production date decisions."""
from copy import deepcopy
import pytest


def facts(raw):
    return dict(commitments=[dict(source_id='M1',commitment_key='M1-C1',speaker='Customer',
        amount_text='80,000',currency_text='INR',date_text=raw,explicitly_replaces_source_id=None)],payment_claims=[])


def packet(original='2026-10-21T23:30:00-04:00'):
    return dict(evidence=[dict(stable_source_id='M1',original_event_at=original,
        event_at='2026-10-22T03:30:00+00:00')])


@pytest.mark.parametrize('raw', ['20 October 2026','2026-10-20','2026-10-20T17:00:00+02:00','today','tomorrow'])
@pytest.mark.parametrize('reverse', [False,True])
def test_known_literal_remainder_equivalence_is_independent_of_production_dates(raw,reverse,monkeypatch):
    from promisekeeper.application.evaluations import candidate_facts_equal
    from promisekeeper.domain import dates
    def forbidden(*args,**kwargs):raise AssertionError('comparison must be independent')
    monkeypatch.setattr(dates,'deadline',forbidden)
    monkeypatch.setattr(dates,'_calendar_day',forbidden)
    actual,expected=facts('by '+raw),facts(raw)
    before=deepcopy((actual,expected))
    assert candidate_facts_equal(*( (expected,actual) if reverse else (actual,expected)),packet())
    assert (actual,expected)==before


@pytest.mark.parametrize('actual,expected,original', [
    ('by 21 October 2026','20 October 2026',None),
    ('by 2026-10-20','20 October 2026',None),
    ('by 20 october 2026','20 October 2026',None),
    ('by soon','soon',None),('by someday','soon',None),('by 31 February 2026','31 February 2026',None),
    ('by 20 October','20 October',None),('by tomorrow','tomorrow',None),
    ('by today','today','2026-10-21T23:30:00'),
    ('by tomorrow','tomorrow','9999-12-31T12:00:00+00:00'),
    ('by 9999-12-31','9999-12-31',None),
    ('by 2026-10-20T17:00:00','2026-10-20T17:00:00',None),
    ('not by 20 October 2026','20 October 2026',None),
    ('by about 20 October 2026','about 20 October 2026',None),
    ('by 20 October 2026 extra','20 October 2026 extra',None),
    ('by by 20 October 2026','by 20 October 2026',None),
    ('before 20 October 2026','20 October 2026',None),
    ('by20 October 2026','20 October 2026',None),
    (None,'20 October 2026',None),
])
def test_wrong_unknown_negated_approximate_or_unanchored_dates_remain_raw_sensitive(actual,expected,original):
    from promisekeeper.application.evaluations import candidate_facts_equal
    assert not candidate_facts_equal(facts(actual),facts(expected),packet(original))


@pytest.mark.parametrize('field,value', [('speaker','Other'),('amount_text','80000'),('currency_text',None),
    ('commitment_key','other'),('source_id','M2'),('explicitly_replaces_source_id','old')])
def test_connector_equivalence_cannot_hide_changes_to_other_candidate_fields(field,value):
    from promisekeeper.application.evaluations import candidate_facts_equal
    actual,expected=facts('by 20 October 2026'),facts('20 October 2026')
    actual['commitments'][0][field]=value
    assert not candidate_facts_equal(actual,expected,packet())


def test_payment_day_connector_remains_strict_even_when_commitment_equivalence_is_valid():
    from promisekeeper.application.evaluations import candidate_facts_equal
    actual,expected=facts('by 20 October 2026'),facts('20 October 2026')
    expected['payment_claims']=[dict(source_id='M2',speaker='Customer',amount_text='80,000',currency_text='INR',
        payment_date_text='20 October 2026',transaction_reference_text='TX1')]
    actual['payment_claims']=deepcopy(expected['payment_claims'])
    actual['payment_claims'][0]['payment_date_text']='by 20 October 2026'
    assert not candidate_facts_equal(actual,expected,packet())


def test_identical_unknown_fields_still_compare_literally_without_general_normalization():
    from promisekeeper.application.evaluations import candidate_facts_equal
    assert candidate_facts_equal(facts('soon'),facts('soon'),packet(None))
    assert not candidate_facts_equal(facts('soon'),facts('someday'),packet(None))
