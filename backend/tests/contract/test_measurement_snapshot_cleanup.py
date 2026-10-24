"""Measurement snapshots must release SQLite handles before directory cleanup."""
import sqlite3

import pytest


@pytest.mark.parametrize('complete_schema', [True, False])
def test_snapshot_closes_real_connection_on_success_and_query_failure(tmp_path, monkeypatch, complete_schema):
    from promisekeeper.application import measurements as runner

    database = tmp_path / 'measurement.sqlite'
    connection = sqlite3.connect(database)
    try:
        for table in runner.TABLES if complete_schema else runner.TABLES[:1]:
            connection.execute(f'CREATE TABLE {table} (id TEXT)')
        connection.commit()
    finally:
        connection.close()

    connect = sqlite3.connect
    opened = []

    def retain_connection(*args, **kwargs):
        connection = connect(*args, **kwargs)
        opened.append(connection)
        return connection

    monkeypatch.setattr(runner.sqlite3, 'connect', retain_connection)
    try:
        if complete_schema:
            assert runner._snapshot(database) == {table: [] for table in runner.TABLES}
        else:
            with pytest.raises(sqlite3.OperationalError, match='no such table'):
                runner._snapshot(database)
        assert len(opened) == 1
        with pytest.raises(sqlite3.ProgrammingError, match='closed database'):
            opened[0].execute('SELECT 1')
        # Windows rejects this unlink if a reader is still open. Keeping the
        # connection reference above rules out garbage collection as cleanup.
        database.unlink()
        assert not database.exists()
    finally:
        for connection in opened:
            connection.close()
