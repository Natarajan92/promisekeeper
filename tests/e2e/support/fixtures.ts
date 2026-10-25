import { randomUUID } from 'node:crypto';
import { expect, type APIRequestContext, type Page } from './test';
import { mutationHeaders } from './scenarioEvents';

// The case overview shows cases needing attention by default; settled and closed cases sit behind Show all.
export async function showAllCases(page:Page) {
  const toggle=page.getByRole('button',{name:/Show all \d+ cases/});
  await toggle.waitFor();
  await toggle.click();
}

export const faultPresets = ['kill-after-start','kill-after-result','kill-after-draft','kill-after-approval','kill-after-closure','retry-exhaustion','late-provider','blocked-provider'] as const;
export type FaultPreset = typeof faultPresets[number];
export async function caseView(request:APIRequestContext,did:string,cid:string) {
  const response=await request.get(`/api/v1/cases/${cid}?demonstration_id=${did}`);
  expect(response.status()).toBe(200);return response.json();
}
export function command(view:any,fields:Record<string,unknown>={}) {
  return {schema_version:'1',operation_id:randomUUID(),expected_case_revision:view.case_revision,...fields};
}
export async function post(request:APIRequestContext,did:string,cid:string,endpoint:string,data:any) {
  return request.post(`/api/v1/cases/${cid}/${endpoint}?demonstration_id=${did}`,{headers:mutationHeaders,data,timeout:10_000});
}
export async function readyDraft(request:APIRequestContext,did:string,cid:string) {
  let view:any;await expect.poll(async()=>{view=await caseView(request,did,cid);return view.draft_generation_state;}).toBe('READY');return view;
}
export async function history(request:APIRequestContext,did:string,cid:string) {
  return (await (await request.get(`/api/v1/cases/${cid}/history?demonstration_id=${did}&limit=100`)).json()).events;
}
