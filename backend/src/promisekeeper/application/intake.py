"""Atomic, local fictional file intake in front of the existing evidence engine."""
from datetime import datetime
import json
from uuid import UUID,uuid4,uuid5

from promisekeeper.application.document_extraction import extract_document
from promisekeeper.domain.document_extraction import DocumentReviewRequired
from promisekeeper.application.bank_import import parse_upload,generated_overlap
from promisekeeper.application.intake_parsing import amount_minor,evidence_amount,facts,parse_csv,stored_facts,MAX_FILE_BYTES
from promisekeeper.application.operations import CommandError,canonical,digest,instant,replay,save_receipt,utcnow
from promisekeeper.application.payment_matching import suggest_invoices
from promisekeeper.fixtures.catalogue import CASE_IDS,_build
from promisekeeper.persistence.repositories import append_event,append_evidence,case,demonstration,load_fixture,require_revision

DOCUMENT_KINDS={'remittance_email','customer_email','whatsapp'}
INTAKE_TABLES=('intake_customers','intake_invoices','intake_payments','intake_allocations','intake_documents','intake_ledger_reviews','intake_batches')


def _revisions(con,did):
    return {r['id']:r['case_revision'] for r in con.execute('SELECT id,case_revision FROM cases WHERE demonstration_id=?',(did,))}


def _workspace(con,did,*,writing=False):
    demo=demonstration(con,did)
    if demo['selected_variant_id']!='csv-demo':raise CommandError('IMPORT_WORKSPACE_REQUIRED',422)
    if writing and con.execute("SELECT 1 FROM investigations WHERE demonstration_id=? AND status='RUNNING'",(did,)).fetchone():
        raise CommandError('INVESTIGATION_RUNNING')
    return demo


def _state(con,did):
    if did is None:return 'new'
    demo=_workspace(con,did)
    counts={table:tuple(con.execute(f'SELECT count(*),max(rowid) FROM {table} WHERE demonstration_id=?',(did,)).fetchone()) for table in INTAKE_TABLES}
    versions=[tuple(r) for r in con.execute('SELECT id,case_revision,evidence_revision,ledger_complete FROM cases WHERE demonstration_id=? ORDER BY id',(did,))]
    return digest(dict(counts=counts,versions=versions,as_of=demo['reference_at']))


def _semantic(row):
    return stored_facts(row)


def _batch(con,did,request,now):
    bid=str(uuid4())
    filename=request['filename'].replace('\\','/').rsplit('/',1)[-1]
    con.execute('INSERT INTO intake_batches VALUES (?,?,?,?,?,?,?)',
                (bid,did,request['kind'],filename,request['content'],digest(request['content']),now))
    return bid


def _allocation_key(row):
    return digest(dict(transaction_ref=row['transaction_ref'],invoice_id=row['invoice_id'],amount_minor=row['amount_minor']))


def _preview(con,request):
    did=request.get('demonstration_id');kind=request['kind'];errors=[];warnings=[];rows=[];extraction=None;duplicates=0
    if did:_workspace(con,did)
    if len(request['content'].encode('utf-8'))>MAX_FILE_BYTES:
        errors.append(dict(row=0,message='File exceeds 256 KiB.'))
    elif kind in DOCUMENT_KINDS:
        if not did or not request.get('case_id'):errors.append(dict(row=0,message='Choose an imported workspace and target invoice first.'))
        elif len(request['content'])>8000:errors.append(dict(row=0,message='Communication documents must fit the 8,000-character evidence limit.'))
        else:
            target=case(con,did,request['case_id'])
            try:
                extraction=extract_document(request['content'],kind,event_at=request.get('event_at'),context_only=request.get('context_only',False),sender_role=request.get('sender_role','UNVERIFIED'))
                if datetime.fromisoformat(extraction['event_at'])>utcnow():raise ValueError('A source message cannot arrive from the future.')
                hints=extraction['invoice_references']
                if hints and set(hints)!={target['invoice_id']}:
                    raise ValueError('Document invoice references differ from the selected invoice or mention multiple invoices. Upload one invoice-specific message.')
                warnings.extend(extraction['warnings'])
                duplicates=int(con.execute('SELECT 1 FROM intake_documents WHERE demonstration_id=? AND case_id=? AND kind=? AND content_hash=?',
                                          (did,request['case_id'],kind,digest(request['content']))).fetchone() is not None)
            except (ValueError,TypeError,OverflowError) as error:
                errors.append(dict(row=0,message=str(error),**({'code':error.code} if isinstance(error,DocumentReviewRequired) else {})))
    else:
        rows,errors,bank_warnings=parse_upload(kind,request['content']);warnings.extend(bank_warnings)
        if not did and kind in {'payments','allocations'}:errors.append(dict(row=0,message='Import customers or invoices into a new workspace first.'))
        existing={}
        if did and kind in {'customers','invoices','payments'}:
            table={'customers':'intake_customers','invoices':'intake_invoices','payments':'intake_payments'}[kind]
            key={'customers':'customer_id','invoices':'invoice_id','payments':'transaction_ref'}[kind]
            existing={r[key]:r['data_json'] for r in con.execute(f'SELECT * FROM {table} WHERE demonstration_id=?',(did,))}
        seen={};new_invoices=0;payment_usage={};invoice_usage={};allocation_seen=set()
        for row in rows:
            try:
                if kind=='invoices':
                    if row['customer_id']:
                        customer=con.execute('SELECT data_json FROM intake_customers WHERE demonstration_id=? AND customer_id=?',(did,row['customer_id'])).fetchone() if did else None
                        if customer is None:raise ValueError('Import this customer_id first, or provide customer_name without a customer_id.')
                        master=json.loads(customer[0])
                        for field in ['customer_name','customer_alias','address']:
                            if not row[field]:row[field]=master.get(field,'')
                    if not row['customer_name']:raise ValueError('Customer name is required.')
                    if len(row['customer_name'])>160:raise ValueError('Customer name exceeds 160 characters.')
                if kind=='allocations':
                    if not did:continue
                    key=_allocation_key(row)
                    if key in allocation_seen or con.execute('SELECT 1 FROM intake_allocations WHERE demonstration_id=? AND import_key=?',(did,key)).fetchone():
                        row['_duplicate']=True;duplicates+=1;continue
                    allocation_seen.add(key)
                    payment=con.execute('SELECT * FROM intake_payments WHERE demonstration_id=? AND transaction_ref=?',(did,row['transaction_ref'])).fetchone()
                    invoice=con.execute('SELECT * FROM intake_invoices WHERE demonstration_id=? AND invoice_id=?',(did,row['invoice_id'])).fetchone()
                    if payment is None or invoice is None:raise ValueError('Receipt and invoice references must both exist in this workspace.')
                    if json.loads(payment['data_json'])['status'] in {'PENDING','REVERSED'}:raise ValueError('A pending or reversed receipt cannot be allocated.')
                    used=con.execute('SELECT coalesce(sum(amount_minor),0) FROM intake_allocations WHERE demonstration_id=? AND payment_id=?',(did,payment['id'])).fetchone()[0]
                    paid=con.execute('SELECT coalesce(sum(amount_minor),0) FROM intake_allocations WHERE demonstration_id=? AND case_id=?',(did,invoice['case_id'])).fetchone()[0]
                    payment_usage[payment['id']]=payment_usage.get(payment['id'],0)+row['amount_minor']
                    invoice_usage[invoice['case_id']]=invoice_usage.get(invoice['case_id'],0)+row['amount_minor']
                    if used+payment_usage[payment['id']]>payment['amount_minor'] or paid+invoice_usage[invoice['case_id']]>json.loads(invoice['data_json'])['amount_minor']:
                        raise ValueError('Allocations exceed the receipt or invoice remaining amount.')
                    continue
                if kind=='payments' and any(generated_overlap(row,json.loads(prior)) for prior in [*existing.values(),*seen.values()]):
                    raise ValueError('Ambiguous bank overlap: the same date/description/amount already has a generated or supplied reference. Review originals; use the existing receipt or rebuild an imported workspace with stable bank references. No second receipt was added.')
                key=row['customer_id'] if kind=='customers' else row['invoice_id'] if kind=='invoices' else row['transaction_ref']
                value=_semantic(row)
                if key in existing or key in seen:
                    if (existing.get(key) or seen.get(key))!=value:raise ValueError('Identifier conflicts with an existing record; no original will be overwritten.')
                    row['_duplicate']=True;duplicates+=1
                elif kind=='invoices':new_invoices+=1
                seen[key]=value
            except (ValueError,TypeError) as error:errors.append(dict(row=row['_row'],message=str(error)))
        if kind=='invoices':
            count=con.execute('SELECT count(*) FROM cases WHERE demonstration_id=?',(did,)).fetchone()[0] if did else 0
            if count+new_invoices>len(CASE_IDS):errors.append(dict(row=0,message='Up to six invoices are supported per workspace.'))
    state=_state(con,did)
    identity={k:request.get(k) for k in ('kind','filename','content','demonstration_id','case_id','event_at','context_only','sender_role')}
    result=dict(schema_version='1',kind=kind,rows=rows,errors=errors,warnings=warnings,duplicates=duplicates,
                extraction=extraction,scope_revision=state,preview_hash=digest(dict(request=identity,state=state)))
    return result


def preview_import(db,request):
    with db.connection() as con:
        con.execute('BEGIN')
        return _preview(con,request)


def _touch(con,did,operation_id,now,*,all_cases=True,cid=None,event='FILE_IMPORTED',payload=None):
    if all_cases:con.execute('UPDATE demonstrations SET reference_at=? WHERE id=?',(now,did))
    rows=con.execute('SELECT * FROM cases WHERE demonstration_id=? AND (? OR id=?)',(did,all_cases,cid)).fetchall()
    for row in rows:
        con.execute('UPDATE cases SET case_revision=case_revision+1,evidence_revision=evidence_revision+1,review_epoch=review_epoch+1,ledger_complete=0 WHERE id=?',(row['id'],))
        append_event(con,dict(row),'APPROVAL_INVALIDATED',operation_id,{'reason':event})
        append_event(con,dict(row),event,operation_id,payload or {})


def _append(con,did,cid,sources):
    fixture=load_fixture(con,did);raw=json.loads(fixture._records_json)
    key=case(con,did,cid)['catalogue_case_id'];raw[key]['sources'].extend(sources)
    updated=_build(UUID(did),'csv-demo',fixture.catalogue_version,fixture.evaluation_at,raw,fixture.applied_events)
    append_evidence(con,updated)


def _source(row,kind,original,data,event_at,arrived_at,*,suffix=None,authoritative=False):
    return dict(source_id=f"{row['catalogue_case_id']}-UPLOAD-{suffix or str(uuid4())}",kind=kind,
                original_content=original,event_at=event_at,arrived_at=arrived_at,
                availability='AVAILABLE',authoritative=authoritative,version=1,data=data)


def _row_text(request,row):
    return f"Uploaded file: {request['filename']}\nOriginal CSV row {row['_row']}:\n{row['_original']}"


def _allocate(con,did,payment_id,cid,minor,operation_id,now,*,import_key=None):
    payment=con.execute('SELECT * FROM intake_payments WHERE demonstration_id=? AND id=?',(did,payment_id)).fetchone()
    if payment is None:raise CommandError('NOT_FOUND',404)
    row=case(con,did,cid)
    invoice=con.execute('SELECT * FROM intake_invoices WHERE demonstration_id=? AND case_id=?',(did,cid)).fetchone()
    if invoice is None:raise CommandError('NOT_FOUND',404)
    paid=con.execute('SELECT coalesce(sum(amount_minor),0) FROM intake_allocations WHERE demonstration_id=? AND case_id=?',(did,cid)).fetchone()[0]
    used=con.execute('SELECT coalesce(sum(amount_minor),0) FROM intake_allocations WHERE demonstration_id=? AND payment_id=?',(did,payment_id)).fetchone()[0]
    source=json.loads(payment['data_json'])
    if source['status'] in {'PENDING','REVERSED'}:raise CommandError('PAYMENT_NOT_SETTLED')
    if minor<=0 or used+minor>payment['amount_minor'] or paid+minor>json.loads(invoice['data_json'])['amount_minor']:
        raise CommandError('ALLOCATION_EXCEEDS_REMAINDER')
    aid=str(uuid4());batch=con.execute('SELECT * FROM intake_batches WHERE id=?',(payment['batch_id'],)).fetchone()
    original=(f"Owner-confirmed receipt allocation: INR {minor//100}.{minor%100:02d} to invoice {row['invoice_id']}.\n"
              f"Original transaction reference: {payment['transaction_ref']}\nReceipt file: {batch['filename']}\n"
              f"Raw receipt: {canonical(source)}\nAllocation confirmed at {now}. This is not an independent bank verification.")
    record=_source(row,'LEDGER',original,dict(transaction_ref='CSV-ALLOCATION:'+aid,
        amount_text=f'{minor//100}.{minor%100:02d}',currency_text='INR',invoice_id=row['invoice_id'],
        verification_status='VERIFIED',settled=True,original_transaction_ref=payment['transaction_ref']),source['paid_at'],now,authoritative=True)
    con.execute('INSERT INTO intake_allocations VALUES (?,?,?,?,?,?,?,?,?)',
                (aid,did,payment_id,cid,minor,record['source_id'],operation_id,import_key,now))
    _append(con,did,cid,[record])
    append_event(con,dict(row),'PAYMENT_ALLOCATED',operation_id,dict(allocation_id=aid,transaction_ref=payment['transaction_ref'],
                 amount_minor=str(minor),invoice_id=row['invoice_id'],source_id=record['source_id']))
    return aid


def commit_import(db,request):
    did=request.get('demonstration_id');target=did or 'new-intake';kind=request['kind']
    with db.transaction() as con:
        try:previous=replay(con,did,'IMPORT_FILE',target,request)
        except CommandError as error:
            if error.code!='OPERATION_PAYLOAD_MISMATCH' or request.get('sender_role')!='UNVERIFIED':raise
            legacy={k:v for k,v in request.items() if k!='sender_role'}
            previous=replay(con,did,'IMPORT_FILE',target,legacy)
        if previous:return previous
        if did:_workspace(con,did,writing=True)
        preview=_preview(con,request)
        if preview['errors']:raise CommandError('IMPORT_VALIDATION_FAILED',422)
        if request['confirmed_preview_hash']!=preview['preview_hash']:raise CommandError('PREVIEW_CHANGED')
        if request.get('confirm') is not True or request.get('fictional_data') is not True:raise CommandError('EXPLICIT_CONFIRMATION_REQUIRED',422)
        if kind=='allocations' and request.get('settled_confirmed') is not True:raise CommandError('EXPLICIT_CONFIRMATION_REQUIRED',422)
        now=instant(utcnow())
        if did is None:
            did=str(uuid4())
            con.execute('INSERT INTO demonstrations (id,catalogue_version,created_at,clock_mode,reference_at,selected_variant_id,applied_events_json) VALUES (?,?,?,?,?,?,?)',
                        (did,'release-0.1',now,'REFERENCE',now,'csv-demo','[]'))
        fresh=[r for r in preview['rows'] if not r.get('_duplicate')]
        changed=bool(fresh) if kind not in DOCUMENT_KINDS else not preview['duplicates']
        if not changed:
            return save_receipt(con,did,'IMPORT_FILE',did,request,'UNCHANGED',hash_target=target,
                                demonstration_id=did,imported=0,duplicates=preview['duplicates'])
        bid=_batch(con,did,request,now)
        # Advance the reference clock before materializing newly arrived evidence.
        con.execute('UPDATE demonstrations SET reference_at=? WHERE id=?',(now,did))
        if kind=='customers':
            for row in fresh:con.execute('INSERT INTO intake_customers VALUES (?,?,?,?)',(did,row['customer_id'],_semantic(row),bid))
        elif kind=='invoices':
            occupied={r[0] for r in con.execute('SELECT catalogue_case_id FROM cases WHERE demonstration_id=?',(did,))}
            slots=iter(key for key in CASE_IDS if key not in occupied)
            for item in fresh:
                slot=next(slots);cid=str(uuid5(UUID(did),slot))
                con.execute('INSERT INTO cases (id,demonstration_id,catalogue_case_id,client,invoice_id,ledger_availability,ledger_complete) VALUES (?,?,?,?,?,?,?)',
                            (cid,did,slot,item['customer_name'],item['invoice_id'],'AVAILABLE',0))
                con.execute('INSERT INTO intake_invoices VALUES (?,?,?,?,?)',(did,item['invoice_id'],cid,_semantic(item),bid))
                record=_source(dict(catalogue_case_id=slot),'INVOICE',_row_text(request,item),
                    dict(invoice_id=item['invoice_id'],client=item['customer_name'],amount_text=evidence_amount(item['amount'],item['amount_minor']),currency_text='INR',due_text=item['due_at']),item['issued_at'],now,authoritative=True)
                _append(con,did,cid,[record]);append_event(con,dict(id=cid,demonstration_id=did),'COPY_CREATED',request['operation_id'],{'origin':'CSV_IMPORT'})
        elif kind=='payments':
            for item in fresh:con.execute('INSERT INTO intake_payments VALUES (?,?,?,?,?,?)',
                (str(uuid4()),did,item['transaction_ref'],item['amount_minor'],_semantic(item),bid))
        elif kind=='allocations':
            for item in fresh:
                payment=con.execute('SELECT id FROM intake_payments WHERE demonstration_id=? AND transaction_ref=?',(did,item['transaction_ref'])).fetchone()
                invoice=con.execute('SELECT case_id FROM intake_invoices WHERE demonstration_id=? AND invoice_id=?',(did,item['invoice_id'])).fetchone()
                _allocate(con,did,payment['id'],invoice['case_id'],item['amount_minor'],request['operation_id'],now,import_key=_allocation_key(item))
        elif kind in DOCUMENT_KINDS:
            row=case(con,did,request['case_id']);extraction=preview['extraction']
            suffix=('CONTEXT-' if request.get('context_only') else 'CUSTOMER-')+str(uuid4())
            record=_source(row,'MESSAGE',request['content'],dict(speaker=extraction['speaker'],candidates=[]),extraction['event_at'],now,suffix=suffix)
            candidates=[]
            for number,item in enumerate(extraction['candidates'],1):
                c={k:v for k,v in item.items() if k not in {'speaker','interpreted_currency','interpreted_date'}}
                if c['kind']=='COMMITMENT':c['commitment_key']=record['source_id']+f'-C{number}'
                candidates.append(c)
            record['data']['candidates']=candidates
            _append(con,did,row['id'],[record])
            con.execute('INSERT INTO intake_documents VALUES (?,?,?,?,?,?,?,?)',
                        (str(uuid4()),did,row['id'],kind,bid,digest(request['content']),canonical(extraction),now))
        _touch(con,did,request['operation_id'],now,event='EVIDENCE_ARRIVED',payload=dict(origin='FILE_IMPORT',batch_id=bid,kind=kind))
        return save_receipt(con,did,'IMPORT_FILE',did,request,'IMPORTED',hash_target=target,
                            demonstration_id=did,imported=len(fresh) if kind not in DOCUMENT_KINDS else 1,duplicates=preview['duplicates'],case_revisions=_revisions(con,did))


def confirm_allocation(db,did,request):
    with db.transaction() as con:
        previous=replay(con,did,'ALLOCATE_PAYMENT',request['case_id'],request)
        if previous:return previous
        _workspace(con,did,writing=True);row=case(con,did,request['case_id']);require_revision(row,request)
        if request.get('confirm') is not True or request.get('settled_confirmed') is not True:raise CommandError('EXPLICIT_CONFIRMATION_REQUIRED',422)
        try:minor=amount_minor(request['amount_text'])
        except ValueError:raise CommandError('INVALID_ALLOCATION_AMOUNT',422) from None
        now=instant(utcnow());_touch(con,did,request['operation_id'],now,event='EVIDENCE_ARRIVED',payload={'origin':'PAYMENT_ALLOCATION'})
        aid=_allocate(con,did,request['payment_id'],request['case_id'],minor,request['operation_id'],now)
        return save_receipt(con,did,'ALLOCATE_PAYMENT',request['case_id'],request,'ALLOCATED',revision=row['case_revision']+1,
                            demonstration_id=did,allocation_id=aid,case_revisions=_revisions(con,did))


def confirm_ledger_review(db,did,request):
    with db.transaction() as con:
        previous=replay(con,did,'REVIEW_IMPORTED_LEDGER',request['case_id'],request)
        if previous:return previous
        demo=_workspace(con,did,writing=True);row=case(con,did,request['case_id']);require_revision(row,request)
        if request['reviewed_through']!=demo['reference_at']:raise CommandError('PREVIEW_CHANGED')
        if request.get('complete') is not True or request.get('confirm') is not True:raise CommandError('EXPLICIT_CONFIRMATION_REQUIRED',422)
        con.execute('UPDATE cases SET ledger_complete=1,case_revision=case_revision+1,evidence_revision=evidence_revision+1,review_epoch=review_epoch+1 WHERE id=?',(row['id'],))
        con.execute('INSERT INTO intake_ledger_reviews VALUES (?,?,?,?,?,?)',
                    (str(uuid4()),did,row['id'],demo['reference_at'],request['operation_id'],instant(utcnow())))
        append_event(con,row,'APPROVAL_INVALIDATED',request['operation_id'],{'reason':'LEDGER_REVIEWED'})
        append_event(con,row,'LEDGER_REVIEWED',request['operation_id'],dict(reviewed_through=demo['reference_at'],complete=True))
        return save_receipt(con,did,'REVIEW_IMPORTED_LEDGER',row['id'],request,'REVIEWED',revision=row['case_revision']+1,demonstration_id=did,case_revisions=_revisions(con,did))


def intake_overview(db,did):
    with db.connection() as con:
        con.execute('BEGIN');demo=_workspace(con,did)
        invoices=[]
        for record in con.execute('SELECT * FROM intake_invoices WHERE demonstration_id=? ORDER BY invoice_id',(did,)):
            data=json.loads(record['data_json']);data['case_id']=record['case_id'];invoices.append(data)
        cases=[]
        for row in con.execute('SELECT * FROM cases WHERE demonstration_id=? ORDER BY catalogue_case_id',(did,)):
            invoice=next(i for i in invoices if i['case_id']==row['id'])
            paid=con.execute('SELECT coalesce(sum(amount_minor),0) FROM intake_allocations WHERE demonstration_id=? AND case_id=?',(did,row['id'])).fetchone()[0]
            review=con.execute('SELECT reviewed_through FROM intake_ledger_reviews WHERE demonstration_id=? AND case_id=? ORDER BY rowid DESC LIMIT 1',(did,row['id'])).fetchone()
            cases.append(dict(id=row['id'],invoice_id=row['invoice_id'],client=row['client'],case_revision=row['case_revision'],
                ledger_complete=bool(row['ledger_complete']),reviewed_through=review[0] if review and row['ledger_complete'] else None,
                invoice_minor=str(invoice['amount_minor']),allocated_minor=str(paid),remaining_minor=str(invoice['amount_minor']-paid)))
        payments=[]
        for row in con.execute('SELECT * FROM intake_payments WHERE demonstration_id=? ORDER BY rowid',(did,)):
            data=json.loads(row['data_json']);allocations=[]
            for item in con.execute('SELECT * FROM intake_allocations WHERE demonstration_id=? AND payment_id=? ORDER BY rowid',(did,row['id'])):
                invoice=next(i for i in invoices if i['case_id']==item['case_id'])
                allocations.append(dict(id=item['id'],case_id=item['case_id'],invoice_id=invoice['invoice_id'],amount_minor=str(item['amount_minor'])))
            used=sum(int(a['amount_minor']) for a in allocations)
            payments.append(data | dict(id=row['id'],amount_minor=str(row['amount_minor']),remaining_minor=str(row['amount_minor']-used),
                                        allocations=allocations,candidates=suggest_invoices(data,invoices),batch_id=row['batch_id']))
        documents=[dict(r,extraction=json.loads(r['extraction_json'])) for r in con.execute('SELECT * FROM intake_documents WHERE demonstration_id=? ORDER BY rowid',(did,))]
        for document in documents:document.pop('extraction_json')
        files=[dict(r) for r in con.execute('SELECT id,kind,filename,created_at FROM intake_batches WHERE demonstration_id=? ORDER BY rowid',(did,))]
        customers=[json.loads(r[0]) for r in con.execute('SELECT data_json FROM intake_customers WHERE demonstration_id=? ORDER BY customer_id',(did,))]
        from promisekeeper.application.sender_review import needs_sender_review
        return dict(schema_version='1',demonstration_id=did,as_of=demo['reference_at'],customers=customers,cases=cases,needs_sender_review=needs_sender_review(con,did),
                    payments=payments,documents=documents,files=files,scope_revision=_state(con,did))


def original_import(db,did,bid):
    with db.connection() as con:
        _workspace(con,did)
        row=con.execute('SELECT id,kind,filename,content,created_at FROM intake_batches WHERE demonstration_id=? AND id=?',(did,bid)).fetchone()
        if row is None:raise CommandError('NOT_FOUND',404)
        return dict(schema_version='1',**dict(row))
