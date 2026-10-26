"""Identify pre-review imported communication without rewriting immutable sources."""


def needs_sender_review(con,did,cid=None):
    return con.execute("""SELECT 1 FROM intake_documents
        WHERE demonstration_id=? AND (? IS NULL OR case_id=?)
        AND json_extract(extraction_json,'$.sender_role') IS NULL
        AND coalesce(json_extract(extraction_json,'$.context_only'),0)=0 LIMIT 1""",(did,cid,cid)).fetchone() is not None
