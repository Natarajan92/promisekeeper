CREATE TABLE demonstrations (
    id TEXT PRIMARY KEY, catalogue_version TEXT NOT NULL,
    created_at TEXT NOT NULL, clock_mode TEXT NOT NULL CHECK(clock_mode IN ('REFERENCE','REAL')),
    reference_at TEXT NOT NULL, reference_clock_event_id TEXT,
    selected_variant_id TEXT, applied_events_json TEXT NOT NULL,
    deleted INTEGER NOT NULL DEFAULT 0 CHECK(deleted IN (0,1))
);
CREATE TABLE cases (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL REFERENCES demonstrations(id) ON DELETE CASCADE,
    catalogue_case_id TEXT NOT NULL CHECK(catalogue_case_id IN ('PK-001','PK-002','PK-003')),
    client TEXT NOT NULL, invoice_id TEXT NOT NULL,
    lifecycle TEXT NOT NULL DEFAULT 'OPEN' CHECK(lifecycle IN ('OPEN','CLOSED')),
    case_revision INTEGER NOT NULL DEFAULT 0 CHECK(case_revision>=0),
    evidence_revision INTEGER NOT NULL DEFAULT 0 CHECK(evidence_revision>=0),
    review_epoch INTEGER NOT NULL DEFAULT 0 CHECK(review_epoch>=0),
    latest_completed_investigation_id TEXT, current_draft_version_id TEXT,
    next_event_sequence INTEGER NOT NULL DEFAULT 1 CHECK(next_event_sequence>=1),
    ledger_availability TEXT NOT NULL CHECK(ledger_availability IN ('AVAILABLE','UNAVAILABLE','MISSING','UNREADABLE')),
    ledger_complete INTEGER NOT NULL CHECK(ledger_complete IN (0,1)),
    UNIQUE(demonstration_id, catalogue_case_id), UNIQUE(demonstration_id,id),
    FOREIGN KEY(demonstration_id,id,latest_completed_investigation_id) REFERENCES investigations(demonstration_id,case_id,id) DEFERRABLE INITIALLY DEFERRED,
    FOREIGN KEY(demonstration_id,id,current_draft_version_id) REFERENCES draft_versions(demonstration_id,case_id,id) DEFERRABLE INITIALLY DEFERRED
);
CREATE TRIGGER monotonic_case_revisions BEFORE UPDATE ON cases
WHEN NEW.case_revision<OLD.case_revision OR NEW.evidence_revision<OLD.evidence_revision
 OR NEW.review_epoch<OLD.review_epoch OR NEW.next_event_sequence<OLD.next_event_sequence
BEGIN SELECT RAISE(ABORT,'Monotonic revisions required'); END;
CREATE TABLE evidence_versions (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
    stable_source_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version>=1),
    kind TEXT NOT NULL CHECK(kind IN ('INVOICE','LEDGER','MESSAGE','REVERSAL','ATTRIBUTION')),
    original_content TEXT NOT NULL CHECK(length(original_content)<=8000), event_at TEXT, arrived_at TEXT NOT NULL,
    availability TEXT NOT NULL CHECK(availability IN ('AVAILABLE','UNAVAILABLE','MISSING','UNREADABLE')),
    authoritative INTEGER NOT NULL CHECK(authoritative IN (0,1)), supersedes_version_id TEXT,
    record_json TEXT NOT NULL CHECK(json_valid(record_json)),
    UNIQUE(demonstration_id,case_id,id), UNIQUE(demonstration_id,id),
    UNIQUE(demonstration_id,case_id,stable_source_id,version),
    FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE,
    FOREIGN KEY(demonstration_id,case_id,supersedes_version_id) REFERENCES evidence_versions(demonstration_id,case_id,id)
);
CREATE TABLE invoice_projections (
    evidence_version_id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL, client TEXT NOT NULL, amount_text TEXT, currency_text TEXT, due_text TEXT,
    minor_units TEXT, unresolved_reason TEXT,
    CHECK(minor_units IS NULL OR minor_units='0' OR (minor_units NOT GLOB '*[^0-9]*' AND minor_units GLOB '[1-9]*')),
    FOREIGN KEY(demonstration_id,case_id,evidence_version_id) REFERENCES evidence_versions(demonstration_id,case_id,id) ON DELETE CASCADE
);
CREATE TABLE payment_projections (
    evidence_version_id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
    transaction_ref TEXT, amount_text TEXT, currency_text TEXT, invoice_id TEXT,
    minor_units TEXT, unresolved_reason TEXT,
    verification_status TEXT NOT NULL CHECK(verification_status IN ('VERIFIED','UNVERIFIED','UNKNOWN')),
    settled INTEGER NOT NULL CHECK(settled IN (0,1)), reverses_payment_version_id TEXT, suspected_duplicate_of TEXT,
    UNIQUE(demonstration_id,case_id,evidence_version_id),
    CHECK(minor_units IS NULL OR minor_units='0' OR (minor_units NOT GLOB '*[^0-9]*' AND minor_units GLOB '[1-9]*')),
    FOREIGN KEY(demonstration_id,case_id,evidence_version_id) REFERENCES evidence_versions(demonstration_id,case_id,id) ON DELETE CASCADE,
    FOREIGN KEY(demonstration_id,case_id,reverses_payment_version_id) REFERENCES payment_projections(demonstration_id,case_id,evidence_version_id),
    FOREIGN KEY(demonstration_id,case_id,suspected_duplicate_of) REFERENCES payment_projections(demonstration_id,case_id,evidence_version_id)
);
CREATE TABLE commitment_anchors (
    id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, evidence_version_id TEXT NOT NULL,
    commitment_key TEXT NOT NULL, clause_start INTEGER NOT NULL CHECK(clause_start>=0),
    clause_end INTEGER NOT NULL CHECK(clause_end>clause_start),
    UNIQUE(demonstration_id,evidence_version_id,commitment_key), UNIQUE(demonstration_id,case_id,id),
    FOREIGN KEY(demonstration_id,case_id,evidence_version_id) REFERENCES evidence_versions(demonstration_id,case_id,id) ON DELETE CASCADE
);
CREATE TRIGGER anchor_range BEFORE INSERT ON commitment_anchors
WHEN NEW.clause_end>(SELECT length(original_content) FROM evidence_versions WHERE id=NEW.evidence_version_id)
 OR EXISTS(SELECT 1 FROM commitment_anchors WHERE evidence_version_id=NEW.evidence_version_id AND clause_start<NEW.clause_end AND clause_end>NEW.clause_start)
BEGIN SELECT RAISE(ABORT,'Invalid or overlapping anchor'); END;
CREATE TABLE commitment_attributions (
    evidence_version_id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
    payment_version_id TEXT NOT NULL, commitment_stable_id TEXT NOT NULL,
    attributed_amount_text TEXT, currency_text TEXT, attributed_minor_units TEXT,
    FOREIGN KEY(demonstration_id,case_id,evidence_version_id) REFERENCES evidence_versions(demonstration_id,case_id,id) ON DELETE CASCADE,
    FOREIGN KEY(demonstration_id,case_id,payment_version_id) REFERENCES payment_projections(demonstration_id,case_id,evidence_version_id),
    FOREIGN KEY(demonstration_id,case_id,commitment_stable_id) REFERENCES commitment_anchors(demonstration_id,case_id,id)
);
