"""Independent golden outcomes for end-user synthetic upload files."""
from datetime import date
import json
from pathlib import Path
from fastapi.testclient import TestClient
from promisekeeper.api.app import create_app
from promisekeeper.config import Settings
from promisekeeper.fixtures.synthetic_pack import generate_pack
from support.intake import HEADERS, operation, preview, commit, overview, allocate
from support.lifecycle import run


def observed(name,data):
    path=Path(__file__).resolve().parents[3]/'.runtime/synthetic-pack'/name
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


def test_pack_generation_is_deterministic_and_keeps_future_promises_relative(tmp_path):
    a,b=tmp_path/'a',tmp_path/'b'
    left=generate_pack(a,date(2026,10,25));right=generate_pack(b,date(2026,10,25))
    assert left==right
    assert {str(p.relative_to(a)):p.read_bytes() for p in a.rglob('*') if p.is_file()}=={str(p.relative_to(b)):p.read_bytes() for p in b.rglob('*') if p.is_file()}
    assert '1 November 2026' in (a/'04-messages/econ-future-promise.eml').read_text(encoding='utf-8')
    assert len(left['cases'])==6
    assert sum(int(c['remainder_minor']) for c in left['cases'])==23500075


def setup(client,folder,manifest):
    did=None
    for kind,name in [('customers','01-customers.csv'),('invoices','02-invoices.csv'),('payments','03-receipts-initial.csv'),('allocations','03a-existing-allocations.csv'),('allocations','03b-owner-reviewed-allocations.csv')]:
        saved,_=commit(client,kind,(folder/name).read_text(encoding='utf-8'),did)
        did=saved['demonstration_id']
    ids={c['invoice_id']:c['id'] for c in overview(client,did)['cases']}
    for item in manifest['documents']:
        commit(client,item['kind'],(folder/item['path']).read_text(encoding='utf-8'),did,case_id=ids[item['invoice_id']])
    return did,ids


def coverage(client,did):
    for row in overview(client,did)['cases']:
        state=overview(client,did)
        response=client.post(f'/api/v1/demonstrations/{did}/intake/ledger-reviews',json=operation(case_id=row['id'],expected_case_revision=row['case_revision'],reviewed_through=state['as_of'],complete=True,confirm=True),headers=HEADERS)
        assert response.status_code==200,response.text


def test_synthetic_pack_has_independent_balances_and_delayed_claim_resolution(tmp_path):
    from zoneinfo import ZoneInfo
    from datetime import datetime
    folder=tmp_path/'pack';manifest=generate_pack(folder,datetime.now(ZoneInfo('Asia/Kolkata')).date())
    app=create_app(Settings('STUB','scripted',tmp_path/'pack.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did,ids=setup(client,folder,manifest);state=overview(client,did)
        assert len(state['payments'])==9
        assert next(p for p in state['payments'] if p['transaction_ref']=='NOVA-T1')['remaining_minor']=='2000000'
        assert next(p for p in state['payments'] if p['transaction_ref']=='MYSTERY-T1')['candidates']==[]
        coverage(client,did)
        results={}
        for expected in manifest['cases']:
            view=run(app.state.db,did,ids[expected['invoice_id']]);results[expected['invoice_id']]=view['current_result']
            assert view['current_result']['financial_facts']['balance']['minor_units']==expected['remainder_minor']
            assert view['current_result']['action']==expected['action']
            assert view['current_result']['status']=='COMPLETE'
            assert view['lifecycle']=='OPEN'
        # Exact duplicate exports never reduce balances again.
        prior=overview(client,did)
        commit(client,'payments',(folder/'03-receipts-initial.csv').read_text(encoding='utf-8'),did)
        commit(client,'allocations',(folder/'03b-owner-reviewed-allocations.csv').read_text(encoding='utf-8'),did)
        assert overview(client,did)==prior
        old=results['ECON-101']
        commit(client,'payments',(folder/'05-later/receipts-later.csv').read_text(encoding='utf-8'),did)
        state=overview(client,did);payment=next(p for p in state['payments'] if p['transaction_ref']=='ECON-T3')
        row=next(c for c in state['cases'] if c['invoice_id']=='ECON-101')
        response,_=allocate(client,did,payment,row,'60000');assert response.status_code==200,response.text
        coverage(client,did);after=run(app.state.db,did,ids['ECON-101'])
        assert after['current_result']['action']=='CLOSE'
        assert after['current_result']['financial_facts']['balance']['minor_units']=='0'
        assert all(c['resolved'] for c in after['current_result']['claims'])
        historical=client.get(f"/api/v1/investigations/{old['investigation_id']}",params={'demonstration_id':did}).json()
        assert historical['result']==old
        observed('main-results.json',dict(initial={key:dict(action=r['action'],status=r['status'],balance=r['financial_facts']['balance']['minor_units']) for key,r in results.items()},later=dict(action=after['current_result']['action'],balance=after['current_result']['financial_facts']['balance']['minor_units'],lifecycle=after['lifecycle'])))


def test_every_rejected_challenge_has_an_actionable_preview_and_no_writes(tmp_path):
    from zoneinfo import ZoneInfo
    from datetime import datetime
    folder=tmp_path/'pack';manifest=generate_pack(folder,datetime.now(ZoneInfo('Asia/Kolkata')).date())
    app=create_app(Settings('STUB','scripted',tmp_path/'challenge.sqlite',None))
    with TestClient(app,base_url='http://127.0.0.1') as client:
        did,ids=setup(client,folder,manifest)
        results=[]
        for item in manifest['rejected']:
            before=overview(client,did)
            extra={'case_id':ids[item['invoice_id']]} if item.get('invoice_id') else {}
            command,view=preview(client,item['kind'],(folder/item['path']).read_text(encoding='utf-8'),did,**extra)
            assert view['errors'],item['path']
            command.update(confirmed_preview_hash=view['preview_hash'],confirm=True,fictional_data=True,settled_confirmed=True)
            response=client.post('/api/v1/intake/commits',json=command,headers=HEADERS)
            assert response.status_code==422,(item['path'],response.text)
            assert overview(client,did)==before,item['path']
            results.append(dict(file=item['path'],errors=view['errors'],commit_status=response.status_code))
        observed('rejection-results.json',results)


def test_exploration_files_disclose_limits_without_changing_money_or_approval(tmp_path):
    from datetime import datetime
    from zoneinfo import ZoneInfo
    folder=tmp_path/'pack';manifest=generate_pack(folder,datetime.now(ZoneInfo('Asia/Kolkata')).date())
    app=create_app(Settings('STUB','scripted',tmp_path/'explore.sqlite',None));results=[]
    with TestClient(app,base_url='http://127.0.0.1') as client:
        for item in manifest['explorations']:
            saved,_=commit(client,'customers',(folder/'01-customers.csv').read_text(encoding='utf-8'))
            did=saved['demonstration_id'];commit(client,'invoices',(folder/'02-invoices.csv').read_text(encoding='utf-8'),did)
            cid=next(c['id'] for c in overview(client,did)['cases'] if c['invoice_id']=='ECON-102')
            commit(client,item['kind'],(folder/item['path']).read_text(encoding='utf-8'),did,case_id=cid,context_only=item['context_only'])
            coverage(client,did);view=run(app.state.db,did,cid);result=view['current_result']
            assert result['financial_facts']['balance']['minor_units']=='4000000'
            assert view['lifecycle']=='OPEN'
            assert view['draft_reviews']==[]
            assert result['action']!='CLOSE'
            if 'supporting-context' in item['path']:assert result['status']=='LIMITED',(item['path'],result)
            if 'relative-weekday' in item['path']:
                # Independent source-calendar policy: strictly next Friday after
                # the generated message's source day, same day -> seven days.
                from datetime import timedelta
                import re
                source=(folder/item['path']).read_text(encoding='utf-8')
                day=datetime.fromisoformat(re.search(r'^Sent: (.+)$',source,re.M)[1]).date()
                friday=day+timedelta(days=(4-day.weekday())%7 or 7)
                assert result['action']==('WAIT' if friday>=datetime.now(ZoneInfo('Asia/Kolkata')).date() else 'FOLLOW_UP')
            if 'rupee-symbol' in item['path']:assert result['action']=='WAIT' and not result['commitment_issues']
            results.append(dict(file=item['path'],action=result['action'],status=result['status'],reason_code=result['reason_code'],balance=result['financial_facts']['balance']['minor_units'],explanation=result['explanation'],commitment_issues=result['commitment_issues']))
        observed('exploration-results.json',results)


def test_zip_contains_only_generated_files_not_preexisting_notes(tmp_path,monkeypatch):
    from zipfile import ZipFile
    from promisekeeper.fixtures.synthetic_pack import main
    output=tmp_path/'pack';output.mkdir();(output/'private-note.txt').write_text('not part of demo')
    archive=tmp_path/'pack.zip'
    monkeypatch.setattr('sys.argv',['synthetic-pack','--output',str(output),'--as-of','2026-10-25','--zip',str(archive)])
    main()
    manifest=json.loads((output/'EXPECTED-RESULTS.json').read_text(encoding='utf-8'))
    with ZipFile(archive) as zipped:
        assert 'private-note.txt' not in zipped.namelist()
        assert sorted(zipped.namelist())==manifest['generated_files']
