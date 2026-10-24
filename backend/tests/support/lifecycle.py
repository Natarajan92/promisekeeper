from uuid import uuid4
from promisekeeper.application.cases import create_demonstration, get_case
from promisekeeper.application.scenario_updates import preview_event, confirm_event
from promisekeeper.application.start_investigation import start_investigation
from promisekeeper.agents.scripted import ScriptedInvestigator
from promisekeeper.orchestration.investigate import investigate


def command(view, **fields):
    return dict(schema_version='1', operation_id=str(uuid4()), expected_case_revision=view['case_revision'], **fields)


def create_case(db, variant=None, catalogue_case_id='PK-003'):
    did = create_demonstration(db, dict(schema_version='1', operation_id=str(uuid4()), catalogue_version='release-0.1', variant_id=variant, clock_mode='REFERENCE'))['demonstration_id']
    with db.connection() as con:
        cid = con.execute('SELECT id FROM cases WHERE demonstration_id=? AND catalogue_case_id=?', (did, catalogue_case_id)).fetchone()[0]
    return did, cid


def update(db, did, cid, event_id):
    p = preview_event(db, did, cid, event_id)
    return confirm_event(db, did, cid, dict(schema_version='1', operation_id=str(uuid4()), expected_case_revision=p['expected_case_revision'], event_id=event_id, catalogue_version=p['catalogue_version'], confirmed_preview_hash=p['preview_hash']))


def run(db, did, cid):
    view = get_case(db, did, cid)
    response = start_investigation(db, did, cid, command(view, retry_of=None))
    assert investigate(db, response['investigation_id'], ScriptedInvestigator())
    return get_case(db, did, cid)


def close_ready(db):
    did, cid = create_case(db)
    before = run(db, did, cid)
    assert before['current_result']['action'] == 'VERIFY_PAYMENT'
    update(db, did, cid, 'PK-003-U1')
    view = run(db, did, cid)
    assert view['current_result']['action'] == 'CLOSE'
    return did, cid, view


def closure(view):
    result = view['current_result']
    return command(view, investigation_id=result['investigation_id'], confirmed_result_hash=result['result_hash'], confirm=True)
