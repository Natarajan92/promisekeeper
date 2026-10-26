import {useCallback, useEffect, useRef, useState} from 'react';
import type {ApiClient} from '../api/client';
import {resolveSelection, selectionKey} from '../api/demonstrationSelection';
import {subscribeCommitted} from '../api/pendingOperations';
import type {CaseListResponse, CaseSummary, CaseView, Demonstration, Health} from '../api/types';
import {clearIntakeState} from '../intake/commands';
import type {Route} from '../routing';

export interface CaseEntry {summary:CaseSummary; view:CaseView|null; error:string|null}
export interface Workspace {
  api:ApiClient; health:Health|null;
  copies:Demonstration[]; selected:string|null; imported:boolean; discovering:boolean; discoveryError:string;
  list:CaseListResponse|null; evaluationAt:string|undefined; plan:Record<string,number>;
  cases:CaseEntry[]; detailsLoading:boolean; refreshTick:number;
  /** Case-list load state for the selected workspace (additive to the planned interface). */
  listLoading:boolean; listError:string;
  select(id:string|null):void; discover(created?:string):Promise<void>; refresh():void; setPlan(p:Record<string,number>):void;
}
export interface PageProps {ws:Workspace; route:Route; navigate:(r:Route)=>void}

const failure=(error:unknown,fallback:string)=>error instanceof Error?error.message:fallback;

// Owns everything the single-page App did for the workspace: discovery, the case list, every case view,
// review-boundary timers for REAL clock, committed-operation reconciliation and deletion.
export function useWorkspace(api:ApiClient):Workspace {
  const [health,setHealth]=useState<Health|null>(null);
  const [copies,setCopies]=useState<Demonstration[]>([]);const [selected,setSelected]=useState<string|null>(null);
  const [discovering,setDiscovering]=useState(true);const [discoveryError,setDiscoveryError]=useState('');
  const [list,setList]=useState<CaseListResponse|null>(null);const [listLoading,setListLoading]=useState(false);const [listError,setListError]=useState('');
  const [plan,setPlan]=useState<Record<string,number>>({});
  const [overviewCutoff,setOverviewCutoff]=useState<{did:string;at:string}|null>(null);
  const [views,setViews]=useState<{did:string;entries:Record<string,{view:CaseView|null;error:string|null}>}>({did:'',entries:{}});
  const [detailsLoading,setDetailsLoading]=useState(false);
  const handledReviewBoundary=useRef('');
  const selectedCopy=useRef(selected);selectedCopy.current=selected;
  const [refreshTick,setRefreshTick]=useState(0);const refresh=useCallback(()=>setRefreshTick(value=>value+1),[]);
  const clear=useCallback(()=>{setList(null);setListError('');setViews({did:'',entries:{}});},[]);
  const select=useCallback((id:string|null)=>{
    selectedCopy.current=id;setSelected(id);
    if(id)localStorage.setItem(selectionKey,id);else localStorage.removeItem(selectionKey);
    clear();
  },[clear]);
  const discover=useCallback(async (created?:string)=>{
    setDiscovering(true);setDiscoveryError('');
    try {const response=await api.demonstrations();setCopies(response.demonstrations);const id=resolveSelection(response.demonstrations,created??localStorage.getItem(selectionKey));setSelected(id);if(id)localStorage.setItem(selectionKey,id);else localStorage.removeItem(selectionKey);}
    catch(error){setDiscoveryError(failure(error,'Saved workspaces could not be loaded.'));}finally{setDiscovering(false);}
  },[api]);
  useEffect(()=>subscribeCommitted(outcome=>{
    if(outcome.command.kind==='deletion'&&outcome.response.receipt.outcome==='DELETED') {
      clearIntakeState(outcome.did);
      if(selectedCopy.current===outcome.did) {
        selectedCopy.current=null;setSelected(null);clear();
        if(localStorage.getItem(selectionKey)===outcome.did)localStorage.removeItem(selectionKey);
      }
      void discover();
    }else if(selectedCopy.current===outcome.did)refresh();
  }),[discover,refresh,clear]);
  useEffect(()=>{void discover();void api.health().then(setHealth).catch(()=>setHealth(null));},[api,discover]);
  useEffect(()=>{
    if(!selected)return;
    let cancelled=false;setListLoading(true);setListError('');
    void api.cases(selected).then(next=>{if(cancelled)return;setList(next);setOverviewCutoff({did:next.demonstration_id,at:next.evaluation_at});})
      .catch(error=>{if(!cancelled)setListError(failure(error,'Saved cases could not be loaded.'));})
      .finally(()=>{if(!cancelled)setListLoading(false);});
    return ()=>{cancelled=true;};
  },[api,selected,refreshTick]);
  // Every case view loads in parallel; one failure is kept on its own entry and never hides the others.
  useEffect(()=>{
    if(!selected||list?.demonstration_id!==selected)return;
    let cancelled=false;const did=selected;
    setViews(old=>old.did===did?old:{did,entries:{}});
    if(!list.cases.length){setDetailsLoading(false);return;}
    setDetailsLoading(true);
    void Promise.all(list.cases.map(item=>api.case(did,item.id).then(
      view=>{if(!cancelled)setViews(old=>old.did===did?{did,entries:{...old.entries,[item.id]:{view,error:null}}}:old);},
      error=>{if(!cancelled)setViews(old=>old.did===did?{did,entries:{...old.entries,[item.id]:{view:null,error:failure(error,'Saved case could not be loaded.')}}}:old);},
    ))).finally(()=>{if(!cancelled)setDetailsLoading(false);});
    return ()=>{cancelled=true;};
  },[api,selected,list]);
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
  const current=list?.demonstration_id===selected?list:null;
  const entries=views.did===selected?views.entries:{};
  const cases:CaseEntry[]=current?current.cases.map(summary=>({summary,view:entries[summary.id]?.view?.id===summary.id?entries[summary.id].view:null,error:entries[summary.id]?.error??null})):[];
  return {
    api,health,copies,selected,discovering,discoveryError,
    imported:copies.find(copy=>copy.id===selected)?.selected_variant_id==='csv-demo',
    list:current,evaluationAt:current?(overviewCutoff?.did===current.demonstration_id?overviewCutoff.at:current.evaluation_at):undefined,
    plan,cases,detailsLoading:!!current&&detailsLoading,refreshTick,listLoading,listError,
    select,discover,refresh,setPlan,
  };
}
