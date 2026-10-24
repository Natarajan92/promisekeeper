"""Per-client payment memory for the Communicator's tone.

Facts are written only from deterministic investigation results ("missed a promise", "kept a
promise", "unverified payment claim") and are read only into the personal-note context. Memory
never feeds money, the recommendation or eligibility. LocalMemory (SQLite) is the default;
Mem0Memory uses the hosted mem0 platform when the owner configures MEM0_API_KEY in LIVE mode.
"""
from datetime import datetime, timedelta
from uuid import uuid4

import httpx

from promisekeeper.application.draft_templates import _amount
from promisekeeper.application.operations import instant, utcnow
from promisekeeper.domain.dates import IST

MEM0_URL = 'https://api.mem0.ai'
RECALL_LIMIT = 3


def _deadline_day(expires_at):
    # A promise "by 20 October" expires at the next midnight IST; name the promised day.
    return (datetime.fromisoformat(expires_at).astimezone(IST) - timedelta(seconds=1)).strftime('%d %b %Y')


def facts_from_result(result):
    evaluated = datetime.fromisoformat(result['evaluation_at'])
    facts = []
    for commitment in result['commitments']:
        if commitment.get('superseded'):
            continue
        amount = _amount(commitment['amount']) if commitment.get('amount') else 'an unstated amount'
        due = _deadline_day(commitment['expires_at']) if commitment.get('expires_at') else None
        if commitment.get('fulfilled'):
            facts.append(f'Kept a promise to pay {amount}' + (f' by {due}.' if due else '.'))
        elif due and datetime.fromisoformat(commitment['expires_at']) <= evaluated:
            facts.append(f'Missed a promise to pay {amount} by {due}.')
    if any(not claim['resolved'] for claim in result['claims']):
        facts.append('Said a payment was made that is not yet verified.')
    return facts


def _user(client, scope):
    # Memories are scoped per demonstration copy so a fresh copy never inherits another copy's history.
    return f'client:{scope}:{client}' if scope else f'client:{client}'


class LocalMemory:
    def __init__(self, db):
        self.db = db

    def remember(self, client, fact, *, scope=None):
        with self.db.transaction() as con:
            con.execute('INSERT OR IGNORE INTO client_memory (id,demonstration_id,client,fact,at) VALUES (?,?,?,?,?)',
                        (str(uuid4()), scope, client, fact, instant(utcnow())))

    def recall(self, client, *, scope=None):
        with self.db.connection() as con:
            if scope is None:
                rows = con.execute('SELECT fact FROM client_memory WHERE client=? ORDER BY at DESC, rowid DESC LIMIT ?',
                                   (client, RECALL_LIMIT)).fetchall()
            else:
                rows = con.execute('SELECT fact FROM client_memory WHERE demonstration_id=? AND client=? ORDER BY at DESC, rowid DESC LIMIT ?',
                                   (scope, client, RECALL_LIMIT)).fetchall()
        return ' '.join(row['fact'] for row in reversed(rows)) or None


class Mem0Memory:
    """Hosted mem0 adapter. Verified offline against a mocked transport only."""
    model = 'mem0'

    def __init__(self, api_key, *, client=None):
        self.headers = {'Authorization': f'Token {api_key}'}
        self.client = client or httpx.Client(timeout=10)

    def remember(self, client, fact, *, scope=None):
        response = self.client.post(f'{MEM0_URL}/v1/memories/', headers=self.headers, json={
            'messages': [{'role': 'user', 'content': fact}], 'user_id': _user(client, scope), 'infer': False,
            'metadata': {'source': 'promisekeeper'}})
        response.raise_for_status()

    def recall(self, client, *, scope=None):
        response = self.client.get(f'{MEM0_URL}/v1/memories/', headers=self.headers, params={'user_id': _user(client, scope)})
        response.raise_for_status()
        payload = response.json()
        items = payload.get('results', []) if isinstance(payload, dict) else payload
        facts = [item['memory'] for item in items if isinstance(item, dict) and item.get('memory')]
        return ' '.join(facts[:RECALL_LIMIT]) or None
