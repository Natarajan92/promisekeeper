import {useEffect,useId,useRef,useState} from 'react';
import type {ApiClient} from '../api/client';
import type {Attempt,CaseView,HistoryEvent,Result} from '../api/types';
import {actionTitle,instant,money,words} from '../components/format';
import {compareResults,completedInvestigations} from './comparison';
import {FindingsView} from './FindingsView';

type Props={api:ApiClient;view:CaseView;onSource:(id:string)=>void;initialInvestigationId?:string};
type Discovery={events:HistoryEvent[];cursor:number|null};
type Pair={before:Result;after:Result};

export function WhatChanged(props:Props){
  return <ComparisonPanel key={`${props.view.demonstration_id}:${props.view.id}`} {...props}/>;
}

function ComparisonPanel({api,view,onSource,initialInvestigationId}:Props){
  const heading=useId(),content=useId();
  const headingRef=useRef<HTMLHeadingElement>(null);
  const [opened,setOpened]=useState(!!initialInvestigationId),[refresh,setRefresh]=useState(0);
  const [discovery,setDiscovery]=useState<Discovery|null>(null),[historyLoading,setHistoryLoading]=useState(false),[error,setError]=useState('');
  const [older,setOlder]=useState(''),[newer,setNewer]=useState(''),[pair,setPair]=useState<Pair|null>(null),[pairLoading,setPairLoading]=useState(false);
  const [original,setOriginal]=useState<'before'|'after'|null>(null);
  const historyRequest=useRef(0);
  const did=view.demonstration_id,cid=view.id;
  const ids=discovery?completedInvestigations(discovery.events,did,cid):[];
  const validChoice=ids.indexOf(older)>=0&&ids.indexOf(older)<ids.indexOf(newer);
  function choiceLabel(id:string,index:number){
    const event=discovery?.events.find(item=>item.event_type==='INVESTIGATION_COMPLETED'&&item.payload.investigation_id===id);
    return `Saved result ${index+1} · completed ${instant(event?.occurred_at)}`;
  }

  function checkPage(page:Discovery,previous?:number){
    completedInvestigations(page.events,did,cid);
    if(page.cursor!==null&&(!Number.isSafeInteger(page.cursor)||page.cursor<=(previous??0)))throw new Error('Comparison history did not advance. Inspect saved History or refresh.');
  }
  useEffect(()=>{
    if(initialInvestigationId){setOpened(true);headingRef.current?.focus();headingRef.current?.scrollIntoView?.({block:'start'});}
  },[initialInvestigationId]);
  useEffect(()=>{
    if(!opened)return;
    const ticket=++historyRequest.current;
    setHistoryLoading(true);setError('');setDiscovery(null);setPair(null);setOriginal(null);setOlder('');setNewer('');
    void (async()=>{
      const events:HistoryEvent[]=[];let cursor:number|undefined;
      for(let pageNumber=0;pageNumber<3;pageNumber++){
        const response=await api.history(did,cid,cursor);
        if(ticket!==historyRequest.current)return;
        const page={events:response.events,cursor:response.next_cursor};checkPage(page,cursor);
        events.push(...page.events);
        if(page.cursor===null){cursor=undefined;break;}
        cursor=page.cursor;
      }
      if(ticket!==historyRequest.current)return;
      const found=completedInvestigations(events,did,cid);
      setDiscovery({events,cursor:cursor??null});
      const requested=initialInvestigationId?found.indexOf(initialInvestigationId):-1;
      if(requested>=0&&requested<found.length-1){setOlder(found[requested]);setNewer(found.at(-1)??'');}
      else {setOlder(found.at(-2)??'');setNewer(found.at(-1)??'');}
    })().catch(failure=>{if(ticket===historyRequest.current)setError(failure instanceof Error?failure.message:'Comparison history is unavailable.');})
      .finally(()=>{if(ticket===historyRequest.current)setHistoryLoading(false);});
    return()=>{historyRequest.current++;};
  },[api,did,cid,opened,refresh,initialInvestigationId]);

  useEffect(()=>{
    setPair(null);setOriginal(null);
    if(!validChoice){setPairLoading(false);return;}
    let cancelled=false;setPairLoading(true);setError('');
    function validate(record:Attempt,id:string){
      if(record.demonstration_id!==did||record.case_id!==cid||record.id!==id||record.investigation_id!==id)throw new Error('Investigation belongs to another workspace, case or saved identity.');
      if(!['COMPLETE','LIMITED'].includes(record.status)||!record.result||record.result.status!==record.status)throw new Error('This investigation has no completed result.');
      if(record.result.investigation_id!==id||record.result.snapshot_id!==record.snapshot_id||record.result.snapshot_hash!==record.snapshot_hash)throw new Error('Saved result identity does not match its investigation.');
      return record.result;
    }
    void Promise.all([api.attempt(did,older),api.attempt(did,newer)]).then(([left,right])=>{
      if(!cancelled)setPair({before:validate(left,older),after:validate(right,newer)});
    }).catch(failure=>{if(!cancelled)setError(failure instanceof Error?failure.message:'Saved comparison is unavailable.');})
      .finally(()=>{if(!cancelled)setPairLoading(false);});
    return()=>{cancelled=true;};
  },[api,did,cid,older,newer,validChoice,refresh]);

  async function more(){
    if(!discovery||discovery.cursor===null||historyLoading)return;
    const ticket=historyRequest.current;setHistoryLoading(true);setError('');
    try{
      const response=await api.history(did,cid,discovery.cursor);
      if(ticket!==historyRequest.current)return;
      const page={events:response.events,cursor:response.next_cursor};checkPage(page,discovery.cursor);
      setDiscovery({events:[...discovery.events,...page.events],cursor:page.cursor});
    }catch(failure){if(ticket===historyRequest.current)setError(failure instanceof Error?failure.message:'More history is unavailable.');}
    finally{if(ticket===historyRequest.current)setHistoryLoading(false);}
  }
  const selected=pair?.before.investigation_id===older&&pair?.after.investigation_id===newer&&validChoice?pair:null;
  const diff=selected?compareResults(selected.before,selected.after):null;
  const latest=!!selected&&discovery?.cursor===null&&newer===ids.at(-1)&&older===ids.at(-2)&&view.latest_completed_result?.investigation_id===newer;
  const laterIncomplete=discovery?.events.some(event=>event.event_type==='INVESTIGATION_INCOMPLETE'&&event.sequence>Math.max(...discovery.events.filter(item=>item.event_type==='INVESTIGATION_COMPLETED').map(item=>item.sequence)));
  function values(result:Result,label:string){
    return <article className="comparison-side"><h4>{label}</h4><p>Evaluated {instant(result.evaluation_at)} · {words(result.status)}</p>
      <dl aria-label={`${label} values`}>
        <div><dt>Recorded recommendation</dt><dd>{actionTitle(result.action)}</dd></div>
        <div><dt>{words(result.financial_label)}</dt><dd>{money(result.financial_facts.balance)}</dd></div>
        <div><dt>Financial certainty</dt><dd>{words(result.financial_facts.certainty)}</dd></div>
        <div><dt>Invoice</dt><dd>{money(result.financial_facts.invoice)}</dd></div>
        <div><dt>Verified payments</dt><dd>{money(result.financial_facts.paid)}</dd></div>
        <div><dt>Invoice due boundary</dt><dd>{instant(result.financial_facts.due_at)}</dd></div>
        <div><dt>Review boundary</dt><dd>{result.review_at?instant(result.review_at):'No saved review date'}</dd></div>
        <div><dt>Recorded reason</dt><dd>{words(result.reason_code)}</dd></div>
      </dl>
      {result.financial_label==='RECORDED_REMAINDER'&&result.claims.some(claim=>!claim.resolved)&&<p className="notice">Payment claim unresolved; the recorded remainder is contested.</p>}
      <details><summary>Saved identity and exact codes</summary><p>Investigation {result.investigation_id}</p><p>Action {result.action}; reason {result.reason_code}</p><p>Result hash {result.result_hash}</p><p>Findings profile {result.findings_version??'legacy'}</p></details>
    </article>;
  }
  const summary=diff?.kind==='action'?'Recommendation changed':diff?.kind==='evidence'?'Same recommendation; evidence changed':diff?.kind==='findings'?'Same recommendation; saved findings changed':diff?.kind==='time'?'Only evaluation time changed':diff?.kind==='identical'?'No material change in comparable saved findings':'Comparison limited';
  return <section className="what-changed" aria-labelledby={heading}>
    <h3 id={heading} ref={headingRef} tabIndex={-1}>What changed</h3>
    <p>Compare saved investigations and inspect the evidence behind each result.</p>
    <button aria-expanded={opened} aria-controls={content} onClick={()=>setOpened(value=>!value)}>{opened?'Hide comparison':'Compare saved investigations'}</button>
    {opened&&<div id={content}>
      <p className="subtle">Read-only comparison. Recorded advice does not authorize a new action or close this case.</p>
      <button disabled={historyLoading} onClick={()=>setRefresh(value=>value+1)}>Refresh comparison history</button>
      {historyLoading&&<p role="status">Loading saved comparison history…</p>}
      {error&&<p role="alert" className="notice">{error} Saved Findings and History remain available.</p>}
      {discovery&&<>
        {initialInvestigationId&&!ids.includes(initialInvestigationId)&&<p className="notice">Requested investigation is not among the loaded completed records. Inspect History or load more records before selecting it.</p>}
        {discovery.cursor!==null&&<p className="notice">Partial history: the latest pair has not been established. Choose from loaded records or load more history.</p>}
        {discovery.cursor!==null&&<button disabled={historyLoading} onClick={()=>void more()}>Load more comparison history</button>}
        {ids.length<2?<p>Two completed investigations are needed. {discovery.cursor===null?'No comparison is available in this history.':'More records may be on later pages.'}</p>:<>
          <div className="comparison-selectors">{(['Earlier','Later'] as const).map(label=><label key={label}>{label} investigation<select aria-label={`${label} investigation`} value={label==='Earlier'?older:newer} onChange={event=>label==='Earlier'?setOlder(event.target.value):setNewer(event.target.value)}><option value="">Choose investigation</option>{ids.map((id,index)=><option key={id} value={id}>{choiceLabel(id,index)}</option>)}</select></label>)}</div>
          {!validChoice&&<p className="notice">Choose two distinct investigations in completion order.</p>}
        </>}
      </>}
      {view.running_attempt&&<p className="notice">Newer attempt is still running. It does not replace either completed result.</p>}
      {laterIncomplete&&<p className="notice">A later investigation was incomplete. It is excluded from this comparison; inspect its event in History.</p>}
      {pairLoading&&<p role="status">Loading the two saved investigations…</p>}
      {selected&&diff&&<>
        <p className="comparison-context">{latest?'Latest two completed investigations':discovery?.cursor!==null?'Selected pair from partial history':'Historical comparison: selected saved results; a different pair or a newer case result may exist.'}</p>
        <h4 className="comparison-summary">{summary}</h4>
        {diff.kind==='time'&&<p>Evidence and comparable saved findings were unchanged. Evaluation time advanced; the recorded review boundaries are shown below.</p>}
        {diff.limitations.map(item=><p className="notice" key={item}>{item}</p>)}
        <div className="comparison-values">{values(selected.before,'Earlier saved')}{values(selected.after,'Later saved')}</div>
        {!!diff.changed.length&&<p>Changed saved fields: {diff.changed.join(', ')}. Inspect the originals for exact values and source-linked details.</p>}
        {diff.sources.length>0&&<><h4>Evidence included in the saved snapshots</h4><p className="subtle">An evidence arrival is separate from the payment or message event time. These differences do not establish causality.</p>
          <ul className="comparison-sources">{diff.sources.map(source=><li key={source.source_id}><strong>{source.source_id}</strong><p>{!source.before.length?'Newly included source':!source.after.length?'Source absent from the later snapshot':'Different saved source version'}</p>
            {(['before','after'] as const).map(side=><div key={side}><p>{side==='before'?'Earlier snapshot':'Later snapshot'}</p>{source[side].map((id,index)=>{
              const entry=selected[side].timeline.find(item=>item.source_id===source.source_id&&item.evidence_version_id===id);
              const record=view.evidence.find(item=>item.id===id&&item.stable_source_id===source.source_id);
              return <div key={id}><button className="source-chip" onClick={()=>onSource(id)}>Inspect {side==='before'?'earlier':'later'} source {source.source_id} / {record?`v${record.version}`:`saved reference ${index+1}`}</button><details className="version-reference"><summary>Exact evidence version</summary><p>{id}</p></details><p className="subtle">Event {instant(entry?.event_at??null)}; arrived {instant(entry?.arrived_at??null)}</p></div>;
            })}</div>)}
          </li>)}</ul></>}
        <div className="decision-actions"><button onClick={()=>setOriginal('before')}>Open earlier investigation</button><button onClick={()=>setOriginal('after')}>Open later investigation</button></div>
        {original&&<article className="historical-record"><h4>{original==='before'?'Earlier':'Later'} saved investigation</h4><p>Recorded advice only. The current case, draft and approval state are unchanged.</p><FindingsView result={selected[original]} view={{...view,freshness:'HISTORICAL_SNAPSHOT',evaluation_at:selected[original].evaluation_at}} onSource={onSource}/></article>}
      </>}
    </div>}
  </section>;
}
