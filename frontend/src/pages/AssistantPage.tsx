import {useEffect, useRef, useState} from 'react';
import type {ApiClient} from '../api/client';
import type {AgentActivity, AgentName, CaseOutcome, MorningReviewView} from '../api/types';
import {AgentTrace} from '../agents/AgentTrace';
import {AgentTeam, AGENT_ICON, KindTag} from '../agents/AgentTeam';
import {MorningReview, type MorningReviewParts} from '../agents/MorningReview';
import {AGENT_LABEL, MESSAGE_LABEL, OUTCOME_LABEL} from '../agents/agentLabels';
import {instant, words} from '../components/format';
import {isPageLoadRoute, routeLink} from '../routing';
import type {PageProps} from '../store/useWorkspace';
import {WorkspaceStatus} from './WorkspaceStatus';
import '../agents/assistant.css';

const ACTIVITY_POLL_MS=1500;
const ACTIVITY_MAX_MS=45_000;
const OUTCOME_TEXT={INVESTIGATED:'Investigated now',SKIPPED:'No change needed',FAILED:'Needs your retry'} as const;
const failure=(error:unknown,fallback:string)=>error instanceof Error?error.message:fallback;

// The saved agent activity of one investigation, followed while it is still being written.
function useCaseActivity(api:ApiClient,did:string|null,investigationId:string|undefined) {
  const [data,setData]=useState<{key:string;rows:AgentActivity[];error:string}|null>(null);
  const key=`${did}:${investigationId}`;
  useEffect(()=>{
    if(!did||!investigationId)return;
    let cancelled=false;let timer:ReturnType<typeof setTimeout>|undefined;const started=Date.now();
    async function poll() {
      try {
        const attempt=await api.attempt(did!,investigationId!);
        if(cancelled)return;
        setData({key,rows:attempt.agent_activity??[],error:''});
        if(attempt.status!=='RUNNING'&&attempt.draft_status!=='RUNNING')return;
      }catch(error){if(cancelled)return;setData(old=>({key,rows:old?.key===key?old.rows:[],error:failure(error,'Agent activity is unavailable.')}));}
      if(Date.now()-started<ACTIVITY_MAX_MS)timer=setTimeout(poll,ACTIVITY_POLL_MS);
    }
    void poll();
    return ()=>{cancelled=true;clearTimeout(timer);};
  },[api,did,investigationId,key]);
  return data?.key===key?data:null;
}

function planOrder(outcomes:CaseOutcome[]) {
  const rank=(item:CaseOutcome)=>item.priority??Number.MAX_SAFE_INTEGER;
  return outcomes.map((item,index)=>({item,index})).sort((a,b)=>rank(a.item)-rank(b.item)||a.index-b.index).map(entry=>entry.item);
}

// Display only: starting, following, polling and their messages all belong to MorningReview.
function statusLine(review:MorningReviewView|null,running:boolean) {
  if(running)return review?`Morning review in progress, started ${instant(review.started_at)}.`:'Starting the morning review…';
  if(!review)return 'No morning review has run in this workspace yet.';
  const who=review.started_by==='AUTONOMOUS'?' Started automatically by your AI supervisor because cases were due.':'';
  return `${review.status==='FAILED'?'Last morning review stopped':'Last morning review finished'} ${instant(review.terminal_at)}.${who}`;
}

// The page reuses the morning review itself (one state machine, one wording) and lays its parts out as the explainer.
export function AssistantPage(props:PageProps) {
  const {ws,navigate}=props;
  if(!ws.selected)return <AssistantBody {...props} parts={null}/>;
  return <MorningReview key={`morning:${ws.selected}`} api={ws.api} did={ws.selected} cases={ws.list?.cases} evaluationAt={ws.evaluationAt} onPlan={ws.setPlan}
    onOpenCase={id=>navigate({page:'case',caseId:id,section:'overview'})} onDone={ws.refresh}
    layout={parts=><AssistantBody {...props} parts={parts}/>}/>;
}

function AssistantBody({ws,route,navigate,parts}:PageProps&{parts:MorningReviewParts|null}) {
  const did=ws.selected;
  const review=parts?.review??null;
  const running=!!parts?.running;
  const outcomes=review&&review.status!=='RUNNING'?planOrder(review.outcomes):[];
  const morningRows=(review?.agent_activity??[]).filter(row=>row.outcome!=='STARTED');
  // The case followed step by step: the one in the route, else the supervisor's first planned case with a saved result.
  const checked=ws.cases.filter(entry=>entry.view?.latest_completed_result);
  const requested=route.page==='assistant'?route.caseId:undefined;
  const requestedEntry=requested?ws.cases.find(entry=>entry.summary.id===requested):undefined;
  const chosen=requested?(requestedEntry?.view?.latest_completed_result?requestedEntry:undefined)
    :outcomes.map(outcome=>checked.find(entry=>entry.summary.id===outcome.case_id)).find(Boolean)??checked[0];
  const view=chosen?.view??null;
  const investigationId=view?.latest_completed_result?.investigation_id;
  const activity=useCaseActivity(ws.api,did,investigationId);
  const caseRows=(activity?.rows??[]).filter(row=>row.outcome!=='STARTED');
  const latest:Partial<Record<AgentName,AgentActivity>>={};
  for(const row of [...morningRows,...caseRows].sort((a,b)=>a.at.localeCompare(b.at)))latest[row.agent]=row;
  const scope=(row:AgentActivity)=>row.investigation_id&&row.investigation_id===investigationId&&view?`for ${view.client}`:'in the morning check';
  const [technical,setTechnical]=useState(false);
  // Choosing a case in the app moves focus to its steps; a refreshed deep link does not.
  const stepsHeading=useRef<HTMLHeadingElement>(null);
  const focused=useRef<unknown>(null);
  useEffect(()=>{
    if(route.page!=='assistant'||!route.caseId||isPageLoadRoute(route)||focused.current===route)return;
    focused.current=route;stepsHeading.current?.focus({preventScroll:true});stepsHeading.current?.scrollIntoView?.({block:'start'});
  },[route]);
  const fellBack=morningRows.some(row=>row.agent==='SUPERVISOR'&&row.outcome==='FALLBACK');
  const mode=ws.health?.agent_mode;
  return <div className="assistant-page">
    <header className="assistant-hero">
      <div className="assistant-hero-text">
        <h1>Assistant at work</h1>
        <p className="assistant-lead">See how your digital team checks each case. AI agents read and draft; code decides money and next steps; you approve everything.</p>
        <p className="assistant-status">{did?statusLine(review,running):'Choose a workspace to see your assistant at work.'}</p>
        <p className="assistant-mode"><span className={`mode-pill mode-${(mode??'unknown').toLowerCase()}`}>{mode==='LIVE'?'LIVE':mode==='STUB'?'STUB':'Mode unknown'}</span> {mode==='LIVE'?'Real AI providers are answering in this run.':mode==='STUB'?'A scripted offline sample stands in for the AI. No AI provider is called.':'The server mode is not known yet.'}</p>
        {parts&&<div className="assistant-hero-description">{parts.description}</div>}
      </div>
      {parts&&<div className="assistant-hero-actions">{parts.button}</div>}
    </header>
    <WorkspaceStatus ws={ws}/>
    {parts&&<div className="assistant-live">{parts.live}</div>}
    <AgentTeam health={ws.health} latest={latest} scope={scope}/>
    {did&&<div className="assistant-columns">
      <section className="assistant-card plan-card" aria-labelledby="plan-heading">
        <div className="assistant-section-head">
          <h2 id="plan-heading">Today's plan</h2>
          <p className="subtle">Your AI supervisor chose this order, re-planned after every result, and code checked each choice.</p>
        </div>
        {!review||review.status==='RUNNING'?<p className="subtle">{running?'The plan appears when the morning review finishes.':'Start a morning review to see which cases your supervisor works on first, and why.'}</p>:<>
          {fellBack&&<p className="notice">The supervisor was unavailable for part of this check, so code used the standard rule order.</p>}
          {outcomes.length===0?<p className="subtle">This morning check had no cases to plan.</p>:
          <ol className="plan-list" aria-labelledby="plan-heading">{outcomes.map((outcome,index)=><li key={outcome.case_id} className="plan-row">
            <span className="plan-rank" aria-hidden="true">{outcome.priority??index+1}</span>
            <div className="plan-body">
              <p className="plan-title"><strong>{outcome.client}</strong> · {outcome.invoice_id}<span className={`plan-chip outcome-${outcome.outcome.toLowerCase()}`}>{OUTCOME_TEXT[outcome.outcome]}</span></p>
              <p className="plan-action">{outcome.action?words(outcome.action):'No current recommendation'}{outcome.balance_text?` · ${outcome.balance_text}`:''}{outcome.draft_ready?' · draft ready for your review':''}</p>
              {outcome.supervisor_reason&&<p className="plan-why"><strong>Why now:</strong> {outcome.supervisor_reason}</p>}
              {outcome.reason&&<p className="subtle">{outcome.reason}</p>}
            </div>
            <div className="plan-links">
              {ws.cases.some(entry=>entry.summary.id===outcome.case_id)&&<><a {...routeLink({page:'assistant',caseId:outcome.case_id},navigate)}>Show steps</a>
              <a {...routeLink({page:'case',caseId:outcome.case_id},navigate)}>Open case →</a></>}
            </div>
          </li>)}</ol>}
          {review.briefing&&<div className="plan-briefing"><h3>Briefing</h3><p>{review.briefing}</p><p className="subtle">{review.briefing_source==='AGENT'?"Written by the Briefing agent. Each amount and date was checked against that case's facts.":'Plain summary written by code (the Briefing agent was unavailable or not trusted for this run).'}</p></div>}
        </>}
      </section>
      <section className="assistant-card steps-card" aria-labelledby="steps-heading">
        <div className="assistant-section-head steps-head">
          <h2 id="steps-heading" ref={stepsHeading} tabIndex={-1}>Step by step</h2>
          {checked.length>0&&<div className="steps-picker"><label htmlFor="assistant-case">Case to follow</label>
            <select id="assistant-case" value={view?.id??''} onChange={event=>navigate({page:'assistant',caseId:event.target.value})}>
              {!view&&<option value="">Choose a case</option>}
              {checked.map(entry=><option key={entry.summary.id} value={entry.summary.id}>{entry.summary.client} · {entry.summary.invoice_id}</option>)}
            </select></div>}
        </div>
        {!view||!investigationId?<p className="subtle">{requestedEntry?`${requestedEntry.summary.client} has not been checked yet. Investigate it or run a morning check.`:requested&&ws.list?"That case isn't in the current workspace. Choose another case to follow.":ws.detailsLoading?'Loading saved cases…':'No case has been checked yet. Run a morning check or investigate a case to see each step.'}</p>:<>
          <p className="subtle">How the team handled {view.client} in its latest saved check, evaluated {instant(view.latest_completed_result!.evaluation_at)}.</p>
          {view.running_attempt&&<p className="notice">A new check is running for this case. These are the steps of the latest saved one.</p>}
          {activity===null&&<p className="subtle" role="status">Loading the team's steps…</p>}
          {activity?.error&&<p className="subtle" role="status">Agent activity unavailable: {activity.error}</p>}
          {activity&&!activity.error&&caseRows.length===0&&<p className="subtle">No agent steps were recorded for this result.</p>}
          {caseRows.length>0&&<ol className="step-feed" aria-label={`Steps for ${view.client}`}>{caseRows.map((row,index)=><li key={`${row.at}-${index}`} className={`step-row outcome-${row.outcome.toLowerCase()}`}>
            <span className="step-icon" aria-hidden="true">{AGENT_ICON[row.agent]}</span>
            <div className="step-body">
              <p className="step-head"><strong>{AGENT_LABEL[row.agent]}</strong><KindTag agent={row.agent}/><span className="step-outcome">{OUTCOME_LABEL[row.outcome]}</span></p>
              {row.note&&<p className="step-note">{row.note}</p>}
              {row.recipient&&<p className="step-handoff">{`→ ${AGENT_LABEL[row.recipient]}: ${MESSAGE_LABEL[row.message_kind??'']??''}`}</p>}
            </div>
          </li>)}</ol>}
          <details className="technical-details" onToggle={event=>setTechnical(event.currentTarget.open)}>
            <summary>Show technical details</summary>
            {technical&&<AgentTrace key={`technical:${investigationId}`} api={ws.api} did={view.demonstration_id} investigationId={investigationId} title="Technical details: models, tokens, time and cost"/>}
          </details>
        </>}
      </section>
    </div>}
  </div>;
}
