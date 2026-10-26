CREATE TABLE intake_batches (
 id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL REFERENCES demonstrations(id),
 kind TEXT NOT NULL, filename TEXT NOT NULL, content TEXT NOT NULL,
 content_hash TEXT NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE intake_customers (
 demonstration_id TEXT NOT NULL REFERENCES demonstrations(id), customer_id TEXT NOT NULL,
 data_json TEXT NOT NULL CHECK(json_valid(data_json)), batch_id TEXT NOT NULL REFERENCES intake_batches(id),
 PRIMARY KEY(demonstration_id,customer_id)
);
CREATE TABLE intake_invoices (
 demonstration_id TEXT NOT NULL, invoice_id TEXT NOT NULL, case_id TEXT NOT NULL,
 data_json TEXT NOT NULL CHECK(json_valid(data_json)), batch_id TEXT NOT NULL REFERENCES intake_batches(id),
 PRIMARY KEY(demonstration_id,invoice_id),
 FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE
);
CREATE TABLE intake_payments (
 id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL REFERENCES demonstrations(id),
 transaction_ref TEXT NOT NULL, amount_minor INTEGER NOT NULL CHECK(amount_minor>0),
 data_json TEXT NOT NULL CHECK(json_valid(data_json)), batch_id TEXT NOT NULL REFERENCES intake_batches(id),
 UNIQUE(demonstration_id,transaction_ref), UNIQUE(demonstration_id,id)
);
CREATE TABLE intake_allocations (
 id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, payment_id TEXT NOT NULL, case_id TEXT NOT NULL,
 amount_minor INTEGER NOT NULL CHECK(amount_minor>0), evidence_source_id TEXT NOT NULL,
 operation_id TEXT NOT NULL, import_key TEXT, created_at TEXT NOT NULL,
 UNIQUE(demonstration_id,import_key),
 FOREIGN KEY(demonstration_id,payment_id) REFERENCES intake_payments(demonstration_id,id) ON DELETE CASCADE,
 FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE
);
CREATE TABLE intake_documents (
 id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL, kind TEXT NOT NULL,
 batch_id TEXT NOT NULL REFERENCES intake_batches(id), content_hash TEXT NOT NULL,
 extraction_json TEXT NOT NULL CHECK(json_valid(extraction_json)), created_at TEXT NOT NULL,
 UNIQUE(demonstration_id,case_id,kind,content_hash),
 FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE
);
CREATE TABLE intake_ledger_reviews (
 id TEXT PRIMARY KEY, demonstration_id TEXT NOT NULL, case_id TEXT NOT NULL,
 reviewed_through TEXT NOT NULL, operation_id TEXT NOT NULL, created_at TEXT NOT NULL,
 FOREIGN KEY(demonstration_id,case_id) REFERENCES cases(demonstration_id,id) ON DELETE CASCADE
);
