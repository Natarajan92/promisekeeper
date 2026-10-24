"""Recording advice never changes finance, draft approval or lifecycle."""
from uuid import uuid4
from promisekeeper.application.operations import instant, replay, save_receipt, utcnow
from promisekeeper.application.reviews import result_context
from promisekeeper.persistence.repositories import append_event, case, require_revision


def record_disposition(db, did, cid, request):
    with db.transaction() as con:
        saved = replay(con, did, 'RECORD_DISPOSITION', cid, request)
        if saved:
            return saved
        row = case(con, did, cid)
        require_revision(row, request)
        result_context(con, row, request['investigation_id'])
        disposition = dict(id=str(uuid4()), demonstration_id=did, case_id=cid, operation_id=request['operation_id'],
            investigation_id=request['investigation_id'], decision=request['decision'], reason=request.get('reason'), decided_at=instant(utcnow()))
        con.execute('INSERT INTO owner_dispositions VALUES (?,?,?,?,?,?,?,?)', tuple(disposition.values()))
        con.execute('UPDATE cases SET case_revision=case_revision+1 WHERE id=?', (cid,))
        append_event(con, row, 'ADVICE_DISPOSITION_RECORDED', request['operation_id'],
            dict(disposition_id=disposition['id'], investigation_id=request['investigation_id'], decision=request['decision']))
        return save_receipt(con, did, 'RECORD_DISPOSITION', cid, request, 'RECORDED', revision=row['case_revision']+1, disposition=disposition)
