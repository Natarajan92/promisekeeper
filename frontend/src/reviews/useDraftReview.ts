import { useEffect, useRef, useState } from 'react';
import { ApiClient, ApiError } from '../api/client';
import type { ReceiptResponse } from '../api/types';
import { completePending, forgetPending, readPending, retainPending, subscribeCommitted, subscribePending, type PendingCommand } from '../api/pendingOperations';

function committedMessage(command:PendingCommand,response:ReceiptResponse) {
  if(response.receipt.outcome==='DELETED')return 'Selected demonstration deleted.';
  if(command.kind==='edit')return 'New unapproved version saved.';
  if(command.kind==='review')return command.operation.decision==='APPROVE'?'Approval recorded for the exact saved version. No message was sent.':'Rejection recorded. The draft remains in history.';
  if(command.kind==='retry')return 'Draft retry acknowledged. Check saved draft status.';
  return 'Decision saved.';
}
export function useDraftReview(api:ApiClient,did:string,cid:string,onRefresh:()=>void) {
  const [pending,setPending]=useState<PendingCommand|null>(()=>readPending(did,cid));
  const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
  const [committed,setCommitted]=useState<PendingCommand|null>(null);
  const mounted=useRef(false);
  const scope=useRef('');scope.current=`${did}:${cid}`;
  const work=useRef(0),refresh=useRef(onRefresh);refresh.current=onRefresh;
  const current=()=>mounted.current&&scope.current===`${did}:${cid}`;
  useEffect(()=>{mounted.current=true;return()=>{mounted.current=false;};},[]);
  useEffect(()=>{
    function synchronize() {
      const saved=readPending(did,cid);setPending(saved);
      if(!saved){work.current++;setBusy(false);setMessage('');}
    }
    synchronize();
    const unwatchPending=subscribePending(did,cid,synchronize);
    const unwatchCommitted=subscribeCommitted(outcome=>{
      if(outcome.did!==did||outcome.cid!==cid)return;
      setCommitted(outcome.command);setMessage(committedMessage(outcome.command,outcome.response));setError('');refresh.current();
    });
    return ()=>{unwatchPending();unwatchCommitted();work.current++;};
  },[did,cid]);
  function complete(command:PendingCommand,response:ReceiptResponse) {
    completePending(did,cid,command,response);
    return response;
  }
  async function recover(command:PendingCommand,submitOriginal:boolean):Promise<ReceiptResponse|null> {
    try{return complete(command,await api.operation(did,command.operation.operation_id));}
    catch(failure){
      if(!(failure instanceof ApiError&&failure.code==='NOT_RECORDED'))throw failure;
      if(readPending(did,cid)?.operation.operation_id!==command.operation.operation_id)return null;
      if(!submitOriginal){if(current())setMessage('Request not recorded. You may retry its exact original payload.');return null;}
    }
    return complete(command,await api.request<ReceiptResponse>(command.path,command.operation));
  }
  async function run(command:PendingCommand,recoverFirst:boolean) {
    const request=++work.current;
    setBusy(true);setError('');
    try {
      return recoverFirst?await recover(command,true):complete(command,await api.request<ReceiptResponse>(command.path,command.operation));
    }catch(failure){
      if(readPending(did,cid)?.operation.operation_id!==command.operation.operation_id)return null;
      if(failure instanceof ApiError&&[400,404,409,422].includes(failure.status)&&failure.code!=='OPERATION_PAYLOAD_MISMATCH') {
        forgetPending(did,cid,command.operation.operation_id);
        if(current())refresh.current();
      }
      if(current()){setMessage('');setError(failure instanceof Error?failure.message:'The outcome is unknown. Check the saved request.');}
      return null;
    }finally{if(current()&&request===work.current)setBusy(false);}
  }
  useEffect(()=>{
    const saved=readPending(did,cid);if(!saved)return;
    let cancelled=false;const request=++work.current;setBusy(true);
    void recover(saved,false).catch(failure=>{if(!cancelled&&readPending(did,cid)?.operation.operation_id===saved.operation.operation_id)setError(failure instanceof Error?failure.message:'The outcome is unknown.');}).finally(()=>{if(!cancelled&&request===work.current)setBusy(false);});
    return()=>{cancelled=true;};
  },[api,did,cid]);
  async function execute(kind:PendingCommand['kind'],path:string,payload:Record<string,unknown>) {
    if(readPending(did,cid)){setError('Reconcile the pending request before starting another.');return null;}
    const command:PendingCommand={kind,path,operation:{schema_version:'1',operation_id:crypto.randomUUID(),...payload}};
    retainPending(did,cid,command);
    return run(command,false);
  }
  return {pending,busy,message,error,committed,execute,
    retryOriginal:()=>{const saved=readPending(did,cid);if(saved)return run(saved,true);forgetPending(did,cid,'');return Promise.resolve(null);},
    reconcile:async()=>{
      const saved=readPending(did,cid);if(!saved){forgetPending(did,cid,'');return;}
      const request=++work.current;setBusy(true);
      try{await recover(saved,false);}catch(failure){if(current()&&readPending(did,cid)?.operation.operation_id===saved.operation.operation_id)setError(failure instanceof Error?failure.message:'The outcome is unknown.');}
      finally{if(current()&&request===work.current)setBusy(false);}
    }
  };
}
