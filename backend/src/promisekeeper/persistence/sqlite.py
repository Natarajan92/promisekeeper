"""Owned SQLite lifecycle; short connections and explicit commit/rollback only."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3

from promisekeeper.orchestration.capacity import PROCESS_CAPACITY
from promisekeeper.persistence.ownership import Ownership


class Database:
    def __init__(self, path):
        self.path = Path(path).resolve()
        self.ownership = Ownership(self.path.with_suffix(self.path.suffix + ".lock"))
        self.capacity = PROCESS_CAPACITY
        self.reservations = set()
        self.ready = False

    def __enter__(self):
        self.ownership.acquire()
        try:
            self._migrate()
            from promisekeeper.persistence.recovery import recover
            recover(self)
            self.ready = True
        except BaseException:
            self.close()
            raise
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self.ready = False
        for owner in tuple(self.reservations):
            self.capacity.release(owner)
        self.reservations.clear()
        saver = getattr(self, "graph_checkpointer", None)
        if saver is not None:
            self.graph_checkpointer = None
            saver.conn.close()
        self.ownership.release()

    @contextmanager
    def connection(self):
        if self.ownership.file is None:
            raise RuntimeError("Database ownership required")
        con = sqlite3.connect(self.path, isolation_level=None, timeout=0.25)
        con.row_factory = sqlite3.Row
        try:
            con.execute("PRAGMA foreign_keys=ON")
            con.execute("PRAGMA journal_mode=DELETE")
            con.execute("PRAGMA synchronous=EXTRA")
            con.execute("PRAGMA busy_timeout=250")
            yield con
        finally:
            con.close()

    def commit(self, con):
        con.commit()

    @contextmanager
    def transaction(self):
        with self.connection() as con:
            con.execute("BEGIN IMMEDIATE")
            try:
                yield con
                self.commit(con)
            except BaseException:
                con.rollback()
                raise

    def _migrate(self):
        with self.connection() as con:
            con.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY)")
            for path in sorted(Path(__file__).with_name("migrations").glob("*.sql")):
                if con.execute("SELECT 1 FROM schema_migrations WHERE version=?", (path.name,)).fetchone():
                    continue
                script = path.read_text(encoding="utf-8")
                # Names come exclusively from packaged migrations, never request data.
                con.executescript("BEGIN IMMEDIATE;\n" + script +
                                  f"\nINSERT INTO schema_migrations VALUES ('{path.name}');\nCOMMIT;")
            immutable = ("evidence_versions", "invoice_projections", "payment_projections", "commitment_anchors",
                         "commitment_attributions", "evidence_snapshots", "investigation_results", "draft_versions",
                         "draft_reviews", "owner_dispositions", "case_events", "operation_receipts",
                         "intake_batches", "intake_customers", "intake_invoices", "intake_payments",
                         "intake_allocations", "intake_documents", "intake_ledger_reviews")
            for table in immutable:
                con.executescript(f"""
                    CREATE TRIGGER IF NOT EXISTS immutable_{table}_update BEFORE UPDATE ON {table}
                    BEGIN SELECT RAISE(ABORT,'Immutable history'); END;
                    CREATE TRIGGER IF NOT EXISTS immutable_{table}_delete BEFORE DELETE ON {table}
                    WHEN EXISTS(SELECT 1 FROM demonstrations WHERE id=OLD.demonstration_id AND deleted=0)
                    BEGIN SELECT RAISE(ABORT,'Immutable history'); END;
                """)
