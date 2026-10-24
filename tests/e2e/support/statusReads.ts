import type { APIRequestContext } from './test';

export type RetryableReadError = {url:string;observed_at:string;http_status:503;code:string};

// One GET only. The caller owns its existing bounded poll; commands are never replayed here.
export async function readAvailable(request:APIRequestContext,url:string,errors:RetryableReadError[],timeout?:number) {
  const response=await request.get(url,{timeout});
  const body=await response.json();
  if(response.status()===503&&body.schema_version==='1'&&body.error?.retryable===true&&
    ['STORAGE_UNAVAILABLE','RECOVERY_IN_PROGRESS'].includes(body.error.code)) {
    errors.push({url,observed_at:new Date().toISOString(),http_status:503,code:body.error.code});
    return null;
  }
  if(response.status()!==200)throw new Error(`GET ${url}: unexpected HTTP ${response.status()} (${body.error?.code??'untyped error'})`);
  return body;
}
