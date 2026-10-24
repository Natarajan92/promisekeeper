import { useEffect, useRef, useState } from 'react';
import type { ApiClient } from '../api/client';
import type { CaseView, DraftVersion, HistoryEvent, Result } from '../api/types';
import { instant, money, words } from '../components/format';
import { FindingsView } from '../investigations/FindingsView';

export function CaseHistory({api,view,events,cursor,onMore,onSource}:{api:ApiClient;view:CaseView;events:HistoryEvent[];cursor:number|null;onMore:()=>void;onSource:(id:string)=>void}) {
  const [draft,setDraft]=useState<DraftVersion|null>(null),[result,setResult]=useState<Result|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(false);
  const request=useRef(0),scope=useRef('');
  const active=`${view.demonstration_id}:${view.id}`;
  if(scope.current!==active){scope.current=active;request.current++;}
  useEffect(()=>{setDraft(null);setResult(null);setError('');return()=>{request.current++;};},[active]);
  async function inspect(kind:'draft'|'result',id:string){
    const ticket=++request.current;setError('');setLoading(true);
    try{
      if(kind==='draft'){
        const response=await api.request<{schema_version:'1';draft_version:DraftVersion}>(`/draft-versions/${encodeURIComponent(id)}?demonstration_id=${encodeURIComponent(view.demonstration_id)}`);
        if(ticket===request.current){if(response.draft_version.case_id&&response.draft_version.case_id!==view.id)throw new Error('This historical draft belongs to another case.');setDraft(response.draft_version);}
      }else{
        const response=await api.attempt(view.demonstration_id,id);
        if(ticket===request.current){if(response.case_id&&response.case_id!==view.id)throw new Error('This historical investigation belongs to another case.');if(response.result)setResult(response.result);else throw new Error('This investigation has no completed result.');}
      }
    }catch(failure){if(ticket===request.current)setError(failure instanceof Error?failure.message:'History unavailable.');}finally{if(ticket===request.current)setLoading(false);}
  }
  const ref=(event:HistoryEvent,key:string)=>typeof event.payload[key]==='string'?event.payload[key] as string:null;
  const sources=result?Array.from(new Set([...(result.timeline??[]).map(source=>source.evidence_version_id),...(result.financial_facts.issues??[]).flatMap(issue=>issue.source_versions?.map(source=>source.evidence_version_id)??[])])):[];
  return <section aria-labelledby="saved-history-heading"><h2 id="saved-history-heading">Saved history</h2><p className="subtle">Immutable events in server sequence. Arrival history is separate from the evidence timeline. Current case: {view.lifecycle}, revision {view.case_revision}.</p>
    <ol className="history-list">{events.map(event=><li key={event.id}><strong>{words(event.event_type)}</strong><p>Sequence {event.sequence} · recorded {instant(event.occurred_at)}</p><div className="decision-actions">{ref(event,'investigation_id')&&<button onClick={()=>void inspect('result',ref(event,'investigation_id')!)}>Inspect investigation</button>}{ref(event,'draft_version_id')&&<button onClick={()=>void inspect('draft',ref(event,'draft_version_id')!)}>Inspect saved draft</button>}{ref(event,'evidence_version_id')&&<button onClick={()=>onSource(ref(event,'evidence_version_id')!)}>Inspect historical source</button>}</div>{ref(event,'draft_review_id')&&view.draft_reviews?.filter(review=>review.id===ref(event,'draft_review_id')).map(review=><details key={review.id}><summary>Inspect exact draft review</summary><p>Historical decision: {words(review.decision)} at {instant(review.decided_at)}</p><p>{review.recipient} / invoice {review.invoice_id} / review epoch {review.review_epoch}</p><pre>{review.exact_text}</pre><p className="source-name">Payload hash {review.payload_hash}</p></details>)}<details><summary>Event details</summary><pre>{JSON.stringify(event.payload,null,2)}</pre></details></li>)}</ol>
    {!events.length&&<p>No saved history events.</p>}{cursor!==null&&<button onClick={onMore}>Load earlier history</button>}
    {loading&&<p role="status">Loading historical record…</p>}{error&&<p role="alert" className="notice">{error}</p>}
    {draft&&<article className="historical-record"><h3>Historical saved draft</h3><p>{draft.recipient} / invoice {draft.invoice_id} / version {draft.version}. {draft.id===view.current_draft_version_id?'This is also the current saved draft.':'This is a prior version.'}</p><pre>{draft.exact_text}</pre><p className="source-name">Saved {instant(draft.created_at)}; investigation {draft.investigation_id}; payload hash {draft.payload_hash}</p></article>}
    {result&&<article className="historical-record"><h3>Historical recommendation: {result.action}</h3><p>Original evaluation {instant(result.evaluation_at)}; balance at that evaluation {money(result.financial_facts.balance)}.</p><p>{result.investigation_id===view.current_result?.investigation_id?'This is also the current investigation.':'This historical recommendation does not replace the current case state.'}</p><p className="source-name">Investigation {result.investigation_id}; result hash {result.result_hash}</p><ul>{(result.timeline??[]).map((source,index)=><li key={`${source.evidence_version_id}:${index}`}>{source.source_id}: evidence time {instant(source.event_at)}; arrival {instant(source.arrived_at)}.</li>)}</ul><div className="source-links">{sources.map(id=><button key={id} onClick={()=>onSource(id)}>Inspect historical source {result.timeline?.find(source=>source.evidence_version_id===id)?.source_id??view.evidence.find(source=>source.id===id)?.stable_source_id??id}</button>)}</div><FindingsView result={result} view={{...view,evaluation_at:result.evaluation_at,freshness:'HISTORICAL_SNAPSHOT'}} onSource={onSource}/></article>}
  </section>;
}
