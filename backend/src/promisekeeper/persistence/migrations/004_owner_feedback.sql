CREATE TABLE owner_feedback (
    id TEXT PRIMARY KEY,
    demonstration_id TEXT NOT NULL REFERENCES demonstrations(id),
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    investigation_id TEXT NOT NULL,
    target TEXT NOT NULL CHECK(target IN ('RECOMMENDATION','DRAFT')),
    rating TEXT NOT NULL CHECK(rating IN ('UP','DOWN')),
    comment TEXT CHECK(comment IS NULL OR length(comment) <= 500),
    operation_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    langsmith_sent INTEGER NOT NULL DEFAULT 0 CHECK(langsmith_sent IN (0,1))
);
CREATE TABLE draft_edit_feedback (
    id TEXT PRIMARY KEY,
    demonstration_id TEXT NOT NULL REFERENCES demonstrations(id),
    case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    investigation_id TEXT NOT NULL,
    draft_version_id TEXT NOT NULL,
    agent_text TEXT NOT NULL,
    approved_text TEXT NOT NULL,
    changed INTEGER NOT NULL CHECK(changed IN (0,1)),
    created_at TEXT NOT NULL
);
