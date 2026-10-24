"""Evaluation-only frozen inventory and independent saved-finding checks.

No production DTO validator, lifecycle selector or findings derivation is used
here. Identity equality supplies soundness/completeness; captured records supply
exact citation and observation evidence even for an empty expected inventory.
"""
import hashlib
import json
from pathlib import Path
import re
from uuid import UUID

INVENTORY_VERSION = 'gate-iii-findings-1'
INVENTORY_HASH = '78867b575bc69b0f1ee8ce4783ecd9264d1678deb8d6fb6a0c0469e97bad3632'
CANONICAL_MANIFEST_HASH = '17bcb26aa33ae4bab8fd37abf7e2260cda1089d47eaedc9bc67e7b89f38e1f81'
FINDINGS_PROFILE = 'deterministic-1'
INVENTORY_PATH = Path(__file__).resolve().parents[3]/'tests'/'evaluations'/'expected_findings.json'
COLLECTIONS = ('contradictions','unresolved_questions','financial_issues','commitment_issues','evidence_observations')
CHECKS = ('findings_source_validation_correct','findings_soundness_correct',
          'findings_completeness_correct','findings_duplicates_correct')


def _hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()


def load_inventory(definitions):
    raw=INVENTORY_PATH.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=INVENTORY_HASH:
        raise ValueError('Expected finding inventory bytes differ from reviewed pin')
    inventory=json.loads(raw)
    ids=[e['id'] for e in definitions]
    if (inventory['inventory_version']!=INVENTORY_VERSION or inventory['catalogue_version']!='release-0.1'
            or inventory['manifest_definitions']!=definitions or _hash(definitions)!=CANONICAL_MANIFEST_HASH
            or inventory['manifest_hash']!=CANONICAL_MANIFEST_HASH or len(ids)!=51 or len(set(ids))!=51
            or set(inventory['entries'])!=set(ids)
            or any(set(item)!=set(COLLECTIONS) for item in inventory['entries'].values())):
        raise ValueError('Expected finding inventory/manifest identity mismatch')
    return inventory


def _identity(item, collection, *, expected=False):
    if collection=='evidence_observations':
        source=item['source_id'] if expected else (item['source']['source_id'] if item['source'] else None)
        # JSON encoding preserves the distinction between true and 1.
        return item['subject'],item['field'],json.dumps(item['value'],ensure_ascii=False),source
    key='kind' if collection=='contradictions' else 'field' if collection=='unresolved_questions' else 'code'
    sources=item['sources'] if expected or collection.endswith('issues') else [s['source_id'] for s in item['sources']]
    return item[key],tuple(sorted(sources))


def findings_view(result):
    """Keep saved actual arrays separate from candidate and policy evidence."""
    return {key:(result['financial_facts']['issues'] if key=='financial_issues' else result[key]) for key in COLLECTIONS}


def score_findings(result, packet, expected):
    checks=dict.fromkeys(CHECKS,True)
    try:
        actual=findings_view(result)
        identities={key:[_identity(item,key) for item in actual[key]] for key in COLLECTIONS}
        wanted={key:{_identity(item,key,expected=True) for item in expected[key]} for key in COLLECTIONS}
        checks['findings_soundness_correct']=all(set(identities[key])<=wanted[key] for key in COLLECTIONS)
        checks['findings_completeness_correct']=all(wanted[key]<=set(identities[key]) for key in COLLECTIONS)
        checks['findings_duplicates_correct']=all(len(items)==len(set(items)) for items in identities.values())

        def require(condition):
            if not condition:raise ValueError('Invalid captured provenance')

        UUID(packet['snapshot_id'])
        require(isinstance(packet['snapshot_hash'],str) and re.fullmatch('[0-9a-f]{64}',packet['snapshot_hash']) is not None)
        require(result['snapshot_id']==packet['snapshot_id'] and result['snapshot_hash']==packet['snapshot_hash'])
        require(result['findings_version']==FINDINGS_PROFILE)
        records={r['id']:r for r in packet['evidence']}
        require(len(records)==len(packet['evidence']))
        for record in records.values():
            UUID(record['id'])

        def reference(ref):
            UUID(ref['evidence_version_id'])
            record=records[ref['evidence_version_id']]
            require(ref['source_id']==record['stable_source_id'])
            return record

        def span(ref):
            record=reference(ref);start,end=ref['start'],ref['end'];text=record['original_content']
            require(record['availability']=='AVAILABLE' and type(start) is int and type(end) is int
                    and 0<=start<end<=len(text) and isinstance(ref['quote'],str)
                    and bool(ref['quote']) and text[start:end]==ref['quote'])

        for key in ('contradictions','unresolved_questions'):
            for item in actual[key]:
                refs=item['sources'];ids=[ref['source_id'] for ref in refs]
                require(len(refs)==(2 if key=='contradictions' else 1) and len(ids)==len(set(ids)))
                for ref in refs:span(ref)
        for key in ('financial_issues','commitment_issues'):
            for item in actual[key]:
                sources=item['sources'];refs=item['source_versions']
                require(len(sources)==len(set(sources)))
                expected_refs={(r['stable_source_id'],r['id']) for r in records.values() if r['stable_source_id'] in sources}
                actual_refs=[(ref['source_id'],ref['evidence_version_id']) for ref in refs]
                require(len(actual_refs)==len(set(actual_refs)) and set(actual_refs)==expected_refs
                        and set(sources)=={sid for sid,_ in expected_refs})
                for ref in refs:reference(ref)
        # Check any other saved source projections as well, without normalizing
        # a DTO or trusting the production validator to establish ownership.
        for key in ('commitments','claims','timeline'):
            for item in result.get(key,[]):reference(item)

        require(packet['ledger_availability'] in {'AVAILABLE','UNAVAILABLE','MISSING','UNREADABLE'} and type(packet['ledger_complete']) is bool)
        observed=[]
        for item in actual['evidence_observations']:
            require(item['snapshot_id']==packet['snapshot_id'] and item['snapshot_hash']==packet['snapshot_hash'])
            subject,field,value=item['subject'],item['field'],item['value']
            if subject=='LEDGER':
                require(item['source'] is None and field in {'availability','complete'})
                require((field=='availability' and type(value) is str and value==packet['ledger_availability'])
                        or (field=='complete' and type(value) is bool and value==packet['ledger_complete']))
            else:
                require(subject=='SOURCE' and item['source'] is not None)
                record=reference(item['source'])
                require((field=='availability' and type(value) is str and value==record['availability'] and value!='AVAILABLE')
                        or (field=='content_present' and type(value) is bool and value is False and not record['original_content']))
            observed.append(_identity(item,'evidence_observations'))
        # Completeness of metadata is checked against the packet too. A forged
        # expected empty collection cannot waive mandatory snapshot observations.
        metadata=[('LEDGER','availability',json.dumps(packet['ledger_availability']),None),
                  ('LEDGER','complete',json.dumps(packet['ledger_complete']),None)]
        for record in records.values():
            if record['availability']!='AVAILABLE':metadata.append(('SOURCE','availability',json.dumps(record['availability']),record['stable_source_id']))
            if not record['original_content']:metadata.append(('SOURCE','content_present','false',record['stable_source_id']))
        require(set(observed)==set(metadata))
    except (KeyError,ValueError,TypeError,AttributeError,OverflowError):
        checks['findings_source_validation_correct']=False
        # If malformed identities prevented comparison, all checks fail closed.
        if 'identities' not in locals() or 'wanted' not in locals():return dict.fromkeys(CHECKS,False)
    return checks
