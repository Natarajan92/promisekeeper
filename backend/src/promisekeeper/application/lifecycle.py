"""Eligible exact-result closure and explicit reopening, committed with history."""
import json
from promisekeeper.application.operations import CommandError, replay, save_receipt
from promisekeeper.application.reviews import eligibility, result_context
from promisekeeper.domain.payments import reconcile_payments
from promisekeeper.persistence.repositories import append_event, case, load_fixture, require_revision


def close_blocks(con, row, investigation_id=None):
    iid = investigation_id or row['latest_completed_investigation_id']
    if not iid:
        return ['NO_COMPLETED_RESULT']
    blocks = eligibility(con, row, iid)
    context = result_context(con, row, iid)
    result = json.loads(context['result_json'])
    if context['action'] != 'CLOSE':
        blocks.append('CLOSE_NOT_RECOMMENDED')
    facts = result.get('financial_facts', {})
    if facts.get('certainty') != 'KNOWN' or facts.get('balance') != dict(currency='INR', minor_units='0'):
        blocks.append('SETTLEMENT_NOT_VERIFIED')
    # The domain ignores unknown invoice timing once exact settlement is proven.
    material_issues = [issue for issue in facts.get('issues', []) if issue['code'] != 'INVOICE_DATE_UNRESOLVED']
    if material_issues or result.get('contradictions') or result.get('limitations'):
        blocks.append('CONFLICTING_OR_LIMITED_RESULT')
    fixture = load_fixture(con, row['demonstration_id'])
    actual = reconcile_payments(fixture.cases[row['catalogue_case_id']].evidence)
    if actual.balance_minor != 0 or any(issue.code != 'INVOICE_DATE_UNRESOLVED' for issue in actual.issues):
        blocks.append('SETTLEMENT_NOT_VERIFIED')
    return list(dict.fromkeys(blocks))


def close_case(db, did, cid, request):
    with db.transaction() as con:
        saved = replay(con, did, 'CLOSE_CASE', cid, request)
        if saved:
            return saved
        row = case(con, did, cid)
        require_revision(row, request)
        if request['confirm'] is not True:
            raise CommandError('INVALID_REQUEST', 422)
        context = result_context(con, row, request['investigation_id'])
        if request['confirmed_result_hash'] != context['result_hash']:
            raise CommandError('RESULT_HASH_CHANGED')
        blocks = close_blocks(con, row, request['investigation_id'])
        if blocks:
            raise CommandError(blocks[0])
        packet = json.loads(con.execute('SELECT packet_json FROM evidence_snapshots WHERE id=?', (context['snapshot_id'],)).fetchone()[0])
        sources = [dict(source_id=e['stable_source_id'], evidence_version_id=e['id']) for e in packet['evidence']
            if e['kind'] in {'INVOICE', 'LEDGER', 'REVERSAL'}]
        con.execute("UPDATE cases SET lifecycle='CLOSED',case_revision=case_revision+1,review_epoch=review_epoch+1 WHERE id=?", (cid,))
        append_event(con, row, 'CASE_CLOSED', request['operation_id'], dict(investigation_id=request['investigation_id'],
            result_hash=context['result_hash'], snapshot_id=context['snapshot_id'], snapshot_hash=context['snapshot_hash'],
            evidence_revision=context['evidence_revision'], invoice_id=row['invoice_id'], settlement_sources=sources))
        return save_receipt(con, did, 'CLOSE_CASE', cid, request, 'CLOSED', revision=row['case_revision']+1, case_id=cid, lifecycle='CLOSED')


def reopen_case(db, did, cid, request):
    with db.transaction() as con:
        saved = replay(con, did, 'REOPEN_CASE', cid, request)
        if saved:
            return saved
        row = case(con, did, cid)
        require_revision(row, request)
        if request['confirm'] is not True:
            raise CommandError('INVALID_REQUEST', 422)
        if row['lifecycle'] != 'CLOSED':
            raise CommandError('CASE_NOT_CLOSED')
        con.execute("UPDATE cases SET lifecycle='OPEN',case_revision=case_revision+1,review_epoch=review_epoch+1 WHERE id=?", (cid,))
        append_event(con, row, 'CASE_REOPENED', request['operation_id'], dict(reason=request.get('reason')))
        return save_receipt(con, did, 'REOPEN_CASE', cid, request, 'REOPENED', revision=row['case_revision']+1, case_id=cid, lifecycle='OPEN')


def lifecycle_projection(con, row, view):
    blocks = close_blocks(con, row)
    view['allowed_commands']['close'] = dict(allowed=not blocks, blocking_reasons=blocks)
    blocks = [] if row['lifecycle'] == 'CLOSED' else ['CASE_NOT_CLOSED']
    view['allowed_commands']['reopen'] = dict(allowed=not blocks, blocking_reasons=blocks)
    blocks = [] if row['latest_completed_investigation_id'] else ['NO_COMPLETED_RESULT']
    view['allowed_commands']['disposition'] = dict(allowed=not blocks, blocking_reasons=blocks)
    view['owner_dispositions'] = [dict(r) for r in con.execute('SELECT * FROM owner_dispositions WHERE case_id=? ORDER BY rowid', (row['id'],))]
    return view
