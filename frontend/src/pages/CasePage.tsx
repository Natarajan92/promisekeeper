import {useEffect, useRef, useState} from 'react';
import type {CaseView, Evidence, HistoryEvent} from '../api/types';
import {instant, money, words} from '../components/format';
import {Avatar} from '../components/Avatar';
import {CaseChip} from '../components/Chip';
import {CaseStory, KeyFacts} from '../cases/CaseStory';
import {CaseJourney} from '../cases/CaseJourney';
import {CaseEvidence} from '../cases/CaseEvidence';
import {SourceViewer} from '../cases/SourceViewer';
import {InvestigationControls} from '../investigations/InvestigationControls';
import {FindingsView} from '../investigations/FindingsView';
import {WhatChanged} from '../investigations/WhatChanged';
import {Timeline} from '../investigations/Timeline';
import {DraftReview} from '../reviews/DraftReview';
import {OwnerDecisions} from '../history/OwnerDecisions';
import {CaseHistory} from '../history/CaseHistory';
import {AgentTrace} from '../agents/AgentTrace';
import {FeedbackButtons} from '../agents/FeedbackButtons';
import {isPageLoadRoute, routeHref, routeLink, type CaseSection, type Route} from '../routing';
import type {PageProps} from '../store/useWorkspace';
import './pages.css';

// Case sections, each a route value. The earlier in-page tab names still work and open the section showing them.
export const CASE_SECTIONS:readonly CaseSection[]=['overview','evidence','history','compare'];
export type LegacyTab='evidence'|'findings'|'timeline'|'review'|'history';
type Target='suggestion'|'draft'|'timeline'|null;
const LEGACY:Record<LegacyTab,[CaseSection,Target]>={evidence:['evidence',null],timeline:['evidence','timeline'],findings:['overview','suggestion'],review:['overview','draft'],history:['history',null]};
const sectionFor=(route:Route):CaseSection=>route.page==='case'&&route.section?route.section:'overview';

export function CasePage({ws,route,navigate}:PageProps) {
  const {api,selected,refresh,refreshTick}=ws;
  const caseId=route.page==='case'?route.caseId:null;
  const [view,setView]=useState<CaseView|null>(null);const [caseError,setCaseError]=useState('');const [loading,setLoading]=useState(false);
  const caseHeading=useRef<HTMLHeadingElement>(null);
  const pendingFocus=useRef<{did:string;cid:string}|null>(null);
  const [focusRequest,setFocusRequest]=useState(0);
  const [comparisonRequest,setComparisonRequest]=useState<{did:string;cid:string;id:string}|null>(null);
  const [source,setSource]=useState<Evidence|null>(null);const [sourceError,setSourceError]=useState('');const [section,setSection]=useState<CaseSection>(()=>sectionFor(route));const [target,setTarget]=useState<{name:Target;request:number}>({name:null,request:0});const [history,setHistory]=useState<HistoryEvent[]>([]);const [cursor,setCursor]=useState<number|null>(null);
  const navigation=useRef(0);const sourceRequest=useRef(0);const historyGeneration=useRef(0);const historyCursor=useRef<number|null>(null);const historyPagePending=useRef(false);
  const activeScope=useRef('');
  const scopeKey=`${selected ?? ''}:${caseId ?? ''}`;
  if(activeScope.current!==scopeKey){activeScope.current=scopeKey;navigation.current++;}
  // Every navigation to this case is an explicit selection: it resets the section and requests heading focus.
  // The route parsed at page load is not a selection, so a refreshed deep link never moves focus.
  const handledRoute=useRef<Route|null>(null);
  useEffect(()=>{
    if(handledRoute.current===route||route.page!=='case')return;
    handledRoute.current=route;
    if(selected&&!isPageLoadRoute(route)){pendingFocus.current={did:selected,cid:route.caseId};setFocusRequest(value=>value+1);}
    navigation.current++;setSection(sectionFor(route));setSource(null);setSourceError('');
  },[route,selected]);
  useEffect(()=>{if(!selected||!caseId)return;let cancelled=false;setLoading(true);setCaseError('');void api.case(selected,caseId).then(next=>{if(!cancelled)setView(next);}).catch(error=>{if(!cancelled)setCaseError(error.message);}).finally(()=>{if(!cancelled)setLoading(false);});return ()=>{cancelled=true;};},[api,selected,caseId,refreshTick]);
  useEffect(()=>{
    const generation=++historyGeneration.current;
    setHistory([]);setCursor(null);historyCursor.current=null;historyPagePending.current=false;
    if(!selected||!caseId||section!=='history')return;
    let cancelled=false;
    void api.history(selected,caseId).then(next=>{
      if(!cancelled&&generation===historyGeneration.current){setHistory(next.events);setCursor(next.next_cursor);historyCursor.current=next.next_cursor;}
    }).catch(error=>{if(!cancelled&&generation===historyGeneration.current)setCaseError(error.message);});
    return ()=>{cancelled=true;};
  },[api,selected,caseId,section,refreshTick]);
  // Opening a section is not a new navigation: the hash is updated in place so refresh and Back keep it,
  // without resetting the page or moving focus to the case heading.
  function openSection(next:CaseSection,name:Target=null) {
    setSection(next);setTarget(old=>({name,request:old.request+1}));
    if(caseId){const href=routeHref({page:'case',caseId,section:next});if(window.location.hash!==href)window.history.replaceState(window.history.state,'',href);}
  }
  const openLegacy=(tab:LegacyTab)=>openSection(...LEGACY[tab]);
  async function openSource(id:string) {
    if(!selected||!caseId)return;
    const generation=navigation.current;const request=++sourceRequest.current;const did=selected;const cid=caseId;
    setSourceError('');
    try {
      const exact=await api.evidence(did,id);
      if(navigation.current===generation&&sourceRequest.current===request&&exact.demonstration_id===did&&exact.case_id===cid)setSource(exact);
    }catch(error){if(navigation.current===generation&&sourceRequest.current===request)setSourceError(error instanceof Error?error.message:'Source unavailable.');}
  }
  async function moreHistory() {
    if(!selected||!caseId||cursor===null||historyPagePending.current)return;
    const generation=historyGeneration.current;const navigationId=navigation.current;const requestedCursor=cursor;
    historyPagePending.current=true;
    try {
      const next=await api.history(selected,caseId,requestedCursor);
      if(generation===historyGeneration.current&&navigationId===navigation.current&&historyCursor.current===requestedCursor){setHistory(old=>[...old,...next.events]);setCursor(next.next_cursor);historyCursor.current=next.next_cursor;}
    }catch(error){if(generation===historyGeneration.current&&navigationId===navigation.current)setCaseError(error instanceof Error?error.message:'History unavailable.');}
    finally{if(generation===historyGeneration.current)historyPagePending.current=false;}
  }
  const currentView=view?.id===caseId&&view.demonstration_id===selected?view:null;
  useEffect(()=>{
    const request=pendingFocus.current;
    if(!request||!currentView||request.did!==currentView.demonstration_id||request.cid!==currentView.id)return;
    pendingFocus.current=null;
    caseHeading.current?.focus({preventScroll:true});
    caseHeading.current?.scrollIntoView?.({block:'start',behavior:'auto'});
  },[currentView,focusRequest]);
  useEffect(()=>{
    if(!target.name)return;
    const element=document.getElementById(`case-${target.name}`);
    element?.focus({preventScroll:true});element?.scrollIntoView?.({block:'start',behavior:'auto'});
  },[target]);
  useEffect(()=>{
    const reviewAt=currentView?.current_result?.review_at;
    if(currentView?.clock_mode!=='REAL'||!reviewAt)return;
    const remaining=Date.parse(reviewAt)-Date.parse(currentView.evaluation_at);
    if(remaining<=0)return;
    const timer=setTimeout(refresh,Math.min(remaining,2_147_483_647));
    return ()=>clearTimeout(timer);
  },[currentView,refresh]);
  // A deep link to a case of another or deleted workspace explains itself instead of showing a blank page.
  const missing=!ws.discovering&&!ws.discoveryError&&(!selected||(!!ws.list&&!ws.list.cases.some(item=>item.id===caseId)));
  if(missing)return <section className="case-missing">
    <h1>This case isn't in the current workspace</h1>
    <p>It may belong to another saved workspace, or its workspace was deleted. Choose a workspace above or open the case list.</p>
    <p><a {...routeLink({page:'cases'},navigate)}>Back to Cases</a></p>
  </section>;
  const error=caseError||ws.listError;
  const summary=ws.list?.cases.find(item=>item.id===caseId);
  const completed=currentView?.latest_completed_result??null;
  const shown:CaseSection=section==='compare'&&!completed?'overview':section;
  const onSource=(id:string)=>void openSource(id);
  const check=currentView&&<section className="pk-card case-check" aria-labelledby="case-check-heading">
    <h2 id="case-check-heading">Check this case</h2>
    <InvestigationControls key={`${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/>
    <CaseJourney view={currentView} active={shown==='evidence'?'evidence':shown==='overview'?'findings':''} onNavigate={openLegacy}/>
  </section>;
  return <>
    <div className="case-workspace case-page">{!currentView&&<header className="case-heading"><h1>Case</h1></header>}{error&&<div role="alert" className="notice"><p>{error}</p><button onClick={refresh}>Refresh saved case</button></div>}{loading&&<p role="status">Loading saved case…</p>}
    {currentView&&<>
      <nav className="crumbs" aria-label="Breadcrumb"><a {...routeLink({page:'cases'},navigate)}>All cases</a><span aria-hidden="true">›</span><span>{currentView.client} · {currentView.invoice_id}</span></nav>
      <header className="case-heading pk-card">
        <Avatar name={currentView.client} size="lg"/>
        <div className="case-head-main">
          <p className="case-code-line">{currentView.catalogue_case_id} / {currentView.invoice_id} / {currentView.lifecycle}</p>
          <div className="case-title"><h1 ref={caseHeading} tabIndex={-1}>{currentView.client}</h1><CaseChip item={{lifecycle:currentView.lifecycle,recommended_action:summary?.recommended_action??(currentView.freshness==='CURRENT'?currentView.current_result?.action??null:null),review_required:currentView.review_required,review_at:summary?.review_at??null}} evaluationAt={ws.evaluationAt??currentView.evaluation_at}/></div>
          <p className="case-meta">Invoice {currentView.invoice_id} · Due {summary?.due_text??'date unknown'}{summary?.currency&&summary.currency!=='INR'?` · ${summary.currency}`:''}</p>
          <details className="case-record"><summary>Case record details</summary><p className="subtle">Business time {instant(currentView.evaluation_at)} · revision {currentView.case_revision}</p></details>
        </div>
        <ul className="case-money" aria-label="Money for this invoice">
          <li><span>Invoice</span><strong>{money(currentView.financial_facts.invoice)}</strong></li>
          <li><span>Received</span><strong>{money(currentView.financial_facts.paid)}</strong><small>verified payments</small></li>
          <li className="case-money-due"><span>Still to collect</span><strong>{money(currentView.financial_facts.balance)}</strong><small>{words(summary?.balance_label??(currentView.financial_facts.certainty==='KNOWN'?'VERIFIED_REMAINDER':'UNKNOWN_REMAINDER'))}</small></li>
        </ul>
      </header>
      {currentView.review_required&&<p className="notice">Review required: {currentView.review_required_reasons.map(words).join(', ')}.</p>}
      <nav className="view-tabs case-tabs" aria-label="Case sections">{CASE_SECTIONS.filter(item=>item!=='compare'||completed).map(item=><button key={item} onClick={()=>openSection(item)} aria-current={shown===item?'page':undefined}>{item==='evidence'?`Evidence (${currentView.evidence.length})`:item[0].toUpperCase()+item.slice(1)}</button>)}</nav>
      <div className="view-content">
        {shown==='overview'&&<div className="case-grid">
          <div className="case-column">
            <CaseStory view={currentView} onSource={onSource}/>
            <KeyFacts view={currentView}/>
          </div>
          <div className="case-column">
            <div id="case-suggestion" className="case-anchor" tabIndex={-1}>{completed?<><FindingsView result={completed} view={currentView} onSource={onSource} onNavigate={openLegacy} actions={<OwnerDecisions contextual key={`findings-owner:${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/>} team={<AgentTrace key={`trace:${completed.investigation_id}`} api={api} did={currentView.demonstration_id} investigationId={completed.investigation_id}/>}/><FeedbackButtons key={`feedback:${completed.investigation_id}`} api={api} did={currentView.demonstration_id} cid={currentView.id} investigationId={completed.investigation_id} target="RECOMMENDATION"/></>
              :<section className="pk-card suggestion-empty" aria-labelledby="no-suggestion-heading"><p className="suggestion-eyebrow">Our suggestion</p><h2 id="no-suggestion-heading">No suggestion yet</h2><p>Inspect saved evidence or choose Investigate case to begin. Your assistant reads the records and suggests one next step.</p></section>}</div>
            <div id="case-draft" className="case-anchor pk-card" tabIndex={-1}><DraftReview key={`${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/></div>
            {check}
          </div>
        </div>}
        {shown==='evidence'&&<div className="case-grid case-grid-evidence">
          <div className="case-column"><div className="pk-card"><CaseEvidence view={currentView} onSource={onSource}/></div></div>
          <div className="case-column">
            <div id="case-timeline" className="case-anchor pk-card" tabIndex={-1}><Timeline evidence={currentView.evidence} onSource={onSource}/></div>
            {check}
          </div>
        </div>}
        {shown==='history'&&<div className="case-grid case-grid-history">
          <div className="case-column">
          <div className="pk-card"><OwnerDecisions key={`owner:${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/></div>
            {check}
          </div>
          <div className="case-column"><div className="pk-card"><CaseHistory key={`history:${selected}:${caseId}`} api={api} view={currentView} events={history} cursor={cursor} onMore={()=>void moreHistory()} onSource={onSource} onCompare={id=>{setComparisonRequest({did:currentView.demonstration_id,cid:currentView.id,id});openSection('compare');}}/></div></div>
        </div>}
        {shown==='compare'&&completed&&<div className="case-stack"><div className="pk-card"><WhatChanged api={api} view={currentView} onSource={onSource} initialInvestigationId={comparisonRequest?.did===selected&&comparisonRequest.cid===caseId?comparisonRequest.id:undefined}/></div></div>}
      </div>
    </>}</div>
    {sourceError&&<p className="notice" role="alert">{sourceError}</p>}
    {source&&<SourceViewer source={source} onClose={()=>setSource(null)}/>}
  </>;
}
