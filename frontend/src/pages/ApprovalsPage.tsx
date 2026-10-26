import {useEffect, useRef, useState, type RefObject} from 'react';
import type {CaseView, Evidence} from '../api/types';
import {money, words} from '../components/format';
import {CaseEvidence, FinancialSummary} from '../cases/CaseEvidence';
import {attentionOrder} from '../cases/caseStatus';
import {SourceViewer} from '../cases/SourceViewer';
import {OwnerDecisions} from '../history/OwnerDecisions';
import {DraftReview} from '../reviews/DraftReview';
import {hasCurrentResult, KIND_CHIP, KIND_ORDER, parseItemId, type ApprovalItem, type ApprovalKind} from '../approvals/queue';
import {useApprovalQueue} from '../approvals/useApprovalQueue';
import {isPageLoadRoute, routeLink} from '../routing';
import type {PageProps, Workspace} from '../store/useWorkspace';
import {WorkspaceStatus} from './WorkspaceStatus';
import '../approvals/approvals.css';

type Filter='ALL'|ApprovalKind;
const FILTER_LABEL:Record<Filter,string>={ALL:'All',REMINDER:'Reminders',CLOSURE:'Closures',PAYMENT_CHECK:'Payments',SUGGESTION:'Suggestions'};
const CHIP_TONE:Record<ApprovalKind,string>={REMINDER:'indigo',CLOSURE:'green',PAYMENT_CHECK:'amber',SUGGESTION:'violet'};

export function initials(name:string) {
  const parts=name.trim().split(/\s+/).filter(Boolean);
  return ((parts[0]?.[0]??'?')+(parts.length>1?parts[parts.length-1][0]:'')).toUpperCase();
}

export function ApprovalsPage({ws,route,navigate}:PageProps) {
  const {items,failed}=useApprovalQueue(ws);
  // While the shared store refreshes after a decision, keep this workspace's last queue so the open decision stays mounted.
  const last=useRef<{did:string|null;items:ApprovalItem[]}|null>(null);
  if(items)last.current={did:ws.selected,items};
  const kept=items??(last.current?.did===ws.selected?last.current.items:null);
  // Cases needing attention first, in the supervisor's plan order, as on the Dashboard and Cases pages.
  const rank=new Map(attentionOrder(ws.list?.cases??[],ws.evaluationAt,ws.plan).map((item,index)=>[item.id,index]));
  const shown=kept?[...kept].sort((a,b)=>(rank.get(a.caseId)??Infinity)-(rank.get(b.caseId)??Infinity)):null;
  const [filter,setFilter]=useState<Filter>('ALL');
  const counts=Object.fromEntries(KIND_ORDER.map(kind=>[kind,shown?.filter(item=>item.kind===kind).length??0])) as Record<ApprovalKind,number>;
  const active:Filter=filter!=='ALL'&&counts[filter]?filter:'ALL';
  const listed=shown?.filter(item=>active==='ALL'||item.kind===active)??[];
  // Without an item in the route, the first item is shown and stays open after it is decided.
  const [sticky,setSticky]=useState<{did:string|null;id:string}|null>(null);
  const routeItem=route.page==='approvals'?route.itemId:undefined;
  const stickyId=sticky?.did===ws.selected?sticky.id:undefined;
  const firstId=listed[0]?.id;
  useEffect(()=>{if(!routeItem&&!stickyId&&firstId)setSticky({did:ws.selected,id:firstId});},[routeItem,stickyId,firstId,ws.selected]);
  const selectedId=routeItem??stickyId??firstId;
  const exact=shown?.find(item=>item.id===selectedId)??null;
  const target=selectedId?parseItemId(selectedId):null;
  // After one decision the same case may still have another item waiting (an approved draft's recommendation).
  const waiting=exact??shown?.find(item=>item.caseId===target?.caseId)??null;
  const entry=target?ws.cases.find(item=>item.summary.id===target.caseId):undefined;
  // An item chosen in the app moves focus to its decision; a refreshed deep link does not.
  const detailHeading=useRef<HTMLHeadingElement>(null);
  const focusFor=useRef<unknown>(null);
  useEffect(()=>{
    if(route.page!=='approvals'||!route.itemId||isPageLoadRoute(route)||focusFor.current===route||!entry?.view)return;
    focusFor.current=route;detailHeading.current?.focus({preventScroll:true});
    // The previous decision may have been scrolled far down; start the new one at its heading.
    detailHeading.current?.closest('section')?.scrollIntoView?.({block:'start'});
  },[route,entry?.view]);
  const needsCheck=ws.cases.filter(item=>item.view&&item.view.lifecycle==='OPEN'&&!hasCurrentResult(item.view)).length;
  return <>
    <div className="workspace-intro"><h1>Your approvals</h1><p>Every decision waiting for you, in one place. Approving never sends anything; you copy an approved message to your own tool.</p></div>
    <WorkspaceStatus ws={ws}/>
    {!ws.selected&&!ws.discovering&&<p className="empty-state">Choose or create a workspace to see the decisions waiting for you.</p>}
    {ws.selected&&<div className="approvals-layout">
      <section className="approvals-queue" aria-labelledby="approvals-queue-heading">
        <h2 id="approvals-queue-heading">Waiting for you</h2>
        {shown===null?<p role="status">Loading your approvals…</p>:<>
          {shown.length>0&&<div className="approval-filters" role="group" aria-label="Show">
            {(['ALL',...KIND_ORDER] as Filter[]).filter(kind=>kind==='ALL'||counts[kind]>0).map(kind=>
              <button key={kind} aria-pressed={active===kind} onClick={()=>{setFilter(kind);setSticky(null);}}>{FILTER_LABEL[kind]} <span className="filter-count">{kind==='ALL'?shown.length:counts[kind]}</span></button>)}
          </div>}
          {shown.length===0&&<p className="approvals-empty">Nothing is waiting for you right now.</p>}
          <ul className="approval-items" aria-labelledby="approvals-queue-heading">{listed.map(item=><li key={item.id}>
            <a className="approval-item" {...routeLink({page:'approvals',itemId:item.id},navigate)} aria-current={item.id===waiting?.id?'true':undefined}>
              <span className="approval-avatar" aria-hidden="true">{initials(item.client)}</span>
              <span className="approval-item-body">
                <strong>{item.client}</strong>
                <span className="approval-item-title">{item.title}</span>
                <span className="approval-item-amount">{money(item.amount)} still to collect</span>
              </span>
              <span className={`approval-chip tone-${CHIP_TONE[item.kind]}`}>{KIND_CHIP[item.kind]}</span>
            </a>
          </li>)}</ul>
        </>}
        {failed.length>0&&<div className="notice approvals-failed" role="alert">
          <p>These cases couldn't load, so a decision for them may be missing:</p>
          <ul>{failed.map(item=><li key={item.summary.id}>{item.summary.client} · {item.summary.invoice_id} <span className="subtle">{item.error}</span></li>)}</ul>
          <button onClick={ws.refresh}>Retry loading cases</button>
        </div>}
        {needsCheck>0&&<p className="subtle approvals-fresh">{needsCheck===1?'1 open case needs':`${needsCheck} open cases need`} a fresh check before a decision can wait here. <a {...routeLink({page:'cases'},navigate)}>See cases</a></p>}
      </section>
      <div className="approval-pane">
        {entry?.view&&target?<ApprovalDetail key={selectedId} ws={ws} view={entry.view} kind={target.kind} item={waiting} decided={!exact} heading={detailHeading} navigate={navigate}/>:
          shown&&routeItem?<section className="approval-detail"><h2>This decision isn't waiting for you</h2><p>It may have been decided already or belong to another workspace. Choose an item from the list.</p></section>:
          shown&&shown.length>0?null:shown&&<section className="approval-detail approval-calm"><h2>All caught up</h2><p>Reminder drafts, closures, payment checks and recommendations appear here when a current check needs your decision.</p></section>}
      </div>
    </div>}
  </>;
}

function ApprovalDetail({ws,view,kind,item,decided,heading,navigate}:{ws:Workspace;view:CaseView;kind:ApprovalKind;item:ApprovalItem|null;decided:boolean;heading:RefObject<HTMLHeadingElement|null>;navigate:PageProps['navigate']}) {
  const {api,refresh}=ws;
  const [source,setSource]=useState<Evidence|null>(null);const [sourceError,setSourceError]=useState('');
  const sourceRequest=useRef(0);
  const scope=`${view.demonstration_id}:${view.id}`;
  async function openSource(id:string) {
    const request=++sourceRequest.current;const did=view.demonstration_id;const cid=view.id;setSourceError('');
    try {
      const exact=await api.evidence(did,id);
      if(sourceRequest.current===request&&exact.demonstration_id===did&&exact.case_id===cid)setSource(exact);
    }catch(error){if(sourceRequest.current===request)setSourceError(error instanceof Error?error.message:'Source unavailable.');}
  }
  const result=view.current_result??view.latest_completed_result;
  return <section className="approval-detail" aria-labelledby="approval-detail-heading">
    <header className="approval-detail-head">
      <span className="approval-avatar large" aria-hidden="true">{initials(view.client)}</span>
      <div>
        <p className="approval-detail-kind"><span className={`approval-chip tone-${CHIP_TONE[kind]}`}>{KIND_CHIP[kind]}</span> {view.catalogue_case_id} · invoice {view.invoice_id}</p>
        <h2 id="approval-detail-heading" ref={heading} tabIndex={-1}>{view.client}</h2>
        {item&&<p className="approval-detail-title">{item.title}</p>}
      </div>
      <a className="approval-open-case" {...routeLink({page:'case',caseId:view.id},navigate)}>Open full case →</a>
    </header>
    {decided&&item&&<p className="notice" role="status">The {KIND_CHIP[kind].toLowerCase()} is no longer waiting for you. This case still has {item.kind==='SUGGESTION'?'a recommendation':'another decision'} waiting for you below.</p>}
    {!item&&<p className="notice" role="status">This is no longer waiting for you: it was decided or the case changed. The case stays here so you can check the result or copy an approved message.</p>}
    {item&&<p className="approval-reason">{item.reason}</p>}
    {/* A payment check shows these figures inside its saved evidence. */}
    {result&&kind!=='PAYMENT_CHECK'&&<FinancialSummary facts={{...result.financial_facts,label:words(result.financial_label)}} showIssues={false}/>}
    <div className="approval-decision">
      {kind==='REMINDER'&&<DraftReview key={`${scope}:draft`} api={api} view={view} onRefresh={refresh}/>}
      {kind==='PAYMENT_CHECK'&&<>
        <p className="notice">Verify the evidence before any payment demand. Check your bank statement or accounting records outside PromiseKeeper; this app does not connect to your bank.</p>
        <CaseEvidence view={view} onSource={id=>void openSource(id)}/>
      </>}
      <OwnerDecisions contextual key={`${scope}:owner`} api={api} view={view} onRefresh={refresh}/>
    </div>
    {sourceError&&<p className="notice" role="alert">{sourceError}</p>}
    {source&&<SourceViewer source={source} onClose={()=>setSource(null)}/>}
  </section>;
}
