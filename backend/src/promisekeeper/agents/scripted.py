"""Explicit STUB adapter using approved candidate packets, never authoritative facts."""
from functools import lru_cache
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
