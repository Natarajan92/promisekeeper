CREATE TABLE client_memory_scoped (
    id TEXT PRIMARY KEY,
    demonstration_id TEXT REFERENCES demonstrations(id),
    client TEXT NOT NULL,
    fact TEXT NOT NULL CHECK(length(fact) BETWEEN 1 AND 300),
    at TEXT NOT NULL,
    UNIQUE(demonstration_id, client, fact)
);
INSERT INTO client_memory_scoped (id, demonstration_id, client, fact, at)
    SELECT id, demonstration_id, client, fact, at FROM client_memory;
DROP TABLE client_memory;
ALTER TABLE client_memory_scoped RENAME TO client_memory;
CREATE INDEX client_memory_scope ON client_memory(demonstration_id, client, at);
