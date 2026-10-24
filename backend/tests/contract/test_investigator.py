from copy import deepcopy
from uuid import uuid4
import pytest
from promisekeeper.agents.protocol import InvestigatorFailure
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.agents.validation import validate_output
from promisekeeper.application.cases import create_demonstration
from promisekeeper.application.start_investigation import start_investigation, finish_incomplete
from promisekeeper.persistence.sqlite import Database
from promisekeeper.tools.evidence import read_snapshot,snapshot_case

def packet_for(db, variant=None, case_id='PK-001'):
    did=create_demonstration(db,dict(schema_version='1',operation_id=str(uuid4()),catalogue_version='release-0.1',variant_id=variant,clock_mode='REFERENCE'))['demonstration_id']
    with db.connection() as con: cid=con.execute('SELECT id FROM cases WHERE demonstration_id=? AND catalogue_case_id=?',(did,case_id)).fetchone()[0]
    started=start_investigation(db,did,cid,dict(schema_version='1',operation_id=str(uuid4()),expected_case_revision=0,retry_of=None))
    with db.connection() as con:
        import json
        raw=json.loads(con.execute('SELECT packet_json FROM evidence_snapshots WHERE id=?',(started['snapshot_id'],)).fetchone()[0])
    packet=read_snapshot(db,dict(schema_version='1',snapshot_id=started['snapshot_id'],evidence_version_ids=[r['id'] for r in raw['evidence']]))
    return started,packet

@pytest.mark.parametrize('mutation',[
    lambda o:o.update(action='CLOSE'),
    lambda o:o.update(snapshot_id=str(uuid4())),
    lambda o:o['commitments'][0].pop('commitment_key'),
    lambda o:o['commitments'][0].update(commitment_key='foreign'),
    lambda o:o['commitments'][0]['source'].update(source_id='foreign'),
    lambda o:o['commitments'][0]['source'].update(evidence_version_id=str(uuid4())),
    lambda o:o['commitments'][0]['source'].update(start=True),
    lambda o:o['commitments'][0]['source'].update(end=99999),
    lambda o:o['commitments'][0]['source'].update(quote='fabricated'),
    lambda o:o['commitments'][0].update(amount_text='1'),
    lambda o:o['commitments'][0].update(date_text='tomorrow'),
    lambda o:o['commitments'][0].update(speaker='Someone else'),
    lambda o:o['commitments'].append(deepcopy(o['commitments'][0])),
    lambda o:o.update(commitments=[]),
    lambda o:o['commitments'][0].update(explicitly_replaces_source_id='foreign'),
])
def test_invalid_authority_provenance_tokens_and_empty_output_fail(tmp_path,mutation):
    with Database(tmp_path/'db.sqlite') as db:
        started,p=packet_for(db)
        out=ScriptedInvestigator().extract(dict(snapshot_id=p['snapshot_id'],packet=p),timeout=20).output
        mutation(out)
        with pytest.raises(InvestigatorFailure,match='INVALID_INVESTIGATOR_OUTPUT'): validate_output(out,p,snapshot_case(p))
        finish_incomplete(db,started['investigation_id'],'TEST')

def test_snapshot_lookup_rejects_foreign_ids_and_extra_tools(tmp_path):
    with Database(tmp_path/'db.sqlite') as db:
        started,p=packet_for(db)
        for request in [dict(schema_version='1',snapshot_id=p['snapshot_id'],evidence_version_ids=[str(uuid4())]),dict(schema_version='1',snapshot_id=p['snapshot_id'],evidence_version_ids=[],path='/etc/passwd')]:
            with pytest.raises(InvestigatorFailure):read_snapshot(db,request)
        # Exact Unicode spans use Python code points; output cannot coerce offsets.
        assert all('candidate' not in r['data'] for r in p['evidence'])
        finish_incomplete(db,started['investigation_id'],'TEST')

@pytest.mark.parametrize('lengths,accepted',[
    pytest.param([1]*64,True,id='64-records'),
    pytest.param([1]*65,False,id='65-records'),
    pytest.param([8000],True,id='8000-code-points'),
    pytest.param([8001],False,id='8001-code-points'),
    pytest.param([8000]*8,True,id='64000-total-code-points'),
    pytest.param([8000]*8+[1],False,id='64001-total-code-points'),
])
def test_snapshot_packet_limits_accept_exact_bounds_and_reject_overflow(tmp_path,lengths,accepted):
    import json
    from promisekeeper.application.operations import digest
    with Database(tmp_path/'db.sqlite') as db:
        started,original=packet_for(db)
        finish_incomplete(db,started['investigation_id'],'TEST')
        with db.connection() as con:
            row=con.execute('SELECT * FROM evidence_snapshots WHERE id=?',(started['snapshot_id'],)).fetchone()
        packet=json.loads(row['packet_json'])
        template=next(r for r in original['evidence'] if r['kind']=='MESSAGE')
        records=[]
        for index,length in enumerate(lengths):
            record=deepcopy(template)
            record.update(id=str(uuid4()),stable_source_id=f'BOUNDARY-{index}',
                original_content='\U0001f600'*length,commitment_anchors=[])
            records.append(record)
        packet['evidence']=records
        snapshot_id=str(uuid4())
        # Seed an oversized immutable packet directly to test the reader boundary;
        # the public API still accepts only registered fictional catalogue records.
        with db.transaction() as con:
            con.execute('INSERT INTO evidence_snapshots VALUES (?,?,?,?,?,?,?)',
                (snapshot_id,row['demonstration_id'],row['case_id'],row['evidence_revision'],
                 row['captured_at'],json.dumps(packet,ensure_ascii=False),digest(packet)))
        request=dict(schema_version='1',snapshot_id=snapshot_id,evidence_version_ids=[r['id'] for r in records])
        if accepted:
            result=read_snapshot(db,request)
            assert result['evidence']==records
            assert [len(r['original_content']) for r in result['evidence']]==lengths
        else:
            with pytest.raises(InvestigatorFailure,match='SNAPSHOT_PACKET_TOO_LARGE'):
                read_snapshot(db,request)

def test_fv16_both_quotes_bind_identical_anchor_credit_and_balance(tmp_path):
    from promisekeeper.domain.recommendations import recommend
    from datetime import datetime
    with Database(tmp_path/'db.sqlite') as db:
        started,p=packet_for(db,'FV-16-LINKED','PK-002')
        results=[]
        for short in [False,True]:
            out=ScriptedInvestigator(short_quotes=short).extract(dict(snapshot_id=p['snapshot_id'],packet=p),timeout=20)
            _,extraction=validate_output(out.output,p,snapshot_case(p))
            results.append(recommend(snapshot_case(p),extraction,datetime.fromisoformat(started['evaluation_at'])))
        assert results[0]==results[1]
        assert results[0].financial.balance_minor==3000000
        assert results[0].commitments[0].id is not None
        finish_incomplete(db,started['investigation_id'],'TEST')

def test_commitment_result_amounts_reject_non_money_authority():
    from pydantic import ValidationError
    from promisekeeper.contracts.investigations import CommitmentView
    base=dict(commitment_stable_id=None,commitment_key=None,source_id='source',evidence_version_id=str(uuid4()),amount=None,expires_at=None,fulfilled=False,fulfillment_unresolved=True,credited=dict(currency='INR',minor_units='0'),superseded=False)
    for changed in [base|dict(amount={'minor_units':1}),base|dict(credited={'currency':'USD','minor_units':'3.14'})]:
        with pytest.raises(ValidationError):CommitmentView.model_validate(changed)
