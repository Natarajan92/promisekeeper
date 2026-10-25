import { randomUUID } from "node:crypto";
import { test, expect, type APIRequestContext } from "./test";
import { readAvailable, type RetryableReadError } from './statusReads';

export const mutationHeaders = { "X-PromiseKeeper-Request": "1" };

export async function createCopy(request: APIRequestContext, variant_id: string | null = null) {
  const response = await request.post("/api/v1/demonstrations", { headers: mutationHeaders, data: {
    schema_version: "1", operation_id: randomUUID(), catalogue_version: "release-0.1", variant_id, clock_mode: "REFERENCE",
  } });
  expect(response.status()).toBe(201);
  const { demonstration_id } = await response.json();
  const cases = await request.get(`/api/v1/demonstrations/${demonstration_id}/cases`);
  expect(cases.status()).toBe(200);
  return { id: demonstration_id as string, cases: (await cases.json()).cases as {id:string;catalogue_case_id:string;client:string}[] };
}

export async function confirmScenarioEvent(request: APIRequestContext, demonstration_id: string, case_id: string, event_id: string) {
  const query = `demonstration_id=${demonstration_id}`;
  const preview = await request.get(`/api/v1/cases/${case_id}/scenario-events/${event_id}/preview?${query}`);
  expect(preview.status()).toBe(200);
  const reviewed = await preview.json();
  const response = await request.post(`/api/v1/cases/${case_id}/scenario-events?${query}`, {
    headers: mutationHeaders, data: { schema_version: "1", operation_id: randomUUID(),
      expected_case_revision: reviewed.expected_case_revision, event_id: reviewed.event_id,
      catalogue_version: reviewed.catalogue_version, confirmed_preview_hash: reviewed.preview_hash },
  });
  expect(response.status()).toBe(200);
  return response.json();
}

export async function investigate(request: APIRequestContext, demonstration_id: string, case_id: string) {
  const scope = `demonstration_id=${demonstration_id}`;
  const detail = await request.get(`/api/v1/cases/${case_id}?${scope}`);
  expect(detail.status()).toBe(200);
  const current = await detail.json();
  const started = await request.post(`/api/v1/cases/${case_id}/investigations?${scope}`, {
    headers: mutationHeaders, data: { schema_version: "1", operation_id: randomUUID(),
      expected_case_revision: current.case_revision, retry_of: null },
  });
  expect(started.status()).toBe(202);
  const receipt = await started.json();
  const url = `/api/v1/investigations/${receipt.investigation_id}?${scope}`;
  const attempt = await waitForInvestigation(request, url);
  // The drafting agents run after the result is saved; saving their draft advances the case revision.
  await expect.poll(async () => (await (await request.get(url)).json()).draft_status, {timeout: 20_000}).not.toBe('RUNNING');
  return attempt;
}

export async function waitForInvestigation(request:APIRequestContext,url:string,errors:RetryableReadError[]=[]) {
  let attempt:any;
  const deadline=Date.now()+10_000;
  try {
    await expect.poll(async()=>{
      const observed=await readAvailable(request,url,errors,Math.max(1,deadline-Date.now()));
      if(observed===null)return 'UNOBSERVED';
      if(!['RUNNING','COMPLETE','LIMITED','INCOMPLETE'].includes(observed.status))
        throw new Error(`GET ${url}: unexpected investigation status ${String(observed.status)}`);
      attempt=observed;
      return observed.status;
    },{timeout:10_000}).toMatch(/^(COMPLETE|LIMITED|INCOMPLETE)$/);
    return attempt;
  } finally {
    if(errors.length)await test.info().attach('investigation-status-read-errors',{body:JSON.stringify(errors,null,2),contentType:'application/json'});
  }
}
