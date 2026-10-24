import type { Attempt, CaseListResponse, FeedbackRecorded, CaseView, Catalogue, Demonstration, Evidence, Health, HistoryEvent, ReceiptResponse } from './types';
import {notifyCaseActivity} from './caseActivity';
export class ApiError extends Error {
  constructor(public code:string, message:string, public status:number, public retryable=false, public blockingReasons:string[] = []) {super(message);this.name='ApiError';}
}
type Fetcher = (input:RequestInfo|URL, init?:RequestInit)=>Promise<Response>;
export type Operation = {schema_version:'1';operation_id:string;[key:string]:unknown};
const keyFor = (did:string,cid:string,kind:string) => `promisekeeper.operation.${did}.${cid}.${kind}`;
export function pendingOperation(did:string,cid:string,kind:string):Operation|null {
  const raw = localStorage.getItem(keyFor(did,cid,kind));
  if (!raw) return null;
  try {const parsed=JSON.parse(raw); return typeof parsed.operation_id==='string' && parsed.schema_version==='1' ? parsed : null;} catch {throw new Error('The pending operation cannot be read. Keep this copy selected and recover the browser record.');}
}
export function stableOperation(did:string,cid:string,kind:string,payload:Record<string,unknown>):Operation {
  const existing=pendingOperation(did,cid,kind);
  if(existing) {
    const {schema_version:_,operation_id:__,...saved}=existing;
    if(JSON.stringify(saved)!==JSON.stringify(payload)) throw new Error('A pending operation has a different payload. Reconcile it before starting another.');
    return existing;
  }
  const operation:Operation={schema_version:'1',operation_id:crypto.randomUUID(),...payload};
  localStorage.setItem(keyFor(did,cid,kind),JSON.stringify(operation));
  notifyCaseActivity(did,cid);
  return operation;
}
export function clearOperation(did:string,cid:string,kind:string) {localStorage.removeItem(keyFor(did,cid,kind));notifyCaseActivity(did,cid);}
export class ApiClient {
  constructor(private fetcher:Fetcher=(...args)=>fetch(...args)) {}
  async request<T>(path:string,operation?:Operation):Promise<T> {
    let response:Response;let data:unknown;
    const controller=new AbortController();let timeout:ReturnType<typeof setTimeout>|undefined;
    const deadline=new Promise<never>((_,reject)=>{timeout=setTimeout(()=>{controller.abort();reject(new Error('Connection timeout'));},8_000);});
    try {
      response=await Promise.race([this.fetcher(`/api/v1${path}`,{signal:controller.signal,...(operation ? {method:'POST',headers:{'Content-Type':'application/json','X-PromiseKeeper-Request':'1'},body:JSON.stringify(operation)} : {})}),deadline]);
      data=await Promise.race([response.json(),deadline]);
    } catch {throw new ApiError('CONNECTION_UNCERTAIN','Connection unavailable. The outcome is unknown; check the saved operation before retrying.',0,true);}
    finally {clearTimeout(timeout);}
    if(!response.ok) {const detail=(data as {error?:{code?:string;message?:string;retryable?:boolean;blocking_reasons?:string[]}})?.error;throw new ApiError(detail?.code ?? 'SERVER_ERROR',detail?.message ?? 'The request could not be completed.',response.status,detail?.retryable,detail?.blocking_reasons);}
    if(!data || typeof data!=='object' || (data as {schema_version?:string}).schema_version!=='1') throw new ApiError('INVALID_RESPONSE','Unsupported server response. Refresh after checking the connection.',response.status);
    return data as T;
  }
  health() {return this.request<Health>('/health');}
  catalogue() {return this.request<Catalogue>('/catalogue');}
  demonstrations() {return this.request<{schema_version:'1';demonstrations:Demonstration[]}>('/demonstrations');}
  cases(did:string) {return this.request<CaseListResponse>(`/demonstrations/${encodeURIComponent(did)}/cases`);}
  case(did:string,cid:string) {return this.request<CaseView>(`/cases/${encodeURIComponent(cid)}${this.scope(did)}`);}
  evidence(did:string,eid:string) {return this.request<Evidence>(`/evidence-versions/${encodeURIComponent(eid)}${this.scope(did)}`);}
  history(did:string,cid:string,cursor?:number) {return this.request<{schema_version:'1';events:HistoryEvent[];next_cursor:number|null}>(`/cases/${encodeURIComponent(cid)}/history${this.scope(did)}${cursor == null?'':`&cursor=${cursor}`}`);}
  start(did:string,cid:string,operation:Operation) {return this.request<ReceiptResponse>(`/cases/${encodeURIComponent(cid)}/investigations${this.scope(did)}`,operation);}
  attempt(did:string,iid:string) {return this.request<Attempt>(`/investigations/${encodeURIComponent(iid)}${this.scope(did)}`);}
  operation(did:string,oid:string) {return this.request<ReceiptResponse>(`/operations/${encodeURIComponent(oid)}${this.scope(did)}`);}
  create(operation:Operation) {return this.request<ReceiptResponse>('/demonstrations',operation);}
  feedback(did:string,cid:string,operation:Operation) {return this.request<FeedbackRecorded>(`/cases/${encodeURIComponent(cid)}/feedback${this.scope(did)}`,operation);}
  private scope(did:string) {return `?demonstration_id=${encodeURIComponent(did)}`;}
}
export const defaultApi = new ApiClient();
