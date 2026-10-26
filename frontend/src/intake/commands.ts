import {ApiClient,ApiError,clearOperation,pendingOperation,stableOperation,type Operation} from '../api/client';
import {rememberCaseRevision,notifyWorkspaceActivity} from '../api/caseActivity';
import type {IntakeReceipt} from './types';

export const intakeFenceKey=(did:string)=>`promisekeeper.intake.pending.${did}`;
export function pendingIntake(did:string,cid:string,kind:string){return pendingOperation(did,cid,`intake-${kind}`);}
export function clearIntakeState(did:string){
  const prefix=`promisekeeper.operation.${did}.`;
  for(const key of Object.keys(localStorage))if(key.startsWith(prefix)&&key.includes('.intake-'))localStorage.removeItem(key);
  localStorage.removeItem(intakeFenceKey(did));notifyWorkspaceActivity(did);
}
export async function executeIntake(api:ApiClient,did:string,cid:string,kind:string,path:string,payload?:Record<string,unknown>):Promise<IntakeReceipt>{
  const saved=pendingIntake(did,cid,kind);
  const fence=localStorage.getItem(intakeFenceKey(did));
  if(fence&&fence!==saved?.operation_id)throw new Error('Another upload or allocation has an unknown outcome. Retry that original request first.');
  const operation:Operation=payload?stableOperation(did,cid,`intake-${kind}`,payload):saved!;
  if(!operation)throw new Error('No saved original request is available.');
  localStorage.setItem(intakeFenceKey(did),operation.operation_id);notifyWorkspaceActivity(did);
  const finish=()=>{clearOperation(did,cid,`intake-${kind}`);if(localStorage.getItem(intakeFenceKey(did))===operation.operation_id)localStorage.removeItem(intakeFenceKey(did));notifyWorkspaceActivity(did);};
  try{
    const response=await api.request<IntakeReceipt>(path,operation);
    for(const [caseId,revision] of Object.entries(response.case_revisions??{}))rememberCaseRevision(response.demonstration_id??did,caseId,revision);
    finish();return response;
  }catch(error){
    if(error instanceof ApiError&&error.status>=400&&error.status<500&&error.code!=='OPERATION_PAYLOAD_MISMATCH')finish();
    throw error;
  }
}
export function intakeError(error:unknown){
  if(error instanceof ApiError){
    const messages:Record<string,string>={PREVIEW_CHANGED:'The workspace changed. Refresh and preview the file again.',REVISION_CONFLICT:'This invoice changed. Refresh before confirming again.',ALLOCATION_EXCEEDS_REMAINDER:'The allocation exceeds the receipt or invoice remainder.',PAYMENT_NOT_SETTLED:'A pending or reversed receipt cannot be allocated.',IMPORT_VALIDATION_FAILED:'The file has validation errors. Review a fresh preview.',IMPORT_WORKSPACE_REQUIRED:'Select an imported workspace for this action.'};
    return messages[error.code]??`${error.message} (${error.code})`;
  }
  return error instanceof Error?error.message:'The request could not be completed.';
}
