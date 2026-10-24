"""Owner feedback and draft edits: the human signal used to improve the agents.

Everything is saved locally first. Sending a rating to the LangSmith run of that investigation
is best-effort and only happens when tracing is configured; it never blocks the owner.
"""
import logging
import os
from uuid import uuid4

from promisekeeper.application.operations import CommandError, instant, utcnow

_log = logging.getLogger(__name__)
_COLUMNS = 'id,case_id,investigation_id,target,rating,comment,operation_id,created_at,langsmith_sent'


def langsmith_client():
    from langsmith import Client
    return Client()


def _view(row):
    return dict(id=row['id'], case_id=row['case_id'], investigation_id=row['investigation_id'], target=row['target'],
                rating=row['rating'], comment=row['comment'], created_at=row['created_at'])


def send_langsmith_feedback(investigation_id, target, rating, comment):
    if os.environ.get('LANGSMITH_TRACING') != 'true' or not os.environ.get('LANGSMITH_API_KEY'):
        return False
    from promisekeeper.orchestration.case_graph import run_id_for
    try:
        langsmith_client().create_feedback(run_id_for(investigation_id), f'owner_{target.lower()}_rating',
                                           score=1 if rating == 'UP' else 0, comment=comment)
        return True
    except Exception:
        _log.warning('LangSmith feedback was not sent; it remains saved locally.')
        return False


def record_feedback(db, did, cid, request):
    with db.transaction() as con:
        saved = con.execute(f'SELECT {_COLUMNS} FROM owner_feedback WHERE operation_id=?', (request['operation_id'],)).fetchone()
        if saved is not None:
            return dict(schema_version='1', feedback=_view(saved), sent_to_langsmith=bool(saved['langsmith_sent']))
        owned = con.execute('SELECT 1 FROM investigations WHERE id=? AND demonstration_id=? AND case_id=?',
                            (request['investigation_id'], did, cid)).fetchone()
        if owned is None:
            raise CommandError('NOT_FOUND', 404)
        fid = str(uuid4())
        con.execute('INSERT INTO owner_feedback (id,demonstration_id,case_id,investigation_id,target,rating,comment,operation_id,created_at) '
                    'VALUES (?,?,?,?,?,?,?,?,?)', (fid, did, cid, request['investigation_id'], request['target'], request['rating'],
                                                   request.get('comment'), request['operation_id'], instant(utcnow())))
        row = con.execute(f'SELECT {_COLUMNS} FROM owner_feedback WHERE id=?', (fid,)).fetchone()
    sent = send_langsmith_feedback(request['investigation_id'], request['target'], request['rating'], request.get('comment'))
    if sent:
        with db.transaction() as con:
            con.execute('UPDATE owner_feedback SET langsmith_sent=1 WHERE id=?', (fid,))
    return dict(schema_version='1', feedback=_view(row), sent_to_langsmith=sent)


def record_edit_diff(con, draft):
    """Pair the agent-written first version with the exact text the owner approved."""
    first = con.execute('SELECT exact_text FROM draft_versions WHERE investigation_id=? ORDER BY version LIMIT 1',
                        (draft['investigation_id'],)).fetchone()
    if first is None:
        return
    con.execute('INSERT INTO draft_edit_feedback (id,demonstration_id,case_id,investigation_id,draft_version_id,agent_text,approved_text,changed,created_at) '
                'VALUES (?,?,?,?,?,?,?,?,?)', (str(uuid4()), draft['demonstration_id'], draft['case_id'], draft['investigation_id'], draft['id'],
                                               first[0], draft['exact_text'], int(first[0] != draft['exact_text']), instant(utcnow())))
