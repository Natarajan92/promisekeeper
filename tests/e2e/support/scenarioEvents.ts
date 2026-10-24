import { randomUUID } from "node:crypto";
import { expect, type APIRequestContext } from "./test";

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
  let attempt: any;
  await expect.poll(async () => {
    const response = await request.get(`/api/v1/investigations/${receipt.investigation_id}?${scope}`);
    expect(response.status()).toBe(200);
    attempt = await response.json();
    return attempt.status;
  }, { timeout: 10_000 }).not.toBe("RUNNING");
  return attempt;
}
