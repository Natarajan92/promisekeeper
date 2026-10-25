import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react';
import { AgentTraceDisclosure } from '../agents/AgentTrace';
import { FeedbackButtons } from '../agents/FeedbackButtons';
import type { ApiClient } from '../api/client';
import type { CaseView } from '../api/types';
import { draftBufferKey, readPending } from '../api/pendingOperations';
import {caseActivitySnapshot,caseIsUpdating,subscribeCaseActivity} from '../api/caseActivity';
import { instant, words } from '../components/format';
import { useDraftReview } from './useDraftReview';

type Buffer={text:string;recipient:string;base:string|null};
export function DraftReview({api,view,onRefresh}:{api:ApiClient;view:CaseView;onRefresh:()=>void}) {
  const draft=view.draft;
  const key=draftBufferKey(view.demonstration_id,view.id);
  const [buffer,setBuffer]=useState<Buffer>(()=>{const raw=localStorage.getItem(key);return raw?JSON.parse(raw):{text:draft?.exact_text??'',recipient:draft?.recipient??'',base:draft?.id??null};});
  const [dirty,setDirty]=useState(()=>localStorage.getItem(key)!==null);
  const commands=useDraftReview(api,view.demonstration_id,view.id,onRefresh);
  const [generationLimitation,setGenerationLimitation]=useState('');
  useEffect(()=>{
    if(view.draft_generation_attempt?.status!=='RUNNING'){setGenerationLimitation('');return;}
    const began=Date.now();
    const timer=setInterval(()=>{if(Date.now()-began<60_000)onRefresh();else{clearInterval(timer);setGenerationLimitation('Draft status could not be confirmed within 60 seconds. The recommendation remains saved. Refresh the case to check its status.');}},1000);
    return()=>clearInterval(timer);
  },[view.draft_generation_attempt?.id,view.draft_generation_attempt?.status,onRefresh]);
  useEffect(()=>{
    const committed=commands.committed;
    if(committed?.kind==='edit'&&committed.operation.exact_text===buffer.text&&committed.operation.recipient===buffer.recipient&&committed.operation.parent_version_id===buffer.base){localStorage.removeItem(key);setDirty(false);}
  },[commands.committed,buffer.text,buffer.recipient,buffer.base,key]);
  useEffect(()=>{if(!dirty)setBuffer({text:draft?.exact_text??'',recipient:draft?.recipient??'',base:draft?.id??null});},[draft?.id,draft?.exact_text,draft?.recipient,dirty]);
  const path=(suffix:string)=>`/cases/${encodeURIComponent(view.id)}/${suffix}?demonstration_id=${encodeURIComponent(view.demonstration_id)}`;
  function change(next:Buffer){setBuffer(next);setDirty(true);localStorage.setItem(key,JSON.stringify(next));}
  async function save() {
    if(!draft)return;
    await commands.execute('edit',path('draft-versions'),{expected_case_revision:view.case_revision,investigation_id:draft.investigation_id,parent_version_id:buffer.base,exact_text:buffer.text,recipient:buffer.recipient});
  }
  async function review(decision:'APPROVE'|'REJECT') {
    if(!draft)return;
    await commands.execute('review',path('draft-reviews'),{expected_case_revision:view.case_revision,draft_version_id:draft.id,payload_hash:draft.payload_hash,expected_review_epoch:view.review_epoch,decision});
  }
  const locked=commands.busy||!!commands.pending;
  useSyncExternalStore(
    useCallback(listener=>subscribeCaseActivity(view.demonstration_id,view.id,listener),[view.demonstration_id,view.id]),
    useCallback(()=>caseActivitySnapshot(view.demonstration_id,view.id),[view.demonstration_id,view.id]),
  );
  const [copyResult,setCopyResult]=useState<{key:string;state:'copied'|'manual'}|null>(null);
  const [copying,setCopying]=useState(false);
  const copyKey=`${view.demonstration_id}:${view.id}:${draft?.id}:${draft?.payload_hash}:${view.review_epoch}:${view.review_state}:${view.case_revision}`;
  const activeCopy=useRef(copyKey);activeCopy.current=copyKey;
  const copyEligible=!!draft&&view.review_state==='APPROVED'&&draft.validation_status==='VALID'&&
    draft.id===view.current_draft_version_id&&
    view.freshness==='CURRENT'&&!view.running_attempt&&!!view.allowed_commands.approve_draft?.allowed&&
    draft.investigation_id===view.current_result?.investigation_id&&!dirty&&!locked&&
    !caseIsUpdating(view.demonstration_id,view.id,view.case_revision);
  const canCopy=useRef(copyEligible);canCopy.current=copyEligible;
  useEffect(()=>()=>{activeCopy.current='';},[]);
  async function copyApproved() {
    if(!copyEligible||!draft||copying||caseIsUpdating(view.demonstration_id,view.id,view.case_revision)||readPending(view.demonstration_id,view.id))return;
    const requestedKey=copyKey;const exact=draft.exact_text;setCopying(true);setCopyResult(null);
    try {
      if(!navigator.clipboard?.writeText)throw new Error('Clipboard unavailable');
      await navigator.clipboard.writeText(exact);
      if(activeCopy.current===requestedKey&&canCopy.current&&!caseIsUpdating(view.demonstration_id,view.id,view.case_revision)&&!readPending(view.demonstration_id,view.id))setCopyResult({key:requestedKey,state:'copied'});
    }catch {
      if(activeCopy.current===requestedKey&&canCopy.current&&!caseIsUpdating(view.demonstration_id,view.id,view.case_revision)&&!readPending(view.demonstration_id,view.id))setCopyResult({key:requestedKey,state:'manual'});
    }finally {if(activeCopy.current)setCopying(false);}
  }
  const changedHead=dirty&&buffer.base!==(draft?.id??null);
  const eligibility=view.allowed_commands;
  const failed=view.draft_generation_attempt?.status==='FAILED'?view.draft_generation_attempt:null;
  return <section className="draft-review" aria-labelledby="draft-review-heading"><h2 id="draft-review-heading">Communication review</h2><p>Approval records your review of the exact saved message. No customer message is sent.</p>{draft&&<AgentTraceDisclosure key={`draft-trace:${draft.investigation_id}`} api={api} did={view.demonstration_id} investigationId={draft.investigation_id}/>}
    {!draft?<p className="notice">{view.no_draft_reason?words(view.no_draft_reason):view.draft_generation_attempt?.status==='RUNNING'?'Preparing a draft from the saved recommendation.':'Investigate this case to see whether a customer draft is needed.'}</p>:<>
      <p><strong>Invoice {draft.invoice_id}</strong> · Version {draft.version} · {words(view.review_state??'UNAPPROVED')}</p>
      <p className="subtle">Saved {instant(draft.created_at)}. Review decisions apply to the saved version shown below.</p>
      {changedHead&&<div className="notice"><p role="alert">A newer saved version exists. Your unsaved text is retained against its original version. Review the saved version before making a new edit.</p><button disabled={locked} onClick={()=>{localStorage.removeItem(key);setBuffer({text:draft.exact_text,recipient:draft.recipient,base:draft.id});setDirty(false);}}>Discard unsaved wording and use saved version</button></div>}
      <label htmlFor="draft-recipient">Draft recipient</label><input id="draft-recipient" value={buffer.recipient} maxLength={500} onChange={event=>change({...buffer,recipient:event.target.value})}/>
      <label htmlFor="draft-text">Draft text</label><textarea id="draft-text" rows={12} maxLength={8000} value={buffer.text} onChange={event=>change({...buffer,text:event.target.value})}/>
      {dirty&&<p className="notice">Unsaved wording. Save it as a new unapproved version before approval.</p>}
      {!!draft.validation_reasons.length&&<div className="notice"><p>Correct these clauses before approval:</p><ul>{draft.validation_reasons.map(reason=><li key={reason}>{words(reason)}</li>)}</ul><p>Use the supported financial wording from the original template. Neutral greeting and closing changes are supported.</p></div>}
      {eligibility.approve_draft&&!eligibility.approve_draft.allowed&&<p className="notice">Approval unavailable: {eligibility.approve_draft.blocking_reasons.map(words).join(', ')}.</p>}
      <div className="decision-actions"><button disabled={locked||!dirty||changedHead||!eligibility.edit_draft?.allowed||!buffer.text.length} onClick={()=>void save()}>Save unapproved version</button>
      <button disabled={locked||dirty||!eligibility.approve_draft?.allowed||draft.validation_status!=='VALID'} onClick={()=>void review('APPROVE')}>Approve exact saved version</button>
      <button disabled={locked||!eligibility.reject_draft?.allowed} onClick={()=>void review('REJECT')}>Reject exact saved version</button></div>
      {draft&&<FeedbackButtons key={`draft-feedback:${draft.id}`} api={api} did={view.demonstration_id} cid={view.id} investigationId={draft.investigation_id} target="DRAFT"/>}
      {view.review_state==='APPROVED'&&<section className="approved-handoff" aria-label="Approved message handoff">
        <h3>{copyEligible?'Approved and ready for you to use':'Check the saved approval before using this message'}</h3>
        <p>Nothing has been sent. {copyEligible?'Copy the approved wording to your usual communication tool and review the recipient there.':'Resolve pending changes and check the latest saved version before using this message.'}</p>
        <button className="primary" disabled={!copyEligible||copying} onClick={()=>void copyApproved()}>{copying?'Copying approved message…':'Copy approved message'}</button>
        {!copyEligible&&<p className="subtle">Copying is unavailable while wording is unsaved, a request is pending, or the saved approval needs review.</p>}
        {copyEligible&&copyResult?.key===copyKey&&copyResult.state==='copied'&&<p role="status">Version {draft.version} copied. Nothing has been sent.</p>}
        {copyEligible&&copyResult?.key===copyKey&&copyResult.state==='manual'&&<div><p role="status">Clipboard access is unavailable. Select and copy the approved text below.</p><label htmlFor="approved-manual-copy">Approved message for manual copying</label><textarea id="approved-manual-copy" readOnly value={draft.exact_text} onFocus={event=>event.currentTarget.select()}/></div>}
      </section>}
      <details><summary>Exact saved version and recipient</summary><p>{draft.recipient} / {draft.invoice_id} / version {draft.version}</p><pre>{draft.exact_text}</pre><p className="subtle">Payload hash {draft.payload_hash}</p></details>
    </>}
    {failed&&<div className="notice"><p>The recommendation is saved. Draft preparation failed: {words(failed.failure_code??'DRAFT_FAILED')}.</p><button disabled={locked||!view.allowed_commands.retry_draft?.allowed} onClick={()=>void commands.execute('retry',path('draft-retries'),{expected_case_revision:view.case_revision,investigation_id:failed.investigation_id,failed_draft_attempt_id:failed.id,expected_draft_head:view.current_draft_version_id})}>Retry failed draft step</button></div>}
    {commands.pending&&<div className="notice"><p>A request is pending for this copy and case. Its exact payload is retained.</p><button disabled={commands.busy} onClick={()=>void commands.reconcile()}>Check saved request outcome</button><button disabled={commands.busy} onClick={()=>void commands.retryOriginal()}>Retry original request</button></div>}
    {generationLimitation&&<p className="notice" role="status">{generationLimitation}</p>}{commands.error&&<p className="notice" role="alert">{commands.error}</p>}<p role="status" aria-live="polite">{commands.message}</p>
    <h3>Review history</h3>{!view.draft_reviews?.length?<p>No recorded draft decision.</p>:<ol>{view.draft_reviews.map(item=><li key={item.id}><strong>{words(item.decision)}</strong> at {instant(item.decided_at)}<p>{item.recipient} / {item.invoice_id} / review epoch {item.review_epoch}</p><details><summary>Reviewed exact text</summary><pre>{item.exact_text}</pre></details></li>)}</ol>}
  </section>;
}
