import { useEffect, useRef, useState, type ReactNode } from 'react';
import type { ApiClient } from '../api/client';
import type { AgentActivity, CaseOutcome, CaseSummary, MorningReviewView } from '../api/types';
import { words } from '../components/format';
import { attentionOrder, needsAttention, statusLabel } from '../cases/caseStatus';
import { AGENT_LABEL, OUTCOME_LABEL } from './agentLabels';

const POLL_MS = 1200;
const MAX_POLL_MS = 120_000;
// Supervisor steps name the decision; a supervisor fallback means rule order, not the draft template.
function stepLabel(row: AgentActivity) {
  if (row.agent !== 'SUPERVISOR') return OUTCOME_LABEL[row.outcome];
  return row.outcome === 'FALLBACK' ? `${row.event} (rule order)` : row.event;
}
const OUTCOME_TEXT = {INVESTIGATED: 'investigated now', SKIPPED: 'no change needed', FAILED: 'needs your retry'} as const;

/** The parts of the morning review a page may lay out itself; every part keeps its own behaviour and wording. */
export interface MorningReviewParts {
  /** The "Start morning review" button. */
  button: ReactNode;
  /** One-line explanation of what the review does. */
  description: ReactNode;
  /** Status message, "Check again" and the live supervisor steps while a review runs. */
  live: ReactNode;
  /** The finished review: briefing status, the per-case strip, saved briefing and supervisor steps. */
  results: ReactNode;
  review: MorningReviewView | null;
  running: boolean;
}

export function MorningReview({api, did, onOpenCase, onDone, maxWaitMs = MAX_POLL_MS, cases, evaluationAt, onPlan, layout}:
  {api: ApiClient; did: string; onOpenCase: (caseId: string) => void; onDone: () => void; maxWaitMs?: number;
   cases?: CaseSummary[]; evaluationAt?: string; onPlan?: (plan: Record<string, number>) => void;
   /** Optional page layout; without it the review renders as one section, as before. */
   layout?: (parts: MorningReviewParts) => ReactNode}) {
  const [review, setReview] = useState<MorningReviewView | null>(null);
  const [busy, setBusy] = useState(false);
  const [following, setFollowing] = useState(false);
  const [message, setMessage] = useState('');
  const mounted = useRef(true);
  const strip = useRef<HTMLUListElement>(null);
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
      if (current.status === 'FAILED') setMessage(`Morning review stopped: ${words(current.failure_code ?? 'unknown')}. Completed case results remain saved. Check each case before retrying.`);
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
  const planned = (review?.outcomes ?? []).some(outcome => outcome.priority);
  const plan = Object.fromEntries((review?.status === 'RUNNING' ? [] : review?.outcomes ?? [])
    .filter(outcome => outcome.priority).map(outcome => [outcome.case_id, outcome.priority as number]));
  const planKey = JSON.stringify(plan);
  // The case overview orders its cards by the same plan, so both views list cases identically.
  useEffect(() => { onPlan?.(plan); }, [planKey]);
  // Cards show each case's current status (not the snapshot saved at review time), in the overview's order.
  const current = new Map((cases ?? []).map(item => [item.id, item]));
  const known = (review?.outcomes ?? []).filter(outcome => current.has(outcome.case_id));
  const byCase = new Map(known.map(outcome => [outcome.case_id, outcome]));
  const cards: CaseOutcome[] = [
    ...attentionOrder(known.map(outcome => current.get(outcome.case_id) as CaseSummary), evaluationAt, plan).map(item => byCase.get(item.id) as CaseOutcome),
    ...(review?.outcomes ?? []).filter(outcome => !current.has(outcome.case_id))];
  function scrollStrip(direction: number) {
    const list = strip.current;
    if (!list) return;
    const card = list.querySelector('li');
    list.scrollBy({left: direction * ((card?.getBoundingClientRect().width ?? 260) + 10), behavior: 'smooth'});
  }
  const description = <p className="subtle">Your AI supervisor plans which cases to investigate first, re-plans after every result and briefs you. Code checks each of its choices. Nothing is sent or approved without you.</p>;
  const button = <button className={review?.status==='COMPLETE'?undefined:'primary'} disabled={running} onClick={() => void start()}>{running ? 'Reviewing your cases…' : 'Start morning review'}</button>;
  const live = <>
    {message && <p className="notice" role="status">{message}</p>}
    {review?.status === 'RUNNING' && !working && <button onClick={() => void follow(review)}>Check again</button>}
    {running && steps.length > 0 && <ol className="morning-steps" aria-live="polite">{steps.map((row, index) =>
      <li key={`${row.at}-${index}`}><strong>{AGENT_LABEL[row.agent]}</strong> {stepLabel(row)}{row.note ? `: ${row.note}` : ''}</li>)}</ol>}
  </>;
  const results = review?.briefing && review.status !== 'RUNNING' ? <div className="briefing">
      {review.started_by === 'AUTONOMOUS' && <p className="autonomy-label">Started automatically by your AI supervisor because cases were due.</p>}
      <p className="briefing-status">{review.status==='COMPLETE'?'Review complete. Choose a case to see its recommendation.':'Review stopped. Check saved case outcomes before retrying.'}</p>
      {planned && <p className="subtle">Cases that need your attention come first, in the same order as the Case overview. “Checked #N” is the order your AI supervisor investigated them. Scroll sideways to see every case.</p>}
      <div className="briefing-strip">
        <button className="strip-nav" aria-label="Previous cases" onClick={() => scrollStrip(-1)}>‹</button>
        <ul className="briefing-cases" ref={strip} aria-label="Morning review cases">{cards.map(outcome => {
          const now = current.get(outcome.case_id);
          const label = now ? statusLabel(now, evaluationAt) : outcome.action ? words(outcome.action) : 'No current recommendation';
          const urgent = now ? needsAttention(now, evaluationAt) : null;
          return <li key={outcome.case_id}>
          <button onClick={() => onOpenCase(outcome.case_id)}>
            {urgent !== null && <span className={`attention-badge ${urgent ? 'urgent' : 'can-wait'}`}>{urgent ? 'Needs attention' : 'Can wait'}</span>}
            <strong>{outcome.client}</strong>
            <span>{label}{outcome.draft_ready && label === words('FOLLOW_UP') ? ' · draft ready for review' : ''}</span>
            {!!outcome.priority && <span className="briefing-rank">Checked #{outcome.priority} by your supervisor</span>}
            <span className={`briefing-outcome outcome-${outcome.outcome.toLowerCase()}`}>{OUTCOME_TEXT[outcome.outcome]}</span>
          </button>
          {outcome.supervisor_reason && <p className="supervisor-reason"><strong>Why now:</strong> {outcome.supervisor_reason}</p>}
          {outcome.reason && <p className="subtle">{outcome.reason}</p>}
        </li>;})}</ul>
        <button className="strip-nav" aria-label="Next cases" onClick={() => scrollStrip(1)}>›</button>
      </div>
      <details className="saved-briefing"><summary>Read saved briefing</summary>
        <p className="briefing-text">{review.briefing}</p>
        <p className="subtle">{review.briefing_source === 'AGENT'
          ? "Written by the Briefing agent. Each amount and date was checked against that case's facts; spelled-out amounts are not allowed."
          : 'Plain summary written by code (the Briefing agent was unavailable or not trusted for this run).'}</p>
      </details>
      {steps.length > 0 && <details className="agent-disclosure"><summary>See what the supervisor did</summary><ol className="morning-steps">{steps.map((row, index) =>
        <li key={`${row.at}-${index}`}><strong>{AGENT_LABEL[row.agent]}</strong> {stepLabel(row)}{row.note ? `: ${row.note}` : ''}</li>)}</ol></details>}
    </div> : null;
  if (layout) return <>{layout({button, description, live, results, review, running})}</>;
  return <section className="morning-review" aria-labelledby="morning-heading">
    <div className="morning-head">
      <div>
        <h2 id="morning-heading">Morning review</h2>
        {description}
      </div>
      {button}
    </div>
    {live}
    {results}
  </section>;
}
