"""Exercise public HTTP boundaries with explicit STUB agents and real persistence."""
from datetime import datetime, timedelta
from email.utils import format_datetime
import time
from uuid import uuid4
from zoneinfo import ZoneInfo

HEADERS = {'X-PromiseKeeper-Request': '1'}


def command(**fields):
    return dict(schema_version='1', operation_id=str(uuid4()), **fields)


class Workflow:
    def __init__(self, client):
        self.client = client
        self.today = datetime.now(ZoneInfo('Asia/Kolkata')).date()
        self.values = {}
        for name, days in [('past', -5), ('future', 10), ('future2', 11), ('issued', -90), ('due', -30)]:
            day = self.today + timedelta(days=days)
            self.values[name+'_iso'] = day.isoformat()
            self.values[name+'_long'] = f'{day.day} {day:%B %Y}'

    def post(self, path, body, expected=200):
        response = self.client.post('/api/v1'+path, json=body, headers=HEADERS)
        if expected is not None and response.status_code != expected:
            raise RuntimeError(f'{path}: expected HTTP {expected}, got {response.status_code}: {response.text}')
        return response

    def get(self, path):
        response = self.client.get('/api/v1'+path)
        if response.status_code != 200:
            raise RuntimeError(f'{path}: HTTP {response.status_code}: {response.text}')
        return response.json()

    def preview(self, kind, text, did=None, **extra):
        if kind in {'whatsapp','customer_email','remittance_email'}:extra.setdefault('sender_role','CUSTOMER')
        body = command(kind=kind, filename='held-out.eml' if 'email' in kind else 'held-out.txt' if kind=='whatsapp' else 'held-out.csv',
                       content=text.format(**self.values), demonstration_id=did, **extra)
        return body, self.post('/intake/previews', body).json()

    def commit_body(self, body, preview):
        return body | dict(operation_id=str(uuid4()), confirmed_preview_hash=preview['preview_hash'],
                           confirm=True, fictional_data=True, settled_confirmed=True)

    def upload(self, kind, text, did=None, **extra):
        body, preview = self.preview(kind, text, did, **extra)
        if preview['errors']:
            raise RuntimeError('Fixture setup rejected: '+str(preview['errors']))
        body = self.commit_body(body, preview)
        return self.post('/intake/commits', body).json(), body

    def workspace(self):
        saved, _ = self.upload('customers', 'customer_id,customer_name,customer_alias,address\nEVAL,Econcity Private Limited,econ,12 Gandhinagar Bangalore 560012\n')
        did = saved['demonstration_id']
        self.upload('invoices', 'invoice_id,customer_id,amount,currency,issued_at,due_at\nEV-101,EVAL,1000,INR,{issued_iso},{due_iso}\n', did)
        return did, self.state(did)['cases'][0]['id']

    def state(self, did):
        return self.get(f'/demonstrations/{did}/intake')

    def view(self, did, cid):
        return self.get(f'/cases/{cid}?demonstration_id={did}')

    def receipt(self, did, amount='500', status='SETTLED', ref='HELD-T1'):
        self.upload('payments', f'transaction_ref,payer_name,payer_alias,address,amount,currency,paid_at,invoice_reference,status\n{ref},Econ Private Limited,ECONC,12 Gandhinagar KR Puram Bangalore 560012,{amount},INR,{{past_iso}},EV-101,{status}\n', did)
        return next(p for p in self.state(did)['payments'] if p['transaction_ref']==ref)

    def allocate(self, did, cid, payment, amount, revision=None, settled=True):
        body = command(payment_id=payment['id'], case_id=cid, amount_text=amount,
                       expected_case_revision=revision or self.view(did,cid)['case_revision'], confirm=True, settled_confirmed=settled)
        return self.post(f'/demonstrations/{did}/intake/allocations', body, expected=None), body

    def cover(self, did, cid):
        self.post(f'/demonstrations/{did}/intake/ledger-reviews', command(case_id=cid,
            expected_case_revision=self.view(did,cid)['case_revision'], reviewed_through=self.state(did)['as_of'], complete=True, confirm=True))

    def investigate(self, did, cid):
        started=self.post(f'/cases/{cid}/investigations?demonstration_id={did}', command(
            expected_case_revision=self.view(did,cid)['case_revision'], retry_of=None), 202).json()
        deadline = time.monotonic()+60
        while time.monotonic()<deadline:
            view = self.view(did,cid)
            if view['current_result'] is not None and not view.get('active_investigation'):
                return view
            attempt=self.get(f"/investigations/{started['investigation_id']}?demonstration_id={did}")
            if attempt['status']=='INCOMPLETE':
                view['_eval_failed_attempt']=dict(status=attempt['status'],failure_code=attempt.get('failure_code'))
                return view
            time.sleep(.02)
        raise RuntimeError('Saved investigation result unavailable within 60s')

    def observations(self, view):
        result = view['current_result']
        if result is None:
            if '_eval_failed_attempt' in view:
                return dict(attempt=view['_eval_failed_attempt'],lifecycle=view['lifecycle'],review_count=len(view['draft_reviews']))
            raise RuntimeError('No saved result')
        balance = result['financial_facts']['balance']
        return dict(balance_minor=balance['minor_units'] if balance else None,
                    currency=balance['currency'] if balance else None,
                    action=result['action'], status=result['status'], reason_code=result['reason_code'],
                    lifecycle=view['lifecycle'], review_count=len(view['draft_reviews']),
                    review_state=view['review_state'], claims=result['claims'],
                    commitment_issues=result['commitment_issues'])

    def document(self, text, sender=None, kind='whatsapp'):
        instant = datetime.combine(self.today-timedelta(days=1), datetime.min.time(), ZoneInfo('Asia/Kolkata'))
        sender = sender or 'accounts@econ.example'
        if 'email' in kind:
            return f'From: {sender}\nDate: {format_datetime(instant)}\nContent-Type: text/plain; charset=utf-8\nSubject: Invoice EV-101\n\n{text}\n'
        return f'Sender: {sender}\nSent: {instant.isoformat()}\n{text}\n'

    def message(self, case):
        did,cid = self.workspace()
        if case.get('receipt'):
            payment = self.receipt(did,case['receipt'])
            if case.get('allocate'):
                response,_ = self.allocate(did,cid,payment,case['allocate'])
                if response.status_code!=200: raise RuntimeError(response.text)
        kind = case.get('doc_kind','whatsapp')
        before = self.state(did)
        body, preview = self.preview(kind,self.document(case['text'],case.get('sender'),kind),did,
                                     case_id=cid,context_only=case.get('context_only',False),sender_role=case.get('sender_role','CUSTOMER'))
        response = self.post('/intake/commits', self.commit_body(body,preview), expected=None)
        accepted = not preview['errors'] and response.status_code==200
        if preview['errors'] and response.status_code!=422:
            raise RuntimeError('Invalid preview commit did not return 422: '+response.text)
        if not preview['errors'] and response.status_code!=200: raise RuntimeError(response.text)
        atomic = accepted or before==self.state(did)
        self.cover(did,cid)
        actual = self.observations(self.investigate(did,cid))
        return actual | dict(accepted=accepted,atomic=atomic,preview_errors=preview['errors'],
                            extraction=preview.get('extraction'),commit_status=response.status_code)

    def import_case(self, case):
        did,_ = self.workspace(); before=self.state(did)
        body,preview=self.preview(case['import_kind'],case['content'],did)
        response=self.post('/intake/commits',self.commit_body(body,preview),expected=None)
        accepted=not preview['errors'] and response.status_code==200
        if response.status_code not in {200,422}:raise RuntimeError(response.text)
        return dict(accepted=accepted,atomic=accepted or self.state(did)==before,
                    preview_errors=preview['errors'],commit_status=response.status_code)

    def allocation(self, case):
        did,cid=self.workspace(); name=case['scenario']
        status={'pending':'PENDING','reversed':'REVERSED','unknown':'UNKNOWN','unknown_unconfirmed':'UNKNOWN'}.get(name,'SETTLED')
        payment=self.receipt(did,'1500' if name=='over_invoice' else '500',status)
        # Hints are suggestions only; the import must not assign funds itself.
        if payment['allocations']:raise RuntimeError('Receipt import allocated without the owner')
        if name=='wrong_workspace':
            other,other_cid=self.workspace(); response,_=self.allocate(other,other_cid,payment,'400')
        else:
            response,body=self.allocate(did,cid,payment,{'over_receipt':'501','over_invoice':'1001'}.get(name,'400'),settled=name!='unknown_unconfirmed')
        replay_equal=True
        if name=='duplicate':
            replay=self.post(f'/demonstrations/{did}/intake/allocations',body)
            replay_equal=replay.json()==response.json()
        if response.status_code not in {200,404,409,422}:raise RuntimeError(response.text)
        self.cover(did,cid)
        return self.observations(self.investigate(did,cid)) | dict(accepted=response.status_code==200,
            remaining_minor=self.state(did)['payments'][0]['remaining_minor'],replay_equal=replay_equal,
            http_status=response.status_code)

    def workflow(self, case):
        did,cid=self.workspace(); name=case['scenario']; detail={}
        if name=='sender_role_preview':
            before=self.state(did)
            body,p=self.preview('whatsapp',self.document('We will pay INR 1000 by {future_long}.'),did,case_id=cid,sender_role='CUSTOMER')
            changed=self.commit_body(body,p)|dict(sender_role='OWNER',context_only=True)
            response=self.post('/intake/commits',changed,expected=None)
            ok=response.status_code==409 and self.state(did)==before
        elif name=='bank_overlap':
            self.upload('payments','Date,Description,Credit\n{past_iso},Econ transfer,500\n',did)
            before=self.state(did)
            body,p=self.preview('payments','Date,Description,Credit,Reference\n{past_iso},Econ transfer,500,REAL-123\n',did)
            response=self.post('/intake/commits',self.commit_body(body,p),expected=None)
            ok=bool(p['errors']) and response.status_code==422 and self.state(did)==before
        elif name in {'preview_read_only','commit_replay','changed_preview'}:
            before=self.state(did)
            body,p=self.preview('payments','transaction_ref,amount,currency,paid_at\nHELD-T1,500,INR,{past_iso}\n',did)
            unchanged=self.state(did)==before
            commit=self.commit_body(body,p)
            if name=='preview_read_only':ok=unchanged
            elif name=='commit_replay':
                first=self.post('/intake/commits',commit).json(); saved=self.state(did)
                second=self.post('/intake/commits',commit).json()
                ok=unchanged and first==second and self.state(did)==saved
            else:
                self.receipt(did,ref='OTHER-1'); saved=self.state(did)
                response=self.post('/intake/commits',commit,expected=None)
                ok=unchanged and response.status_code==409 and self.state(did)==saved
        elif name in {'cross_scope','deletion_scope'}:
            other,other_cid=self.workspace(); before=self.state(other)
            if name=='cross_scope':
                response=self.client.get(f'/api/v1/cases/{cid}?demonstration_id={other}')
                ok=response.status_code==404 and self.state(other)==before
            else:
                self.post(f'/demonstrations/{did}/deletion',command(confirmed_demonstration_id=did,confirm=True))
                response=self.client.get(f'/api/v1/demonstrations/{did}/intake')
                ok=response.status_code==404 and self.state(other)==before
        elif name=='stale_revision':
            revision=self.view(did,cid)['case_revision'];payment=self.receipt(did)
            before=self.state(did);response,_=self.allocate(did,cid,payment,'400',revision)
            ok=response.status_code==409 and before==self.state(did)
        elif name=='stale_approval':
            self.upload('whatsapp',self.document('We will pay INR 1000 by {past_long}.'),did,case_id=cid)
            self.cover(did,cid);view=self.investigate(did,cid);draft=view['draft']
            if not draft:raise RuntimeError('Expected follow-up draft unavailable')
            review=command(expected_case_revision=view['case_revision'],draft_version_id=draft['id'],
                payload_hash=draft['payload_hash'],expected_review_epoch=view['review_epoch'],decision='APPROVE')
            self.post(f'/cases/{cid}/draft-reviews?demonstration_id={did}',review)
            approved=self.view(did,cid)
            self.receipt(did);stale=self.view(did,cid)
            response=self.post(f'/cases/{cid}/draft-reviews?demonstration_id={did}',review | {'operation_id':str(uuid4())},expected=None)
            ok=approved['review_state']=='APPROVED' and stale['review_state']!='APPROVED' and response.status_code==409
            detail=dict(approved=approved['review_state'],after_evidence=stale['review_state'],stale_response=response.status_code)
        elif name=='close_requires_owner':
            payment=self.receipt(did,'1000');response,_=self.allocate(did,cid,payment,'1000')
            if response.status_code!=200:raise RuntimeError(response.text)
            self.upload('whatsapp',self.document('We paid INR 1000 on {past_long}. UTR: HELD-T1.'),did,case_id=cid)
            self.cover(did,cid);view=self.investigate(did,cid);result=view['current_result']
            response=self.post(f'/cases/{cid}/closure?demonstration_id={did}',command(expected_case_revision=view['case_revision'],
                investigation_id=result['investigation_id'],confirmed_result_hash=result['result_hash'],confirm=False),expected=None)
            ready=self.view(did,cid);result=ready['current_result']
            self.post(f'/cases/{cid}/closure?demonstration_id={did}',command(expected_case_revision=ready['case_revision'],
                investigation_id=result['investigation_id'],confirmed_result_hash=result['result_hash'],confirm=True))
            ok=view['lifecycle']=='OPEN' and response.status_code==422 and ready['lifecycle']=='OPEN' and self.view(did,cid)['lifecycle']=='CLOSED'
            detail=dict(before_owner=ready['lifecycle'],recommendation=result['action'],after_owner=self.view(did,cid)['lifecycle'])
        else:raise ValueError('Unknown workflow scenario: '+name)
        return dict(invariant=ok,detail=detail)
