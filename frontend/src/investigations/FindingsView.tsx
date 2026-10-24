import type { CaseView, EvidenceObservation, FinancialIssue, Result, SourceVersionRef } from '../api/types';
import { FinancialSummary } from '../cases/CaseEvidence';
import { instant, money, words } from '../components/format';

export function FindingsView({result,view,onSource}:{result:Result;view:CaseView;onSource:(id:string)=>void}) {
  const reviewReached=!!result.review_at && Date.parse(view.evaluation_at)>=Date.parse(result.review_at);
  function resolveSource(value:string|SourceVersionRef) {
    if(typeof value!=='string')return view.evidence.find(source=>source.id===value.evidence_version_id&&source.stable_source_id===value.source_id);
    const snapshotVersion=result.timeline.find(entry=>entry.source_id===value)?.evidence_version_id;
    return view.evidence.find(source=>source.id===(snapshotVersion ?? value));
  }
  function sourceButton(value:string|SourceVersionRef,index:number) {
    const record=resolveSource(value);
    const label=typeof value==='string'?value:`${value.source_id} (version ${value.evidence_version_id})`;
    return record
      ? <button key={index} className="source-chip" onClick={()=>onSource(record.id)}>{record.stable_source_id} / v{record.version}</button>
      : <span key={index} className="subtle">Source {label} unavailable in this view</span>;
  }
  function issueList(issues:FinancialIssue[]) {
    return <ul>{issues.map((issue,index)=><li key={index}>
      <p>{issue.detail}</p><span className="subtle">{words(issue.code)}</span>
      <div className="source-links">{(issue.source_versions ?? issue.sources).map(sourceButton)}</div>
    </li>)}</ul>;
  }
  function observationText(observation:EvidenceObservation) {
    if(observation.subject==='LEDGER')return observation.field==='availability'
      ? `Saved ledger availability: ${words(observation.value)}.`
      : `Saved ledger is ${observation.value?'complete':'incomplete'}.`;
    return observation.field==='content_present'
      ? `Source ${observation.source.source_id} has no readable original content.`
      : `Source ${observation.source.source_id} availability: ${words(observation.value)}.`;
  }
  return <section className="findings" aria-labelledby="findings-heading">
    <div className="findings-heading">
      <div><p>Saved recommendation · {result.status}</p><h2 id="findings-heading">{result.action}</h2></div>
      <p>Evaluated {instant(result.evaluation_at)}</p>
    </div>
    {view.freshness!=='CURRENT'&&<p className="notice">Historical result: {words(view.freshness)}. Inspect current evidence before acting.</p>}
    {!result.findings_version&&<p className="notice">Legacy findings: saved before the current findings profile. Reinvestigate to include source-linked issues and evidence observations.</p>}
    {result.status==='LIMITED'&&<p className="notice">Limited investigation. Review the missing or unresolved evidence below.</p>}
    <p className="explanation">{result.explanation.text}</p>
    <div className="next-step"><h3>Next step</h3><p>{result.next_step}</p></div>
    {result.action==='VERIFY_PAYMENT'&&<p className="notice">Verify the evidence before any payment demand.</p>}
    {result.action==='CLOSE'&&<p className="notice">This recommendation does not close the case. Review the settlement in History and explicitly confirm case closure.</p>}
    {result.action==='WAIT'&&<div className="review-boundary">
      <h3>Review at {instant(result.review_at)}</h3>
      <p>{reviewReached?'Review required: the review boundary has been reached. Reinvestigate; another future condition may still require waiting.':'Wait until this earliest review boundary, then reinvestigate. No contact is initiated.'}</p>
      <p>Invoice overdue boundary {instant(result.financial_facts.due_at)}</p>
    </div>}
    <FinancialSummary facts={{...result.financial_facts,label:words(result.financial_label)}} showIssues={false}/>
    <div className="source-links">{result.explanation.sources.map(sourceButton)}</div>
    {result.financial_facts.issues.length>0&&<><h3>Financial issues</h3>{issueList(result.financial_facts.issues)}</>}
    {!!result.commitment_issues?.length&&<><h3>Commitment issues</h3>{issueList(result.commitment_issues)}</>}
    {!!result.evidence_observations?.length&&<><h3>Evidence observations</h3><p className="subtle">Captured in this investigation's saved snapshot.</p><ul>{result.evidence_observations.map((observation,index)=><li key={index}>
      <p>{observationText(observation)}</p>
      {observation.subject==='SOURCE'&&observation.field==='availability'&&!!resolveSource(observation.source)?.original_content&&<div className="source-links">{sourceButton(observation.source,index)}</div>}
    </li>)}</ul></>}
    {result.limitations.length>0&&<><h3>Limitations</h3><ul>{result.limitations.map((item,i)=><li key={i}>{words(item)}</li>)}</ul></>}
    {result.commitments.length>0&&<><h3>Commitments and fulfillment</h3>{result.commitments.map((commitment,i)=><article className="commitment" key={commitment.commitment_stable_id ?? i}>
      <h4>{money(commitment.amount)} promise</h4>
      <dl>
        <div><dt>Promise expiry</dt><dd>{instant(commitment.expires_at)}</dd></div>
        <div><dt>Fulfillment</dt><dd>{commitment.fulfillment_unresolved?'Unresolved':commitment.fulfilled?'Fulfilled':'Unfulfilled'}{commitment.superseded?' · explicitly superseded':''}</dd></div>
        <div><dt>Explicitly credited</dt><dd>{money(commitment.credited)}</dd></div>
        <div><dt>Commitment identity</dt><dd>{commitment.commitment_stable_id ?? 'Unresolved identity'}</dd></div>
      </dl>
      {sourceButton(commitment.evidence_version_id,i)}
    </article>)}</>}
    {result.claims.length>0&&<><h3>Payment claims</h3>{result.claims.map((claim,i)=><div className="claim" key={i}>
      <p>{claim.resolved?'Supported claim':'Unresolved claim'}{claim.customer_clarification?' · customer clarification needed':''}</p>
      {sourceButton(claim.evidence_version_id,i)}
    </div>)}</>}
    {result.contradictions.length>0&&<><h3>Contradictions</h3><ul>{result.contradictions.map((item,i)=><li key={i}>
      {words(item.kind)}<div className="source-links">{item.sources.map(sourceButton)}</div>
    </li>)}</ul></>}
    {result.unresolved_questions.length>0&&<><h3>Unresolved facts</h3><ul>{result.unresolved_questions.map((item,i)=><li key={i}>
      {words(item.field)}<div className="source-links">{item.sources.map(sourceButton)}</div>
    </li>)}</ul></>}
    <details className="result-provenance"><summary>Saved investigation provenance</summary>
      <p>Investigation {result.investigation_id}</p><p>Snapshot {result.snapshot_id}</p><p>Result hash {result.result_hash}</p>
      <p>Findings profile: {result.findings_version ?? 'legacy'}</p>
    </details>
  </section>;
}
