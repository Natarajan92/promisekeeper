CREATE TABLE agent_activity (
    id TEXT PRIMARY KEY,
    demonstration_id TEXT NOT NULL REFERENCES demonstrations(id),
    case_id TEXT REFERENCES cases(id) ON DELETE CASCADE,
    investigation_id TEXT, morning_review_id TEXT,
    agent TEXT NOT NULL CHECK(agent IN ('INTAKE','EXTRACTOR','RULES_ENGINE','MEMORY','COMMUNICATOR','SAFETY_CHECK','TONE_REVIEWER','OWNER','SUPERVISOR','BRIEFING')),
    event TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK(outcome IN ('STARTED','SUCCEEDED','REVISE','FALLBACK','FAILED','WAITING','SKIPPED')),
    note TEXT, model TEXT,
    input_tokens INTEGER CHECK(input_tokens IS NULL OR input_tokens>=0),
    output_tokens INTEGER CHECK(output_tokens IS NULL OR output_tokens>=0),
    latency_ms INTEGER CHECK(latency_ms IS NULL OR latency_ms>=0),
    at TEXT NOT NULL
);
CREATE INDEX agent_activity_investigation ON agent_activity(investigation_id, at);
CREATE INDEX agent_activity_morning_review ON agent_activity(morning_review_id, at);
CREATE TRIGGER agent_activity_append_only BEFORE UPDATE ON agent_activity
BEGIN SELECT RAISE(ABORT,'Agent activity is append-only'); END;
