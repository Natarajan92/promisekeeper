CREATE TABLE client_memory (
    id TEXT PRIMARY KEY,
    demonstration_id TEXT REFERENCES demonstrations(id),
    client TEXT NOT NULL,
    fact TEXT NOT NULL CHECK(length(fact) BETWEEN 1 AND 300),
    at TEXT NOT NULL,
    UNIQUE(client, fact)
);
CREATE INDEX client_memory_client ON client_memory(client, at);
