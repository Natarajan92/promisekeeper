"""Read only exact IDs from an immutable captured packet, with no truncation."""
from copy import deepcopy
from datetime import datetime
import json
from uuid import UUID
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.application.operations import digest
from promisekeeper.domain.evidence import (Attribution, Availability, CaseEvidence, CommitmentAnchor,
    Evidence, Invoice, Message, Payment, SourceKind, VerificationStatus)

def read_snapshot(db, request):
    if set(request) != {'schema_version','snapshot_id','evidence_version_ids'} or request['schema_version'] != '1':
        raise InvestigatorFailure('INVALID_SNAPSHOT_REQUEST')
    ids = request['evidence_version_ids']
    if not isinstance(ids,list) or len(ids) != len(set(ids)):
        raise InvestigatorFailure('INVALID_SNAPSHOT_REQUEST')
    with db.connection() as con:
        row = con.execute('SELECT * FROM evidence_snapshots WHERE id=?',(request['snapshot_id'],)).fetchone()
        if row is None:
            raise InvestigatorFailure('SNAPSHOT_NOT_FOUND')
        packet = json.loads(row['packet_json'])
        if digest(packet) != row['hash']:
            raise InvestigatorFailure('SNAPSHOT_INTEGRITY_FAILURE')
    if not set(ids) <= {r['id'] for r in packet['evidence']}:
        raise InvestigatorFailure('FOREIGN_SNAPSHOT_REFERENCE')
    records = [r for r in packet['evidence'] if r['id'] in ids]
    if len(records)>64 or any(len(r['original_content'])>8000 for r in records) or sum(len(r['original_content']) for r in records)>64000:
        raise InvestigatorFailure('SNAPSHOT_PACKET_TOO_LARGE')
    return deepcopy(packet | dict(snapshot_id=row['id'], snapshot_hash=row['hash'], evidence=records))

def snapshot_case(packet):
    """Reconstruct deterministic facts exclusively from captured records."""
    did,cid = UUID(packet['demonstration_id']),UUID(packet['case_id'])
    sources = {}
    for r in packet['evidence']:
        original_at=r.get('original_event_at',r['event_at'])
        sources[r['id']] = Evidence(UUID(r['id']),did,cid,r['stable_source_id'],SourceKind(r['kind']),r['original_content'],
            datetime.fromisoformat(original_at) if original_at else None,datetime.fromisoformat(r['arrived_at']),
            Availability(r['availability']),r['authoritative'],r['version'],UUID(r['supersedes_version_id']) if r['supersedes_version_id'] else None)
    by_source = {s.source_id:s.id for s in sources.values()}
    invoices,payments,messages,anchors,links = [],[],[],[],[]
    for r in packet['evidence']:
        s,d = sources[r['id']],r['data']
        if s.kind == 'INVOICE': invoices.append(Invoice(s,**d))
        elif s.kind in {'LEDGER','REVERSAL'}:
            payments.append(Payment(s,d['transaction_ref'],d['amount_text'],d['currency_text'],d['invoice_id'],
                VerificationStatus(d['verification_status']),d['settled'],by_source.get(d.get('reverses_source_id')),by_source.get(d.get('suspected_duplicate_source_id'))))
        elif s.kind == 'MESSAGE': messages.append(Message(s,d['speaker']))
        for a in r['commitment_anchors']:
            anchors.append(CommitmentAnchor(UUID(a['id']),did,cid,UUID(a['evidence_version_id']),a['commitment_key'],a['clause_start'],a['clause_end']))
    for r in packet['evidence']:
        if r['kind'] == 'ATTRIBUTION':
            d=r['data']; target=by_source[d['commitment_source_id']]
            a=next(a for a in anchors if a.evidence_version_id==target and a.commitment_key==d['commitment_key'])
            links.append(Attribution(sources[r['id']],by_source[d['payment_source_id']],a.id,d['attributed_amount_text'],d['currency_text']))
    if not invoices: raise InvestigatorFailure('MISSING_INVOICE_RECORD')
    return CaseEvidence(did,cid,invoices[0].source.source_id.split('-')[0]+'-'+invoices[0].source.source_id.split('-')[1],
        invoices[0].client,invoices[0].invoice_id,tuple(invoices),tuple(payments),tuple(messages),tuple(anchors),tuple(links),
        Availability(packet['ledger_availability']),packet['ledger_complete'])
