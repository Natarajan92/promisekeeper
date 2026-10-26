// A committed receipt may arrive before the corresponding case refresh.
// Keep clipboard handoff fenced until that newer saved revision is displayed.
const revisionKey=(did:string,cid:string)=>`promisekeeper.known-revision.${did}.${cid}`;
const investigationKey=(did:string,cid:string)=>`promisekeeper.operation.${did}.${cid}.investigation`;
const intakeKey=(did:string)=>`promisekeeper.intake.pending.${did}`;
const listeners=new Set<(did:string,cid:string)=>void>();

export function notifyCaseActivity(did:string,cid:string) {
  for(const listener of listeners)listener(did,cid);
}
export function notifyWorkspaceActivity(did:string) {for(const listener of listeners)listener(did,'*');}
export function subscribeCaseActivity(did:string,cid:string,listener:()=>void) {
  const changed=(changedDid:string,changedCid:string)=>{if(changedDid===did&&(changedCid===cid||changedCid==='*'))listener();};
  const stored=(event:StorageEvent)=>{
    if((event.storageArea===localStorage||event.storageArea===null)&&
       (event.key===null||event.key===revisionKey(did,cid)||event.key===investigationKey(did,cid)||event.key===intakeKey(did)))listener();
  };
  listeners.add(changed);window.addEventListener('storage',stored);
  return()=>{listeners.delete(changed);window.removeEventListener('storage',stored);};
}
function knownRevision(did:string,cid:string):number {
  const raw=localStorage.getItem(revisionKey(did,cid));
  if(raw===null)return 0;
  const value=Number(raw);
  return Number.isSafeInteger(value)&&value>=0?value:Number.POSITIVE_INFINITY;
}
export function rememberCaseRevision(did:string,cid:string,revision:number|null) {
  if(revision===null||!Number.isSafeInteger(revision)||revision<0)return;
  if(revision>knownRevision(did,cid))localStorage.setItem(revisionKey(did,cid),String(revision));
  notifyCaseActivity(did,cid);
}
export function caseActivitySnapshot(did:string,cid:string):string {
  return JSON.stringify([localStorage.getItem(investigationKey(did,cid)),localStorage.getItem(revisionKey(did,cid)),localStorage.getItem(intakeKey(did))]);
}
export function caseIsUpdating(did:string,cid:string,displayedRevision:number):boolean {
  return localStorage.getItem(investigationKey(did,cid))!==null||localStorage.getItem(intakeKey(did))!==null||knownRevision(did,cid)>displayedRevision;
}
