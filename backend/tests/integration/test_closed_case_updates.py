from support.lifecycle import close_ready, closure, command, update, run
from support.closed_conflict import CLOSED_CONFLICT_EVENT, install_closed_conflict_event
from promisekeeper.application.cases import get_case,get_evidence
from promisekeeper.persistence.sqlite import Database
from promisekeeper.persistence.repositories import history
from promisekeeper.orchestration.investigate import get_investigation


def test_confirmed_conflict_keeps_closed_state_and_retains_closure_result_sources_until_explicit_reopen(tmp_path,monkeypatch):
    from promisekeeper.application.lifecycle import close_case,reopen_case
    install_closed_conflict_event(monkeypatch)
    with Database(tmp_path/'db.sqlite') as db:
        did,cid,view=close_ready(db);result=view['current_result'];sources=view['evidence']
        close_case(db,did,cid,closure(view));events=history(db,did,cid)['events']
        update(db,did,cid,CLOSED_CONFLICT_EVENT['id'])
        now=get_case(db,did,cid)
        assert now['lifecycle']=='CLOSED' and now['review_required']
        assert now['freshness']=='EVIDENCE_CHANGED' and now['current_result'] is None
        assert now['latest_completed_result']==result
        assert now['allowed_commands']['start_investigation']['allowed'] is False
        assert now['allowed_commands']['close']['allowed'] is False
        assert history(db,did,cid)['events'][:len(events)]==events
        assert get_investigation(db,did,result['investigation_id'])['result']==result
        for source in sources:assert get_evidence(db,did,source['id'])==source
        reopened=reopen_case(db,did,cid,command(now,confirm=True,reason='Review conflicting invoice'))
        assert reopened['lifecycle']=='OPEN'
        after=run(db,did,cid)
        assert after['current_result']['action']=='VERIFY_PAYMENT'
        assert get_investigation(db,did,result['investigation_id'])['result']==result
        assert history(db,did,cid)['events'][:len(events)]==events
