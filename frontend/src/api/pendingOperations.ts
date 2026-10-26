import type { Operation } from './client';
import type { ReceiptResponse } from './types';
import {rememberCaseRevision} from './caseActivity';

export type PendingCommand = {kind:'edit'|'review'|'retry'|'disposition'|'closure'|'reopening'|'scenario'|'deletion';path:string;operation:Operation};
const key=(did:string,cid:string)=>`promisekeeper.pending.${did}.${cid}`;
export type CommittedOperation={did:string;cid:string;command:PendingCommand;response:ReceiptResponse};
const pendingListeners=new Set<(storageKey:string|null)=>void>();
const committedListeners=new Set<(outcome:CommittedOperation)=>void>();
const completed=new Set<string>();
function notifyPending(storageKey:string|null) {for(const listener of pendingListeners)listener(storageKey);}
function storageChanged(event:StorageEvent) {
  if(event.storageArea===localStorage||event.storageArea===null)notifyPending(event.key);
}
export function subscribePending(did:string,cid:string,listener:()=>void) {
  const changed=(storageKey:string|null)=>{if(storageKey===null||storageKey===key(did,cid))listener();};
  if(!pendingListeners.size)window.addEventListener('storage',storageChanged);
  pendingListeners.add(changed);
  return ()=>{pendingListeners.delete(changed);if(!pendingListeners.size)window.removeEventListener('storage',storageChanged);};
}
export function subscribeCommitted(listener:(outcome:CommittedOperation)=>void) {
  committedListeners.add(listener);
  return ()=>{committedListeners.delete(listener);};
}
export function readPending(did:string,cid:string):PendingCommand|null {
  const raw=localStorage.getItem(key(did,cid));
  if(!raw)return null;
  const value=JSON.parse(raw) as PendingCommand;
  if(!value.operation || value.operation.schema_version!=='1' || typeof value.operation.operation_id!=='string' || typeof value.path!=='string')throw new Error('The saved request cannot be read. Preserve this browser record before recovery.');
  return value;
}
export function retainPending(did:string,cid:string,command:PendingCommand) {
  const previous=readPending(did,cid);
  if(previous&&JSON.stringify(previous)!==JSON.stringify(command))throw new Error('Reconcile the pending request before changing its payload.');
  localStorage.setItem(key(did,cid),JSON.stringify(command));
  completed.delete(`${key(did,cid)}:${command.operation.operation_id}`);
  notifyPending(key(did,cid));
}
export function forgetPending(did:string,cid:string,operationId:string) {
  if(readPending(did,cid)?.operation.operation_id===operationId)localStorage.removeItem(key(did,cid));
  notifyPending(key(did,cid));
}
export const draftBufferKey=(did:string,cid:string)=>`promisekeeper.unsaved-draft.${did}.${cid}`;
// Only an API receipt establishes a commit. Storage changes only synchronize pending controls.
export function completePending(did:string,cid:string,command:PendingCommand,response:ReceiptResponse) {
  const identity=`${key(did,cid)}:${command.operation.operation_id}`;
  if(completed.has(identity))return;
  completed.add(identity);
  rememberCaseRevision(did,cid,response.receipt.case_revision);
  if(command.kind==='edit') {
    const bufferKey=draftBufferKey(did,cid),raw=localStorage.getItem(bufferKey);
    if(raw) {
      try {
        const buffer=JSON.parse(raw);
        if(buffer.text===command.operation.exact_text&&buffer.recipient===command.operation.recipient&&buffer.base===command.operation.parent_version_id)localStorage.removeItem(bufferKey);
      }catch {/* Preserve an unreadable buffer; it is not evidence of matching saved wording. */}
    }
  }
  forgetPending(did,cid,command.operation.operation_id);
  for(const listener of committedListeners)listener({did,cid,command,response});
}
// Workspace-level commands (selected-copy deletion) are retained under this scope, never under a case.
export const WORKSPACE_SCOPE='workspace';
// A case's own pending request, or an uncertain workspace deletion that fences every case command in that copy.
export function readFencingPending(did:string,cid:string):PendingCommand|null {
  return readPending(did,cid)??(cid===WORKSPACE_SCOPE?null:readPending(did,WORKSPACE_SCOPE));
}
