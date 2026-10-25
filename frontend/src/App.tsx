import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiClient, defaultApi } from './api/client';
import { resolveSelection, selectionKey } from './api/demonstrationSelection';
import { subscribeCommitted } from './api/pendingOperations';
import type { CaseListResponse, CaseView, Catalogue, Demonstration, Evidence, Health, HistoryEvent } from './api/types';
import { StatusBanner } from './components/StatusBanner';
import { instant, words } from './components/format';
import { DemonstrationPicker } from './cases/DemonstrationPicker';
import { CaseList } from './cases/CaseList';
import { CaseJourney } from './cases/CaseJourney';
import { CaseEvidence } from './cases/CaseEvidence';
import { SourceViewer } from './cases/SourceViewer';
import { InvestigationControls } from './investigations/InvestigationControls';
import { FindingsView } from './investigations/FindingsView';
import { Timeline } from './investigations/Timeline';
import { DraftReview } from './reviews/DraftReview';
import { OwnerDecisions } from './history/OwnerDecisions';
import { ScenarioUpdate } from './history/ScenarioUpdate';
import { CaseHistory } from './history/CaseHistory';
import { AgentTrace } from './agents/AgentTrace';
import { AgentRoster } from './agents/AgentRoster';
import { FeedbackButtons } from './agents/FeedbackButtons';
import { MorningReview } from './agents/MorningReview';
export default function App({api=defaultApi}:{api?:ApiClient}) {
  const [health,setHealth]=useState<Health|null>(null);const [catalogue,setCatalogue]=useState<Catalogue|null>(null);
  const [copies,setCopies]=useState<Demonstration[]>([]);const [selected,setSelected]=useState<string|null>(null);const [listing,setListing]=useState(true);const [discoveryError,setDiscoveryError]=useState('');
  const [list,setList]=useState<CaseListResponse|null>(null);const [caseId,setCaseId]=useState<string|null>(null);const [view,setView]=useState<CaseView|null>(null);const [caseError,setCaseError]=useState('');const [loading,setLoading]=useState(false);
  const [overviewCutoff,setOverviewCutoff]=useState<{did:string;at:string}|null>(null);
  const handledReviewBoundary=useRef('');
  const [source,setSource]=useState<Evidence|null>(null);const [sourceError,setSourceError]=useState('');const [tab,setTab]=useState('evidence');const [history,setHistory]=useState<HistoryEvent[]>([]);const [cursor,setCursor]=useState<number|null>(null);
  const navigation=useRef(0);const sourceRequest=useRef(0);const historyGeneration=useRef(0);const historyCursor=useRef<number|null>(null);const historyPagePending=useRef(false);
  const activeScope=useRef('');
  const selectedCopy=useRef(selected);selectedCopy.current=selected;
  const scopeKey=`${selected ?? ''}:${caseId ?? ''}`;
  if(activeScope.current!==scopeKey){activeScope.current=scopeKey;navigation.current++;}
  const [refreshTick,setRefreshTick]=useState(0);const refresh=useCallback(()=>setRefreshTick(value=>value+1),[]);
  function select(id:string) {navigation.current++;selectedCopy.current=id;setSelected(id);localStorage.setItem(selectionKey,id);setCaseId(null);setView(null);setList(null);setSource(null);setSourceError('');setCaseError('');}
  function selectCase(id:string) {
    if(id===caseId)return;
    navigation.current++;setCaseId(id);setView(null);setTab('evidence');setSource(null);setSourceError('');
  }
  const discover=useCallback(async (created?:string)=>{
    setListing(true);setDiscoveryError('');
    try {const response=await api.demonstrations();setCopies(response.demonstrations);const id=resolveSelection(response.demonstrations,created??localStorage.getItem(selectionKey));setSelected(id);if(id)localStorage.setItem(selectionKey,id);else localStorage.removeItem(selectionKey);}
    catch(error){setDiscoveryError(error instanceof Error?error.message:'Saved copies could not be loaded.');}finally{setListing(false);}
  },[api]);
  useEffect(()=>subscribeCommitted(outcome=>{
    if(outcome.command.kind==='deletion'&&outcome.response.receipt.outcome==='DELETED') {
      if(selectedCopy.current===outcome.did) {
        navigation.current++;selectedCopy.current=null;setSelected(null);setCaseId(null);setView(null);setList(null);setSource(null);setSourceError('');setCaseError('');
        if(localStorage.getItem(selectionKey)===outcome.did)localStorage.removeItem(selectionKey);
      }
      void discover();
    }else if(selectedCopy.current===outcome.did)refresh();
  }),[discover,refresh]);
  useEffect(()=>{void discover();void api.health().then(setHealth).catch(()=>setHealth(null));void api.catalogue().then(setCatalogue).catch(()=>setCatalogue(null));},[api,discover]);
  useEffect(()=>{if(!selected)return;let cancelled=false;setLoading(true);setCaseError('');void api.cases(selected).then(next=>{if(cancelled)return;setList(next);setOverviewCutoff({did:next.demonstration_id,at:next.evaluation_at});setCaseId(old=>next.cases.some(item=>item.id===old)?old:next.cases[0]?.id??null);}).catch(error=>{if(!cancelled)setCaseError(error.message);}).finally(()=>{if(!cancelled)setLoading(false);});return ()=>{cancelled=true;};},[api,selected,refreshTick]);
  useEffect(()=>{if(!selected||!caseId)return;let cancelled=false;setLoading(true);setCaseError('');void api.case(selected,caseId).then(next=>{if(!cancelled)setView(next);}).catch(error=>{if(!cancelled)setCaseError(error.message);}).finally(()=>{if(!cancelled)setLoading(false);});return ()=>{cancelled=true;};},[api,selected,caseId,refreshTick]);
  useEffect(()=>{
    const generation=++historyGeneration.current;
    setHistory([]);setCursor(null);historyCursor.current=null;historyPagePending.current=false;
    if(!selected||!caseId||tab!=='history')return;
    let cancelled=false;
    void api.history(selected,caseId).then(next=>{
      if(!cancelled&&generation===historyGeneration.current){setHistory(next.events);setCursor(next.next_cursor);historyCursor.current=next.next_cursor;}
    }).catch(error=>{if(!cancelled&&generation===historyGeneration.current)setCaseError(error.message);});
    return ()=>{cancelled=true;};
  },[api,selected,caseId,tab,refreshTick]);
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
    if(list?.clock_mode!=='REAL')return;
    const reviewTimes=list.cases.flatMap(item=>item.review_at?[Date.parse(item.review_at)]:[]);
    if(!reviewTimes.length)return;
    const evaluated=Date.parse(list.evaluation_at);
    const expired=list.cases.filter(item=>item.review_at&&Date.parse(item.review_at)<=evaluated);
    if(expired.length){
      const key=`${list.demonstration_id}:${expired.map(item=>`${item.id}:${item.review_at}`).join(',')}`;
      if(handledReviewBoundary.current!==key){handledReviewBoundary.current=key;refresh();return;}
    }
    const upcoming=reviewTimes.filter(at=>at>evaluated);
    if(!upcoming.length)return;
    const next=Math.min(...upcoming);const remaining=next-evaluated;
    const delay=Math.min(remaining,2_147_483_647);
    const timer=setTimeout(()=>{setOverviewCutoff({did:list.demonstration_id,at:new Date(evaluated+delay).toISOString()});refresh();},delay);
    return()=>clearTimeout(timer);
  },[list,refresh]);
  useEffect(()=>{
    const reviewAt=currentView?.current_result?.review_at;
    if(currentView?.clock_mode!=='REAL'||!reviewAt)return;
    const remaining=Date.parse(reviewAt)-Date.parse(currentView.evaluation_at);
    if(remaining<=0)return;
    const timer=setTimeout(refresh,Math.min(remaining,2_147_483_647));
    return ()=>clearTimeout(timer);
  },[currentView,refresh]);
  return <><a className="skip-link" href="#main">Skip to case workspace</a><header className="app-header"><a className="wordmark" href="/">PromiseKeeper<span>Evidence before action.</span></a><div className="header-tools"><p className="workspace-label">Agency case workspace</p><AgentRoster health={health}/></div></header><StatusBanner health={health} clock={list?.clock_mode}/><main id="main"><div className="workspace-intro"><h1>Your payment casebook</h1><p>Inspect the record. Find the next responsible step.</p></div>{listing&&<p role="status">Loading saved demonstrations…</p>}{discoveryError?<div className="notice" role="alert"><p>{discoveryError}</p><button onClick={()=>void discover()}>Retry saved-copy discovery</button></div>:!listing&&<DemonstrationPicker api={api} copies={copies} selected={selected} catalogue={catalogue} onSelect={select} onCreated={id=>{select(id);void discover(id);}}/>}{!catalogue&&!listing&&!discoveryError&&<p className="notice">Fixture catalogue unavailable. Refresh to enable explicit creation.</p>}{copies.length>1&&!selected&&!discoveryError&&<p className="empty-state">Choose a saved demonstration to inspect its three cases.</p>}{selected&&<MorningReview key={`morning:${selected}`} api={api} did={selected} onOpenCase={id=>{selectCase(id);setTab('findings');}} onDone={refresh}/>}{selected&&<div className="workspace-grid">{list&&<CaseList cases={list.cases} evaluationAt={overviewCutoff?.did===list.demonstration_id?overviewCutoff.at:list.evaluation_at} selected={caseId} onSelect={selectCase}/>}<div className="case-workspace">{caseError&&<div role="alert" className="notice"><p>{caseError}</p><button onClick={refresh}>Refresh saved case</button></div>}{loading&&<p role="status">Loading saved case…</p>}{currentView&&<><header className="case-heading"><p>{currentView.catalogue_case_id} / {currentView.invoice_id} / {currentView.lifecycle}</p><h2>{currentView.client}</h2><p className="subtle">Business time {instant(currentView.evaluation_at)} · revision {currentView.case_revision}</p>{currentView.review_required&&<p className="notice">Review required: {currentView.review_required_reasons.map(words).join(', ')}.</p>}</header><CaseJourney view={currentView} active={tab} onNavigate={setTab}/><InvestigationControls key={`${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/><nav className="view-tabs" aria-label="Case sections">{['evidence','findings','timeline','review','history'].map(item=><button key={item} onClick={()=>setTab(item)} aria-current={tab===item?'page':undefined}>{item[0].toUpperCase()+item.slice(1)}</button>)}</nav><div className="view-content">{tab==='evidence'&&<CaseEvidence view={currentView} onSource={id=>void openSource(id)}/>} {tab==='findings'&&(currentView.latest_completed_result?<><FindingsView result={currentView.latest_completed_result} view={currentView} onSource={id=>void openSource(id)} onNavigate={setTab} actions={<OwnerDecisions contextual key={`findings-owner:${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/>} team={<AgentTrace key={`trace:${currentView.latest_completed_result.investigation_id}`} api={api} did={currentView.demonstration_id} investigationId={currentView.latest_completed_result.investigation_id}/>}/><FeedbackButtons key={`feedback:${currentView.latest_completed_result.investigation_id}`} api={api} did={currentView.demonstration_id} cid={currentView.id} investigationId={currentView.latest_completed_result.investigation_id} target="RECOMMENDATION"/></>:<section className="empty-state"><h2>No completed investigation</h2><p>Inspect saved evidence or choose Investigate case to begin.</p></section>)}{tab==='timeline'&&<Timeline evidence={currentView.evidence} onSource={id=>void openSource(id)}/>} {tab==='review'&&<DraftReview key={`${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/>} {tab==='history'&&<><OwnerDecisions key={`owner:${selected}:${caseId}`} api={api} view={currentView} onRefresh={refresh}/><ScenarioUpdate key={`scenario:${selected}:${caseId}`} api={api} view={currentView} events={catalogue?.events??[]} selectedVariantId={copies.find(copy=>copy.id===selected)?.selected_variant_id} onRefresh={refresh}/><CaseHistory key={`history:${selected}:${caseId}`} api={api} view={currentView} events={history} cursor={cursor} onMore={()=>void moreHistory()} onSource={id=>void openSource(id)}/></>}</div></>}</div></div>}{sourceError&&<p className="notice" role="alert">{sourceError}</p>}</main><footer>Fictional demonstration. No customer messages are sent.</footer>{source&&<SourceViewer source={source} onClose={()=>setSource(null)}/>}</>;
}
