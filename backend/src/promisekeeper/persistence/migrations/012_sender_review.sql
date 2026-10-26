-- Retain immutable advice/history but fence decisions based on communication
-- imported before explicit sender review. Context-only evidence remains safe.
UPDATE cases
SET case_revision=case_revision+1,
    evidence_revision=evidence_revision+1,
    review_epoch=review_epoch+1,
    ledger_complete=0
WHERE id IN (
 SELECT case_id FROM intake_documents
 WHERE json_extract(extraction_json,'$.sender_role') IS NULL
   AND coalesce(json_extract(extraction_json,'$.context_only'),0)=0
);
