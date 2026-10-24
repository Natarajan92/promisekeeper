CREATE TABLE evidence_snapshots (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
    evidence_revision INTEGER NOT NULL CHECK(evidence_revision>=0), captured_at TEXT NOT NULL,
    packet_json TEXT NOT NULL CHECK(json_valid(packet_json)), hash TEXT NOT NULL CHECK(length(hash)=64),
    UNIQUE(demonstration_id,case_id,id),
    FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE
);
CREATE TABLE investigations (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, operation_id TEXT NOT NULL UNIQUE,
    retry_of TEXT, started_at TEXT NOT NULL, evaluation_at TEXT NOT NULL, deadline_at TEXT NOT NULL,
    snapshot_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('RUNNING','COMPLETE','LIMITED','INCOMPLETE')),
    terminal_at TEXT, failure_code TEXT, agent_mode TEXT NOT NULL CHECK(agent_mode IN ('STUB','LIVE')),
    requested_model TEXT, returned_model TEXT, response_id TEXT, prompt_version TEXT, schema_version TEXT, adapter_version TEXT,
    CHECK((status='RUNNING' AND terminal_at IS NULL) OR (status<>'RUNNING' AND terminal_at IS NOT NULL)),
    UNIQUE(demonstration_id,case_id,id),
    FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE,
    FOREIGN KEY(demonstration_id,case_id,snapshot_id) REFERENCES evidence_snapshots(demonstration_id,case_id,id),
    FOREIGN KEY(demonstration_id,case_id,retry_of) REFERENCES investigations(demonstration_id,case_id,id)
);
CREATE UNIQUE INDEX one_running_case ON investigations(case_id) WHERE status='RUNNING';
CREATE TRIGGER terminal_investigation BEFORE UPDATE ON investigations WHEN OLD.status<>'RUNNING'
BEGIN SELECT RAISE(ABORT,'Terminal attempt is fenced'); END;
CREATE TABLE investigation_results (
    investigation_id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('FOLLOW_UP','WAIT','VERIFY_PAYMENT','CLOSE')),
    review_at TEXT, result_json TEXT NOT NULL CHECK(json_valid(result_json)), result_hash TEXT NOT NULL,
    rule_version TEXT NOT NULL,
    CHECK((action='WAIT' AND review_at IS NOT NULL) OR (action<>'WAIT' AND review_at IS NULL)),
    FOREIGN KEY(demonstration_id,case_id,investigation_id) REFERENCES investigations(demonstration_id,case_id,id) ON DELETE CASCADE
);
CREATE TRIGGER result_requires_completion BEFORE INSERT ON investigation_results
WHEN NOT EXISTS(SELECT 1 FROM investigations WHERE id=NEW.investigation_id AND status IN ('COMPLETE','LIMITED'))
BEGIN SELECT RAISE(ABORT,'Incomplete attempt has no result'); END;
CREATE TABLE step_attempts (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
    step_name TEXT NOT NULL, invocation_number INTEGER NOT NULL CHECK(invocation_number>=1),
    invocation_kind TEXT NOT NULL CHECK(invocation_kind IN ('INITIAL','AUTO_RETRY','MANUAL_RETRY')),
    operation_id TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT, outcome TEXT, failure_code TEXT,
    CHECK(step_name<>'EXTRACTION' OR invocation_kind IN ('INITIAL','AUTO_RETRY')),
    UNIQUE(investigation_id,step_name,invocation_number),
    FOREIGN KEY(demonstration_id,case_id,investigation_id) REFERENCES investigations(demonstration_id,case_id,id) ON DELETE CASCADE
);
CREATE UNIQUE INDEX one_auto_retry ON step_attempts(investigation_id,step_name) WHERE invocation_kind='AUTO_RETRY';
CREATE UNIQUE INDEX one_initial_step ON step_attempts(investigation_id,step_name) WHERE invocation_kind='INITIAL';
CREATE TABLE draft_generation_attempts (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
    operation_id TEXT NOT NULL UNIQUE, retry_of TEXT, expected_draft_head TEXT,
    status TEXT NOT NULL CHECK(status IN ('RUNNING','READY','FAILED')),
    started_at TEXT NOT NULL, deadline_at TEXT NOT NULL, terminal_at TEXT, failure_code TEXT,
    UNIQUE(demonstration_id,case_id,id),
    CHECK((status='RUNNING' AND terminal_at IS NULL) OR (status<>'RUNNING' AND terminal_at IS NOT NULL)),
    FOREIGN KEY(demonstration_id,case_id,investigation_id) REFERENCES investigations(demonstration_id,case_id,id) ON DELETE CASCADE,
    FOREIGN KEY(demonstration_id,case_id,retry_of) REFERENCES draft_generation_attempts(demonstration_id,case_id,id),
    FOREIGN KEY(demonstration_id,case_id,expected_draft_head) REFERENCES draft_versions(demonstration_id,case_id,id)
);
CREATE TRIGGER terminal_draft_attempt BEFORE UPDATE ON draft_generation_attempts WHEN OLD.status<>'RUNNING'
BEGIN SELECT RAISE(ABORT,'Terminal draft attempt is fenced'); END;
CREATE TABLE draft_versions (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, investigation_id TEXT NOT NULL,
    parent_version_id TEXT, recipient TEXT NOT NULL, invoice_id TEXT NOT NULL,
    exact_text TEXT NOT NULL CHECK(length(exact_text) BETWEEN 1 AND 8000), version INTEGER NOT NULL CHECK(version>=1),
    payload_hash TEXT NOT NULL, created_at TEXT NOT NULL, validation_status TEXT NOT NULL, validation_reasons_json TEXT NOT NULL,
    UNIQUE(demonstration_id,case_id,id), UNIQUE(case_id,version),
    FOREIGN KEY(demonstration_id,case_id,investigation_id) REFERENCES investigations(demonstration_id,case_id,id) ON DELETE CASCADE,
    FOREIGN KEY(demonstration_id,case_id,parent_version_id) REFERENCES draft_versions(demonstration_id,case_id,id)
);
CREATE TABLE draft_reviews (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, operation_id TEXT NOT NULL UNIQUE,
    draft_version_id TEXT NOT NULL, owner_actor TEXT NOT NULL,
    decision TEXT NOT NULL CHECK(decision IN ('APPROVE','REJECT')), decided_at TEXT NOT NULL,
    exact_text TEXT NOT NULL, recipient TEXT NOT NULL, invoice_id TEXT NOT NULL, payload_hash TEXT NOT NULL,
    investigation_id TEXT NOT NULL, evidence_revision INTEGER NOT NULL, review_epoch INTEGER NOT NULL,
    FOREIGN KEY(demonstration_id,case_id,draft_version_id) REFERENCES draft_versions(demonstration_id,case_id,id) ON DELETE CASCADE,
    FOREIGN KEY(demonstration_id,case_id,investigation_id) REFERENCES investigations(demonstration_id,case_id,id)
);
CREATE TABLE owner_dispositions (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, operation_id TEXT NOT NULL UNIQUE,
    investigation_id TEXT NOT NULL, decision TEXT NOT NULL CHECK(decision IN ('ACCEPT','REJECT')),
    reason TEXT CHECK(length(reason)<=1000), decided_at TEXT NOT NULL,
    FOREIGN KEY(demonstration_id,case_id,investigation_id) REFERENCES investigations(demonstration_id,case_id,id) ON DELETE CASCADE
);
CREATE TABLE case_events (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
    sequence INTEGER NOT NULL CHECK(sequence>=1), event_type TEXT NOT NULL, operation_id TEXT,
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)), occurred_at TEXT NOT NULL,
    UNIQUE(case_id,sequence),
    FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE
);
CREATE TABLE operation_receipts (
    operation_id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL,
    operation_type TEXT NOT NULL, canonical_request_hash TEXT NOT NULL,
    target_id TEXT NOT NULL, committed_at TEXT NOT NULL, response_json TEXT NOT NULL CHECK(json_valid(response_json))
);
CREATE TABLE operation_tombstones (
    operation_id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL,
    operation_type TEXT NOT NULL, canonical_request_hash TEXT NOT NULL, committed_at TEXT NOT NULL
);
CREATE TRIGGER permanent_operation_tombstone_update BEFORE UPDATE ON operation_tombstones
BEGIN SELECT RAISE(ABORT,'Permanent operation identity'); END;
CREATE TRIGGER permanent_operation_tombstone_delete BEFORE DELETE ON operation_tombstones
BEGIN SELECT RAISE(ABORT,'Permanent operation identity'); END;
CREATE TRIGGER receipt_cannot_reuse_tombstone BEFORE INSERT ON operation_receipts
WHEN EXISTS(SELECT 1 FROM operation_tombstones WHERE operation_id=NEW.operation_id)
BEGIN SELECT RAISE(ABORT,'Deleted operation identity'); END;
CREATE TRIGGER immutable_step_identity BEFORE UPDATE ON step_attempts
WHEN NEW.id<>OLD.id OR NEW.demonstration_id<>OLD.demonstration_id OR NEW.case_id<>OLD.case_id
 OR NEW.investigation_id<>OLD.investigation_id OR NEW.step_name<>OLD.step_name
 OR NEW.invocation_number<>OLD.invocation_number OR NEW.invocation_kind<>OLD.invocation_kind
 OR NEW.operation_id<>OLD.operation_id OR NEW.started_at<>OLD.started_at OR OLD.ended_at IS NOT NULL
BEGIN SELECT RAISE(ABORT,'Step identity and retry usage are immutable'); END;
CREATE TRIGGER retained_step_usage BEFORE DELETE ON step_attempts
WHEN EXISTS(SELECT 1 FROM demonstrations WHERE id=OLD.demonstration_id AND deleted=0)
BEGIN SELECT RAISE(ABORT,'Retry usage is retained'); END;
