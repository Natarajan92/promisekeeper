"""Validate candidate syntax, provenance, tokens and catalogue anchor binding."""
from promisekeeper.contracts.investigations import CandidateOnlyOutput
from promisekeeper.domain.evidence import Extraction, CommitmentCandidate, ClaimCandidate
from promisekeeper.domain.commitments import reconcile_commitments
from promisekeeper.domain.payments import reconcile_payments
from promisekeeper.agents.protocol import InvestigatorFailure
from pydantic import ValidationError

def validate_output(raw, packet, case):
    try:
        # The versioned candidate-only policy is enforced by the same strict
        # zero-length findings arrays for both STUB and LIVE responses.
        output = CandidateOnlyOutput.model_validate_json(raw) if isinstance(raw,str) else CandidateOnlyOutput.model_validate(raw)
        if output.snapshot_id != packet['snapshot_id']: raise ValueError('Snapshot mismatch')
        records = {r['id']:r for r in packet['evidence']}
        # The same bounded intake rules constrain uploaded evidence for every
        # provider. A LIVE extractor cannot turn a legacy/conditional document
        # into an active customer promise by returning an otherwise valid span.
        for record in records.values():
            if record['kind']=='MESSAGE' and record['availability']=='AVAILABLE' and '-UPLOAD-CUSTOMER-' in record['stable_source_id']:
                import re
                from promisekeeper.domain.document_extraction import extract_document
                content=record['original_content']
                kind='customer_email' if re.search(r'^From:',content,re.M|re.I) and re.search(r'^Date:',content,re.M|re.I) else 'whatsapp'
                extract_document(content,kind,event_at=record['event_at'],sender_role='CUSTOMER')
        domain_sources = {m.source.id:m.source for m in case.messages}
        seen=set()
        def span(s):
            r=records.get(s.evidence_version_id)
            if r is None or r['stable_source_id'] != s.source_id or r['availability'] != 'AVAILABLE': raise ValueError('Foreign/unavailable source')
            if not 0<=s.start<s.end<=len(r['original_content']) or r['original_content'][s.start:s.end] != s.quote: raise ValueError('Invalid quote')
            return r
        commitments,claims=[],[]
        for candidate,kind in [(c,'commitment') for c in output.commitments]+[(c,'claim') for c in output.payment_claims]:
            if candidate.candidate_id in seen: raise ValueError('Duplicate candidate ID')
            seen.add(candidate.candidate_id)
            r=span(candidate.source)
            from uuid import UUID
            source=domain_sources.get(UUID(r['id']))
            if source is None: raise ValueError('Candidate is not a message')
            common=dict(source=source,start=candidate.source.start,end=candidate.source.end,quote=candidate.source.quote,
                speaker=candidate.speaker,amount_text=candidate.amount_text,currency_text=candidate.currency_text)
            if kind=='commitment':
                if candidate.explicitly_replaces_source_id is not None and candidate.explicitly_replaces_source_id not in {r['stable_source_id'] for r in records.values()}: raise ValueError('Foreign replacement')
                commitments.append(CommitmentCandidate(**common,commitment_key=candidate.commitment_key,date_text=candidate.date_text,explicitly_replaces_source_id=candidate.explicitly_replaces_source_id))
            else: claims.append(ClaimCandidate(**common,payment_date_text=candidate.payment_date_text,transaction_reference_text=candidate.transaction_reference_text))
        for item in [*output.contradictions,*output.unresolved]:
            for s in item.sources: span(s)
        extraction=Extraction(tuple(commitments),tuple(claims))
        reconcile_commitments(case,extraction,reconcile_payments(case))
        reviewed_context_only=bool(case.messages) and all('-UPLOAD-CONTEXT-' in m.source.source_id for m in case.messages)
        if case.messages and not commitments and not claims and not reviewed_context_only: raise ValueError('Empty fabricated extraction')
        return output,extraction
    except (ValueError,KeyError,TypeError,ValidationError) as exc:
        raise InvestigatorFailure('INVALID_INVESTIGATOR_OUTPUT') from exc
