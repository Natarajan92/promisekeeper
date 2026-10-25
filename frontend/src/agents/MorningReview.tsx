import { useEffect, useRef, useState } from 'react';
import type { ApiClient } from '../api/client';
import type { MorningReviewView } from '../api/types';
import { words } from '../components/format';
import { AGENT_LABEL, OUTCOME_LABEL } from './agentLabels';

const POLL_MS = 1200;
const MAX_POLL_MS = 120_000;
const OUTCOME_TEXT = {INVESTIGATED: 'investigated now', SKIPPED: 'no change needed', FAILED: 'needs your retry'} as const;

export function MorningReview({api, did, onOpenCase, onDone, maxWaitMs = MAX_POLL_MS}:
  {api: ApiClient; did: string; onOpenCase: (caseId: string) => void; onDone: () => void; maxWaitMs?: number}) {
  const [review, setReview] = useState<MorningReviewView | null>(null);
  const [busy, setBusy] = useState(false);
  const [following, setFollowing] = useState(false);
  const [message, setMessage] = useState('');
  const mounted = useRef(true);
  async function follow(initial: MorningReviewView) {
    setFollowing(true); setMessage('');
    let current = initial;
    const started = Date.now();
    try {
      while (mounted.current && current.status === 'RUNNING' && Date.now() - started < maxWaitMs) {
        setReview(current);
        await new Promise(resolve => setTimeout(resolve, POLL_MS));
        current = await api.morningReview(did, current.id);
      }
      if (!mounted.current) return;
      setReview(current);
      if (current.status === 'RUNNING') {
        setMessage('Still working. Your cases stay available; choose Check again in a moment.');
        return;
      }
      if (current.status === 'FAILED') setMessage(`Morning review stopped: ${words(current.failure_code ?? 'unknown')}. Saved cases are unchanged.`);
      onDone();
    } catch (error) {
      if (mounted.current) setMessage(`Could not check the morning review: ${error instanceof Error ? error.message : 'try again.'}`);
    } finally {
      if (mounted.current) setFollowing(false);
    }
  }
  useEffect(() => {
    mounted.current = true;
    void api.latestMorningReview(did).then(latest => {
      if (!mounted.current) return;
      setReview(latest.morning_review);
      // A review started elsewhere (another tab, autonomy) is followed rather than left greyed out.
      if (latest.morning_review?.status === 'RUNNING') void follow(latest.morning_review);
    }).catch(() => undefined);
    return () => { mounted.current = false; };
  }, [api, did]);
  async function start() {
    setBusy(true); setMessage('');
    let started: MorningReviewView;
    try {
      started = await api.startMorningReview(did, {schema_version: '1', operation_id: crypto.randomUUID()});
    } catch (error) {
      if (mounted.current) { setMessage(`Morning review not started: ${error instanceof Error ? error.message : 'try again.'}`); setBusy(false); }
      return;
    }
    if (mounted.current) setBusy(false);
    await follow(started);
  }
  const working = busy || following;
  const running = working || review?.status === 'RUNNING';
  const steps = (review?.agent_activity ?? []).filter(row => row.outcome !== 'STARTED');
  return <section className="morning-review" aria-labelledby="morning-heading">
    <div className="morning-head">
      <div>
        <h2 id="morning-heading">Morning review</h2>
        <p className="subtle">Your AI supervisor checks every open case, investigates the ones that need it and briefs you. Nothing is sent or approved without you.</p>
      </div>
      <button className="primary" disabled={running} onClick={() => void start()}>{running ? 'Reviewing your cases…' : 'Start morning review'}</button>
    </div>
    {message && <p className="notice" role="status">{message}</p>}
    {review?.status === 'RUNNING' && !working && <button onClick={() => void follow(review)}>Check again</button>}
    {running && steps.length > 0 && <ol className="morning-steps" aria-live="polite">{steps.map((row, index) =>
      <li key={`${row.at}-${index}`}><strong>{AGENT_LABEL[row.agent]}</strong> {OUTCOME_LABEL[row.outcome]}{row.note ? `: ${row.note}` : ''}</li>)}</ol>}
    {review?.briefing && review.status !== 'RUNNING' && <div className="briefing">
      {review.started_by === 'AUTONOMOUS' && <p className="autonomy-label">Started automatically by your AI supervisor because cases were due.</p>}
      <p className="briefing-text">{review.briefing}</p>
      <p className="subtle">{review.briefing_source === 'AGENT'
        ? "Written by the Briefing agent. Each amount and date was checked against that case's facts; spelled-out amounts are not allowed."
        : 'Plain summary written by code (the Briefing agent was unavailable or not trusted for this run).'}</p>
      <ul className="briefing-cases">{review.outcomes.map(outcome => <li key={outcome.case_id}>
        <button onClick={() => onOpenCase(outcome.case_id)}>
          <strong>{outcome.client}</strong>
          <span>{outcome.action ? words(outcome.action) : 'No current recommendation'}{outcome.draft_ready && outcome.action === 'FOLLOW_UP' ? ' · draft ready for review' : ''}</span>
          <span className={`briefing-outcome outcome-${outcome.outcome.toLowerCase()}`}>{OUTCOME_TEXT[outcome.outcome]}</span>
        </button>
        {outcome.reason && <p className="subtle">{outcome.reason}</p>}
      </li>)}</ul>
      {steps.length > 0 && <details className="agent-disclosure"><summary>See what the supervisor did</summary><ol className="morning-steps">{steps.map((row, index) =>
        <li key={`${row.at}-${index}`}><strong>{AGENT_LABEL[row.agent]}</strong> {OUTCOME_LABEL[row.outcome]}{row.note ? `: ${row.note}` : ''}</li>)}</ol></details>}
    </div>}
  </section>;
}
