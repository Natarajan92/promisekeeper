"""STUB adapter for approved fixtures and bounded uploaded text; never money authority."""
from functools import lru_cache
import re
from promisekeeper.agents.protocol import AgentResponse, InvestigatorFailure
from promisekeeper.fixtures.catalogue import fresh_copy, variant_ids, apply_event, _event_table

@lru_cache(maxsize=1)
def _approved():
    candidates={}
    def collect(fixture):
        for item in fixture.cases.values():
            for kind,values in [('commitment',item.extraction.commitments),('claim',item.extraction.claims)]:
                for c in values: candidates[(c.source.source_id,c.source.original_content)]=(kind,c)
    for variant in [None,*variant_ids()]:
        f=fresh_copy(variant);collect(f)
        for event in _event_table(variant):
            try: collect(apply_event(f,event))
            except ValueError: pass
    return candidates

class ScriptedInvestigator:
    def __init__(self, behavior='approved', *, short_quotes=False):
        self.behavior=behavior;self.short_quotes=short_quotes
        self.calls=0

    def extract(self, request, *, timeout):
        self.calls+=1
        if self.behavior in {'timeout','unavailable','transient_once'} and (self.behavior!='transient_once' or self.calls==1):
            raise InvestigatorFailure('INVESTIGATOR_TIMEOUT' if self.behavior=='timeout' else 'INVESTIGATOR_UNAVAILABLE',transient=True)
        if self.behavior=='refusal': raise InvestigatorFailure('INVESTIGATOR_REFUSAL')
        if self.behavior=='malformed': return AgentResponse('{')
        result=dict(schema_version='1',snapshot_id=request['snapshot_id'],commitments=[],payment_claims=[],contradictions=[],unresolved=[])
        for r in request['packet']['evidence']:
            if r['kind']!='MESSAGE' or r['availability']!='AVAILABLE': continue
            if '-UPLOAD-CONTEXT-' in r['stable_source_id']:
                continue
            if '-UPLOAD-' in r['stable_source_id']:
                from promisekeeper.domain.document_extraction import extract_document
                content=r['original_content']
                kind='customer_email' if re.search(r'^From:',content,re.M|re.I) and re.search(r'^Date:',content,re.M|re.I) else 'whatsapp'
                extracted=extract_document(content,kind,event_at=r['event_at'],sender_role='CUSTOMER' if '-UPLOAD-CUSTOMER-' in r['stable_source_id'] else 'UNVERIFIED')
                for number,entry in enumerate(extracted['candidates'],1):
                    start=content.index(entry['clause']);end=start+len(entry['clause'])
                    span=dict(evidence_version_id=r['id'],source_id=r['stable_source_id'],start=start,end=end,quote=content[start:end])
                    item=dict(candidate_id=f'candidate-{len(result["commitments"])+len(result["payment_claims"])}',source=span,
                              speaker=entry['speaker'],amount_text=entry['amount_text'],currency_text=entry['currency_text'])
                    if entry['kind']=='COMMITMENT':
                        item.update(commitment_key=r['stable_source_id']+f'-C{number}',date_text=entry['date_text'],explicitly_replaces_source_id=None)
                        result['commitments'].append(item)
                    else:
                        item.update(payment_date_text=entry['payment_date_text'],transaction_reference_text=entry['transaction_reference_text'])
                        result['payment_claims'].append(item)
                continue
            approved=_approved().get((r['stable_source_id'],r['original_content']))
            if approved is None: raise InvestigatorFailure('UNREGISTERED_STUB_PACKET')
            kind,c=approved
            start,end=c.start,c.end
            if not self.short_quotes and len(r['commitment_anchors'])<=1: start,end=0,len(r['original_content'])
            span=dict(evidence_version_id=r['id'],source_id=r['stable_source_id'],start=start,end=end,quote=r['original_content'][start:end])
            item=dict(candidate_id=f'candidate-{len(result["commitments"])+len(result["payment_claims"])}',source=span,
                speaker=c.speaker,amount_text=c.amount_text,currency_text=c.currency_text)
            if kind=='commitment':
                item.update(commitment_key=c.commitment_key,date_text=c.date_text,explicitly_replaces_source_id=c.explicitly_replaces_source_id)
                result['commitments'].append(item)
            else:
                item.update(payment_date_text=c.payment_date_text,transaction_reference_text=c.transaction_reference_text)
                result['payment_claims'].append(item)
        return AgentResponse(result)
