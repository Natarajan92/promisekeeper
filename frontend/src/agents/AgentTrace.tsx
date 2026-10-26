import { useEffect, useState } from 'react';
import type { ApiClient } from '../api/client';
import type { AgentActivity, AgentName, AgentTotals } from '../api/types';
import { AGENT_LABEL, AGENT_ROLE, MESSAGE_LABEL, OUTCOME_LABEL, usage } from './agentLabels';

const POLL_MS = 1500;
const MAX_POLL_MS = 45_000;

function finished(rows: AgentActivity[], status: string, draftStatus: string) {
  return rows.some(row => row.agent === 'OWNER') || (status !== 'RUNNING' && draftStatus !== 'RUNNING');
}

export function AgentTrace({api, did, investigationId, agents, compact=false, title = 'How your AI team worked on this case'}:
  {api: ApiClient; did: string; investigationId: string; agents?: AgentName[]; compact?:boolean; title?: string}) {
  const [rows, setRows] = useState<AgentActivity[] | null>(null);
  const [totals, setTotals] = useState<AgentTotals | null>(null);
  const [error, setError] = useState('');
  const [state,setState]=useState<{status:string;draft:string}|null>(null);
  const [paused,setPaused]=useState(false);
  const [processingOpen,setProcessingOpen]=useState(false);
  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const started = Date.now();
    setRows(null);setTotals(null);setState(null);setError('');setPaused(false);
    async function poll() {
      try {
        const attempt = await api.attempt(did, investigationId);
        if (cancelled) return;
        const activity = attempt.agent_activity ?? [];
        setRows(activity); setTotals(attempt.agent_totals ?? null); setError('');
        setState({status:attempt.status,draft:attempt.draft_status});
        if (finished(activity, attempt.status, attempt.draft_status)) return;
        if (Date.now() - started > MAX_POLL_MS) {setPaused(true);return;}
      } catch (failure) {
        if (cancelled) return;
        setError(failure instanceof Error ? failure.message : 'Agent activity is unavailable.');
        if (Date.now() - started > MAX_POLL_MS) {setPaused(true);return;}
      }
      timer = setTimeout(poll, POLL_MS);
    }
    void poll();
    return () => { cancelled = true; clearTimeout(timer); };
  }, [api, did, investigationId]);
  const shown = (rows ?? []).filter(row => row.outcome !== 'STARTED' && (!agents || agents.includes(row.agent)));
  const last = shown[shown.length - 1];
  const summary = totals ? [...usage(totals.latency_ms, totals.input_tokens, totals.output_tokens),
    totals.cost_usd === null ? 'cost not configured' : `≈ $${totals.cost_usd.toFixed(4)}`].join(' · ') : '';
  const progress=!state?'Checking saved progress…':state.status==='RUNNING'?'Investigation in progress.':state.status==='INCOMPLETE'?'Investigation incomplete. Check saved status and recovery options.':state.draft==='RUNNING'?'Recommendation saved. Preparing your message.':state.draft==='FAILED'?'Recommendation saved. Message preparation needs attention.':state.draft==='READY'?'Recommendation saved. Message ready for review.':'Recommendation saved.';
  const detail=<>
    {rows === null && !error && <p className="subtle" role="status">Loading agent activity…</p>}
    {error && <p className="subtle" role="status">Agent activity unavailable: {error}</p>}
    {rows !== null && !shown.length && <p className="subtle">No agent steps recorded for this result.</p>}
    {shown.length > 0 && <ol>{shown.map((row, index) => <li key={`${row.at}-${index}`} className={`agent-step outcome-${row.outcome.toLowerCase()}`}>
      <div className="agent-step-head">
        <strong>{AGENT_LABEL[row.agent] ?? row.agent}</strong>
        <span className="agent-outcome">{OUTCOME_LABEL[row.outcome] ?? row.outcome}</span>
      </div>
      <p className="agent-role">{AGENT_ROLE[row.agent]}</p>
      {row.note && <p className="agent-note">{row.note}</p>}
      {row.recipient && <p className="agent-handoff">{`→ ${AGENT_LABEL[row.recipient]}: ${MESSAGE_LABEL[row.message_kind ?? ''] ?? ''}`}</p>}
      {(row.model || row.latency_ms || row.input_tokens) && <p className="agent-usage">{[row.model, ...usage(row.latency_ms, row.input_tokens, row.output_tokens)].filter(Boolean).join(' · ')}</p>}
    </li>)}</ol>}
    {summary && !agents && <p className="agent-totals">Total: {summary}</p>}
  </>;
  return <section className={`agent-trace${compact?' progress-summary':''}`} aria-label={title}>
    <h3>{title}</h3>
    {compact&&<div aria-live="polite"><p>{progress}</p><p className="subtle">{last?`Last confirmed: ${AGENT_LABEL[last.agent]} — ${OUTCOME_LABEL[last.outcome]}.`:'Waiting for a confirmed activity update.'}</p></div>}
    {compact&&error&&<p className="notice">Progress updates unavailable. The server outcome is unknown; check saved investigation status.</p>}
    {paused&&<p className="notice">Activity updates paused. This is the last confirmed status; check saved investigation status for a newer result.</p>}
    {compact?<details className="processing-details" onToggle={event=>setProcessingOpen(event.currentTarget.open)}><summary>Processing details</summary>{processingOpen&&detail}</details>:detail}
    {!compact&&<p className="visually-hidden" aria-live="polite">{last ? `${AGENT_LABEL[last.agent]}: ${OUTCOME_LABEL[last.outcome]}` : ''}</p>}
  </section>;
}

export function AgentTraceDisclosure({api, did, investigationId}: {api: ApiClient; did: string; investigationId: string}) {
  const [open, setOpen] = useState(false);
  return <details className="agent-disclosure" onToggle={event => setOpen((event.currentTarget as HTMLDetailsElement).open)}>
    <summary>See how your AI team wrote this draft</summary>
    {open && <AgentTrace api={api} did={did} investigationId={investigationId} agents={['MEMORY', 'COMMUNICATOR', 'SAFETY_CHECK', 'TONE_REVIEWER']} title="How this draft was written"/>}
  </details>;
}
