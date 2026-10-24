import type {CaseView} from '../api/types';
import {instant} from '../components/format';

type Section='evidence'|'findings'|'review';
export function CaseJourney({view,active,onNavigate}:{view:CaseView;active:string;onNavigate:(section:Section)=>void}) {
  const result=view.current_result;
  const current=!!result&&!view.running_attempt;
  const message=current&&(result.action==='FOLLOW_UP'||!!view.draft);
  const third:Section=message?'review':result?.action==='VERIFY_PAYMENT'?'evidence':'findings';
  const thirdLabel=message?'Review message':result?.action==='VERIFY_PAYMENT'?'Check payment evidence':result?.action==='CLOSE'?'Review settlement':'Check review date';
  return <nav className="case-journey" aria-label="Case journey">
    <ol>
      <li><button aria-current={active==='evidence'?'step':undefined} onClick={()=>onNavigate('evidence')}>Inspect evidence</button></li>
      <li><button disabled={!view.latest_completed_result} aria-current={active==='findings'?'step':undefined} onClick={()=>onNavigate('findings')}>{view.latest_completed_result&&!current?'View previous recommendation':'View recommendation'}</button></li>
      <li><button disabled={!current} aria-current={active==='review'?'step':undefined} onClick={()=>onNavigate(third)}>{current?thirdLabel:'Choose the next action'}</button></li>
    </ol>
    <p>{view.lifecycle==='CLOSED'?'This case is closed. Its evidence and decisions remain available.':view.running_attempt?'Investigation in progress. You can keep inspecting evidence.':!result?'Inspect the saved evidence, then choose Investigate case for a current recommendation.':result.action==='WAIT'?`Next review: ${instant(result.review_at)}. Return then and investigate again; no reminder is sent.`:'View the recommendation and its sources before recording your decision.'}</p>
  </nav>;
}
