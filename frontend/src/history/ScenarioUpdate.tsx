import { useEffect, useRef, useState } from 'react';
import { ApiError, type ApiClient } from '../api/client';
import type { CaseView, CatalogueEvent, ScenarioPreview } from '../api/types';
import { instant, words } from '../components/format';
import { useDraftReview } from '../reviews/useDraftReview';

export function ScenarioUpdate({api,view,events,selectedVariantId,onRefresh}:{api:ApiClient;view:CaseView;events:CatalogueEvent[];selectedVariantId:string|null|undefined;onRefresh:()=>void}) {
  const eligible=events.filter(event=>selectedVariantId!==undefined&&event.eligible_variant_ids.includes(selectedVariantId)&&event.case_id===view.catalogue_case_id&&(view.clock_mode!=='REAL'||event.kind!=='CLOCK'));
  const [selected,setSelected]=useState(eligible[0]?.id??''),[preview,setPreview]=useState<ScenarioPreview|null>(null),[confirmed,setConfirmed]=useState(false),[loading,setLoading]=useState(false),[error,setError]=useState('');
  const generation=useRef(0);
  const commands=useDraftReview(api,view.demonstration_id,view.id,onRefresh);
  const base=`/cases/${encodeURIComponent(view.id)}/scenario-events`;
  const scope=`?demonstration_id=${encodeURIComponent(view.demonstration_id)}`;
  const locked=loading||commands.busy||!!commands.pending;
  useEffect(()=>{generation.current++;setPreview(null);setConfirmed(false);setLoading(false);return()=>{generation.current++;};},[view.demonstration_id,view.id,view.case_revision,selectedVariantId]);
  useEffect(()=>{if(!eligible.some(event=>event.id===selected)){setSelected(eligible[0]?.id??'');setPreview(null);setConfirmed(false);}},[events,view.catalogue_case_id,view.clock_mode,selectedVariantId,selected]);
  async function loadPreview(){
    const request=++generation.current;setLoading(true);setError('');setPreview(null);setConfirmed(false);
    try{const next=await api.request<ScenarioPreview>(`${base}/${encodeURIComponent(selected)}/preview${scope}`);if(request!==generation.current)return;if(next.demonstration_id!==view.demonstration_id||next.case_id!==view.id||next.event_id!==selected||next.expected_case_revision!==view.case_revision)throw new ApiError('PREVIEW_CHANGED','Preview changed. Review again.',409);setPreview(next);}
    catch(failure){if(request===generation.current)setError(failure instanceof Error?failure.message:'Preview unavailable.');}finally{if(request===generation.current)setLoading(false);}
  }
  async function confirm(){if(!preview||!confirmed)return;const response=await commands.execute('scenario',`${base}${scope}`,{expected_case_revision:preview.expected_case_revision,event_id:preview.event_id,catalogue_version:preview.catalogue_version,confirmed_preview_hash:preview.preview_hash});if(response||!commands.pending){setPreview(null);setConfirmed(false);}}
  // A rejected revision or hash requires a fresh read and another explicit confirmation.
  useEffect(()=>{if(commands.error&&!commands.pending){setPreview(null);setConfirmed(false);}},[commands.error,commands.pending]);
  return <section className="scenario-update" aria-labelledby="scenario-update-heading"><h2 id="scenario-update-heading">Fictional scenario updates</h2><p>Preview the exact saved evidence and business clock changes before applying a catalogue event.</p>
    {!eligible.length?<p>No catalogue updates are available for this case.</p>:<><label htmlFor="scenario-event">Fictional update</label><select id="scenario-event" value={selected} disabled={locked} onChange={event=>{generation.current++;setSelected(event.target.value);setPreview(null);setConfirmed(false);}}>{eligible.map(event=><option key={event.id} value={event.id}>{event.id} / {words(event.kind)} / {instant(event.evaluation_at)}</option>)}</select><div className="decision-actions"><button disabled={locked||!selected} onClick={()=>void loadPreview()}>Preview selected fictional update</button></div></>}
    {loading&&<p role="status">Loading exact preview…</p>}{preview&&<div className="confirmation-panel"><h3>Exact update preview</h3><p>{view.catalogue_case_id} / {view.invoice_id}; event {preview.event_id}; revision {preview.expected_case_revision}.</p>{preview.evidence_changes.length?<ul>{preview.evidence_changes.map(source=><li key={source.id}><strong>{source.stable_source_id} / version {source.version}</strong><p>{source.authoritative?'Authoritative record':'Unverified report'} / {words(source.availability)}</p><pre>{source.original_content}</pre><p>Evidence time {instant(source.event_at)}; arrival {instant(source.arrived_at)}.</p></li>)}</ul>:<p>No evidence additions.</p>}{preview.clock_change?<p>Business clock: {instant(preview.clock_change.from)} → {instant(preview.clock_change.to)}. This changes business time for every case in this copy.</p>:<p>No business clock change.</p>}<p className="source-name">Catalogue {preview.catalogue_version}; preview hash {preview.preview_hash}</p><label className="confirmation-check"><input type="checkbox" checked={confirmed} onChange={event=>setConfirmed(event.target.checked)}/>I reviewed this exact fictional update</label><button disabled={locked||!confirmed} onClick={()=>void confirm()}>Confirm fictional update</button></div>}
    {commands.pending&&<div className="notice"><p>A request is pending for this copy and case. Its exact payload is retained.</p><button disabled={commands.busy} onClick={()=>void commands.reconcile()}>Check saved request outcome</button><button disabled={commands.busy} onClick={()=>void commands.retryOriginal()}>Retry original request</button></div>}{(error||commands.error)&&<p role="alert" className="notice">{error||commands.error}</p>}<p role="status" aria-live="polite">{commands.message}</p>
  </section>;
}
