import { useEffect, useRef, useState } from 'react';
import { ApiClient, ApiError, clearOperation, pendingOperation, stableOperation } from '../api/client';
import type { Attempt, CaseView, ReceiptResponse } from '../api/types';
import { instant, words } from '../components/format';
import {rememberCaseRevision} from '../api/caseActivity';
import { AgentTrace } from '../agents/AgentTrace';
export function InvestigationControls({api,view,onRefresh}:{api:ApiClient;view:CaseView;onRefresh:()=>void}) {
  const [busy,setBusy]=useState(false);
  const [message,setMessage]=useState('');
  const [attempt,setAttempt]=useState<Attempt|null>(null);
  const [activeId,setActiveId]=useState<string|null>(view.running_attempt);
  const [limited,setLimited]=useState(false);
  const mounted=useRef(true);
  const started=useRef(0);
  const scope={did:view.demonstration_id,cid:view.id};
  const eligibility=view.allowed_commands.start_investigation;
  const [hasPending,setHasPending]=useState(()=>!!pendingOperation(scope.did,scope.cid,'investigation'));
  useEffect(()=>{mounted.current=true;return ()=>{mounted.current=false;};},[]);
  useEffect(()=>{if(view.running_attempt)setActiveId(view.running_attempt);},[view.running_attempt]);
  function acknowledge(receipt:ReceiptResponse) {
    if(!mounted.current)return;
    if(!receipt.investigation_id) throw new Error('The operation receipt has no investigation. Refresh the case and inspect history.');
    rememberCaseRevision(scope.did,scope.cid,receipt.receipt.case_revision);
    clearOperation(scope.did,scope.cid,'investigation');setHasPending(false);
    setActiveId(receipt.investigation_id);setMessage('Investigation start saved. Waiting for a terminal result.');onRefresh();
  }
  async function reconcileOnly() {
    const pending=pendingOperation(scope.did,scope.cid,'investigation');
    if(!pending) return;
    setBusy(true);setMessage('Checking the saved operation outcome…');
    try {acknowledge(await api.operation(scope.did,pending.operation_id));}
    catch(error) {if(!mounted.current)return;if(error instanceof ApiError&&error.code==='NOT_RECORDED')setMessage('Start not recorded. Retry the original operation explicitly.');else setMessage(error instanceof Error?error.message:'Operation outcome is still unknown.');}
    finally {if(mounted.current)setBusy(false);}
  }
  useEffect(()=>{if(hasPending&&!view.running_attempt)void reconcileOnly();},[]);
  async function start() {
    setBusy(true);setLimited(false);setMessage('Saving investigation start…');started.current=Date.now();
    try {
      const pending=pendingOperation(scope.did,scope.cid,'investigation');
      if(pending) {try {acknowledge(await api.operation(scope.did,pending.operation_id));return;}catch(error){if(!(error instanceof ApiError&&error.code==='NOT_RECORDED'))throw error;}}
      const operation=pending ?? stableOperation(scope.did,scope.cid,'investigation',{expected_case_revision:view.case_revision,retry_of:attempt?.status==='INCOMPLETE'?attempt.investigation_id:null});
      setHasPending(true);
      acknowledge(await api.start(scope.did,scope.cid,operation));
    } catch(error) {
      if(mounted.current) {
        if(error instanceof ApiError&&error.code==='REVISION_CONFLICT')rememberCaseRevision(scope.did,scope.cid,view.case_revision+1);
        if(error instanceof ApiError && [400,404,409,422].includes(error.status) && error.code!=='OPERATION_PAYLOAD_MISMATCH') {
          clearOperation(scope.did,scope.cid,'investigation');setHasPending(false);onRefresh();
        }
        setMessage(error instanceof Error?error.message:'Start failed. Check the operation before retrying.');
      }
    }
    finally {if(mounted.current)setBusy(false);}
  }
  useEffect(()=>{
    if(!activeId)return;
    let cancelled=false;let watchdogExpired=false;let timer:ReturnType<typeof setTimeout>;
    started.current=started.current||Date.now();
    const watchdog=setTimeout(()=>{if(!cancelled){watchdogExpired=true;setLimited(true);setBusy(false);setMessage('Connection limitation: no terminal result confirmed within 60 seconds. The server outcome is unknown. Check saved status before starting again.');}},Math.max(0,60_000-(Date.now()-started.current)));
    async function poll() {
      try {const next=await api.attempt(scope.did,activeId!);if(cancelled)return;setAttempt(next);
        if(next.status!=='RUNNING') {clearTimeout(watchdog);setActiveId(null);setLimited(false);setMessage(next.status==='INCOMPLETE'?`Investigation incomplete: ${next.failure_code?words(next.failure_code):'review the saved limitation'}. ${next.limitations.join(' ')}`:`${next.status} result saved.`);onRefresh();return;}
        if(Date.now()-started.current>=60_000)return;
      }catch(error){if(cancelled)return;if(!watchdogExpired)setMessage(error instanceof Error?error.message:'Connection unavailable. Saved evidence remains inspectable.');if(Date.now()-started.current>=60_000)return;}
      timer=setTimeout(poll,1000);
    }
    void poll();return ()=>{cancelled=true;clearTimeout(timer);clearTimeout(watchdog);};
  },[activeId,api,scope.did,scope.cid]);
  const running=!!activeId;
  return <section className="investigation-controls" aria-label="Investigation controls"><div><button className="primary" disabled={busy||running||!eligibility?.allowed} onClick={()=>void start()}>{running?'Investigation running':hasPending?'Retry original start':attempt?.status==='INCOMPLETE'?'Retry investigation':'Investigate case'}</button>{hasPending&&!running&&<button disabled={busy} onClick={()=>void reconcileOnly()}>Check operation outcome</button>}{limited&&<button onClick={()=>{started.current=Date.now();setActiveId(null);setTimeout(()=>setActiveId(view.running_attempt??attempt?.investigation_id??activeId),0);setLimited(false);}}>Check saved investigation status</button>}</div>{!eligibility?.allowed&&!running&&<p className="subtle">Start unavailable: {eligibility?.blocking_reasons.map(words).join(', ') || 'server eligibility unavailable'}.</p>}<p className={limited?'notice':'status-message'} role="status" aria-live="polite">{message||'Starts only when you choose to investigate. Sources stay available during an investigation.'}</p>{attempt&&<p className="subtle">{attempt.status} · evaluated {instant(attempt.evaluation_at)} · deadline {instant(attempt.deadline_at)}</p>}{running&&activeId&&<AgentTrace key={`live:${activeId}`} api={api} did={scope.did} investigationId={activeId} title="Your AI team is working"/>}</section>;
}
