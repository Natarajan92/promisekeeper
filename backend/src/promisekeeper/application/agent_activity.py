"""Append-only record of what each agent did, with per-step usage for the trace."""
import logging
from uuid import uuid4
from promisekeeper.application.operations import instant, utcnow

_log = logging.getLogger(__name__)
_COLUMNS = ('agent', 'event', 'outcome', 'note', 'model', 'input_tokens', 'output_tokens', 'latency_ms', 'at',
            'case_id', 'investigation_id', 'morning_review_id')


def record_agent(db, *, demonstration_id, case_id, agent, event, outcome, note=None, model=None, input_tokens=None,
                 output_tokens=None, latency_ms=None, investigation_id=None, morning_review_id=None):
    """The trace is explanatory. A failed write is logged and never interrupts the agent workflow."""
    try:
        with db.transaction() as con:
            con.execute('''INSERT INTO agent_activity (id,demonstration_id,case_id,investigation_id,morning_review_id,agent,event,
                outcome,note,model,input_tokens,output_tokens,latency_ms,at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (str(uuid4()), demonstration_id, case_id, investigation_id, morning_review_id, agent, event, outcome,
                 note, model, input_tokens, output_tokens, latency_ms, instant(utcnow())))
    except Exception:
        _log.warning('Agent activity was not recorded for %s/%s', agent, event)


def list_agent_activity(con, *, investigation_id=None, morning_review_id=None):
    column, value = ('investigation_id', investigation_id) if investigation_id else ('morning_review_id', morning_review_id)
    rows = con.execute(f'SELECT {",".join(_COLUMNS)} FROM agent_activity WHERE {column}=? ORDER BY at, rowid', (value,))
    return [dict(row) for row in rows]


def activity_totals(rows, token_rates):
    """Cost is reported only when every model that used tokens has an owner-configured USD rate."""
    used = [row for row in rows if row.get('input_tokens') is not None or row.get('output_tokens') is not None]
    totals = dict(input_tokens=sum(row.get('input_tokens') or 0 for row in rows),
                  output_tokens=sum(row.get('output_tokens') or 0 for row in rows),
                  latency_ms=sum(row.get('latency_ms') or 0 for row in rows), cost_usd=None)
    if used and all(row.get('model') in token_rates for row in used):
        totals['cost_usd'] = round(sum((row.get('input_tokens') or 0) * token_rates[row['model']][0]
                                       + (row.get('output_tokens') or 0) * token_rates[row['model']][1]
                                       for row in used) / 1_000_000, 6)
    return totals
