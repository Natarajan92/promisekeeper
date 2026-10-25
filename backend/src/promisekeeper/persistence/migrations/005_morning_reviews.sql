CREATE TABLE morning_reviews (
    id TEXT PRIMARY KEY,
    demonstration_id TEXT NOT NULL REFERENCES demonstrations(id),
    operation_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','COMPLETE','FAILED')),
    started_at TEXT NOT NULL,
    terminal_at TEXT,
    briefing TEXT,
    briefing_source TEXT CHECK(briefing_source IS NULL OR briefing_source IN ('AGENT','DETERMINISTIC')),
    outcomes_json TEXT NOT NULL DEFAULT '[]',
    failure_code TEXT,
    CHECK((status='RUNNING' AND terminal_at IS NULL) OR (status<>'RUNNING' AND terminal_at IS NOT NULL))
);
CREATE UNIQUE INDEX one_running_morning_review ON morning_reviews(demonstration_id) WHERE status='RUNNING';
