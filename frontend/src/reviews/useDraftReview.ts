import { useEffect, useRef, useState } from 'react';
import {rememberCaseRevision} from '../api/caseActivity';
import { ApiClient, ApiError } from '../api/client';
import type { ReceiptResponse } from '../api/types';
import { completePending, forgetPending, readFencingPending, readPending, retainPending, subscribeCommitted, subscribePending, WORKSPACE_SCOPE, type PendingCommand } from '../api/pendingOperations';

function committedMessage(command:PendingCommand,response:ReceiptResponse) {
  if(response.receipt.outcome==='DELETED')return 'Selected demonstration deleted.';
  if(command.kind==='edit')return 'New unapproved version saved.';
  if(command.kind==='review')return command.operation.decision==='APPROVE'?'Approval recorded for the exact saved version. No message was sent.':'Rejection recorded. The draft remains in history.';
  if(command.kind==='retry')return 'Draft retry acknowledged. Check saved draft status.';
  return 'Decision saved.';
}
export function useDraftReview(api:ApiClient,did:string,cid:string,onRefresh:()=>void) {
  // A case scope is also fenced by an uncertain workspace deletion; its notice reconciles that record.
  const fenced=cid!==WORKSPACE_SCOPE;
  const targetOf=()=>readPending(did,cid)||!fenced||!readPending(did,WORKSPACE_SCOPE)?cid:WORKSPACE_SCOPE;
  const [pending,setPending]=useState<PendingCommand|null>(()=>readFencingPending(did,cid));
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  const [committed,setCommitted]=useState<PendingCommand|null>(null);
  const mounted=useRef(false);
  const scope=useRef('');scope.current=`${did}:${cid}`;
  const work=useRef(0),refresh=useRef(onRefresh);refresh.current=onRefresh;
  const current=()=>mounted.current&&scope.current===`${did}:${cid}`;
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  useEffect(()=>{
    function synchronize() {
      const saved=readFencingPending(did,cid);setPending(saved);
      if(!saved){work.current++;setBusy(false);setMessage('');}
    }
    synchronize();
    const unwatchPending=subscribePending(did,cid,synchronize);
    const unwatchWorkspace=fenced?subscribePending(did,WORKSPACE_SCOPE,synchronize):()=>{};
    const unwatchCommitted=subscribeCommitted(outcome=>{
      if(outcome.did!==did||(outcome.cid!==cid&&!(fenced&&outcome.cid===WORKSPACE_SCOPE)))return;
      setCommitted(outcome.command);setMessage(committedMessage(outcome.command,outcome.response));setError('');refresh.current();
    });
    return ()=>{unwatchPending();unwatchWorkspace();unwatchCommitted();work.current++;};
  },[did,cid,fenced]);
  function complete(target:string,command:PendingCommand,response:ReceiptResponse) {
    completePending(did,target,command,response);
    return response;
  }
  async function recover(target:string,command:PendingCommand,submitOriginal:boolean):Promise<ReceiptResponse|null> {
    try{return complete(target,command,await api.operation(did,command.operation.operation_id));}
    catch(failure){
      if(!(failure instanceof ApiError&&failure.code==='NOT_RECORDED'))throw failure;
      if(readPending(did,target)?.operation.operation_id!==command.operation.operation_id)return null;
      if(!submitOriginal){if(current())setMessage('Request not recorded. You may retry its exact original payload.');return null;}
    }
    return complete(target,command,await api.request<ReceiptResponse>(command.path,command.operation));
  }
  async function run(target:string,command:PendingCommand,recoverFirst:boolean) {
    const request=++work.current;
    setBusy(true);setError('');
    try {
      return recoverFirst?await recover(target,command,true):complete(target,command,await api.request<ReceiptResponse>(command.path,command.operation));
    }catch(failure){
      if(readPending(did,target)?.operation.operation_id!==command.operation.operation_id)return null;
      if(failure instanceof ApiError&&failure.code==='REVISION_CONFLICT'&&typeof command.operation.expected_case_revision==='number') {
        rememberCaseRevision(did,target,command.operation.expected_case_revision+1);
      }
      if(failure instanceof ApiError&&[400,404,409,422].includes(failure.status)&&failure.code!=='OPERATION_PAYLOAD_MISMATCH') {
        forgetPending(did,target,command.operation.operation_id);
        if(current())refresh.current();
      }
      if(current()){setMessage('');setError(failure instanceof Error?failure.message:'The outcome is unknown. Check the saved request.');}
      return null;
    }finally{if(current()&&request===work.current)setBusy(false);}
  }
  useEffect(()=>{
    const saved=readPending(did,cid);if(!saved)return;
    let cancelled=false;const request=++work.current;setBusy(true);
    void recover(cid,saved,false).catch(failure=>{if(!cancelled&&readPending(did,cid)?.operation.operation_id===saved.operation.operation_id)setError(failure instanceof Error?failure.message:'The outcome is unknown.');}).finally(()=>{if(!cancelled&&request===work.current)setBusy(false);});
    return()=>{cancelled=true;};
  },[api,did,cid]);
  async function execute(kind:PendingCommand['kind'],path:string,payload:Record<string,unknown>) {
    if(readFencingPending(did,cid)){setError('Reconcile the pending request before starting another.');return null;}
    const command:PendingCommand={kind,path,operation:{schema_version:'1',operation_id:crypto.randomUUID(),...payload}};
    retainPending(did,cid,command);
    return run(cid,command,false);
  }
  return {pending,busy,message,error,committed,execute,
    retryOriginal:()=>{const target=targetOf();const saved=readPending(did,target);if(saved)return run(target,saved,true);forgetPending(did,cid,'');return Promise.resolve(null);},
    reconcile:async()=>{
      const target=targetOf();
      const saved=readPending(did,target);if(!saved){forgetPending(did,cid,'');return;}
      const request=++work.current;setBusy(true);
      try{await recover(target,saved,false);}catch(failure){if(current()&&readPending(did,target)?.operation.operation_id===saved.operation.operation_id)setError(failure instanceof Error?failure.message:'The outcome is unknown.');}
      finally{if(current()&&request===work.current)setBusy(false);}
    }
  };
}
// True while an uncertain selected-copy deletion is retained; case commands outside this hook check it too.
export function useWorkspaceFence(did:string):boolean {
  const read=()=>{try{return !!readPending(did,WORKSPACE_SCOPE);}catch{return true;}};
  const [fence,setFence]=useState(read);
  useEffect(()=>{const sync=()=>setFence(read());sync();return subscribePending(did,WORKSPACE_SCOPE,sync);},[did]);
  return fence;
}
