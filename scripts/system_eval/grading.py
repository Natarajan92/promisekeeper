"""Literal independent oracles. Never import product derivation code here."""
from collections import Counter


def grade(case, actual):
    expected = case['expected']
    checks = {}
    if actual.get('error'):
        return {'executed': False}, 'ERROR'
    for key, value in expected.items():
        checks[key] = key in actual and type(actual[key]) is type(value) and actual[key] == value
    # In every evaluated message/money scenario the owner has neither approved
    # a message nor closed the invoice. Absence is not a passing observation.
    for key in ('lifecycle', 'review_count'):
        if case['kind'] in {'message', 'allocation'}:
            checks[key] = actual.get(key) == ('OPEN' if key == 'lifecycle' else 0)
    if case['kind'] in {'message','allocation'}:
        checks['review_state']=actual.get('review_state') in {'NONE','UNAPPROVED'}
        checks['currency']=actual.get('currency')=='INR'
    if 'safe_actions' in case:
        checks['safe_action'] = (actual.get('accepted') is False or
                                 actual.get('action') in case['safe_actions'])
    return checks, 'PASS' if checks and all(checks.values()) else 'FAIL'


def summarize(rows):
    counts = Counter(row['verdict'] for row in rows)
    return {name: counts[name] for name in ('PASS', 'FAIL', 'ERROR', 'UNEXECUTED')}
