"""Sequence cursors retain immutable events and direct historical object access."""
from promisekeeper.application.operations import CommandError
from promisekeeper.application.reviews import draft_view
from promisekeeper.persistence.repositories import demonstration, history


def get_history(db, did, cid, cursor=0, limit=50):
    return history(db, did, cid, cursor, limit)


def get_historical_draft(db, did, vid):
    with db.connection() as con:
        con.execute('BEGIN')
        demonstration(con, did)
        row = con.execute('SELECT * FROM draft_versions WHERE demonstration_id=? AND id=?', (did, vid)).fetchone()
        if row is None:
            raise CommandError('NOT_FOUND', 404)
        return dict(schema_version='1', draft_version=draft_view(con, row))
