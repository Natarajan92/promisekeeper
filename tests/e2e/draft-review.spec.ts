import { randomUUID } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { test,expect,type APIRequestContext,type Page } from './support/test';
import { createCopy,investigate,mutationHeaders,confirmScenarioEvent } from './support/scenarioEvents';
import { isolatedServer } from './support/server';

async function caseView(request:APIRequestContext,did:string,cid:string){return (await request.get(`/api/v1/cases/${cid}?demonstration_id=${did}`)).json();}
async function readyDraft(request:APIRequestContext,did:string,cid:string){let view:any;await expect.poll(async()=>{view=await caseView(request,did,cid);return view.draft_generation_state;}).not.toBe('RUNNING');return view;}
async function openReview(page:Page,did:string,cid:string,url='/'){await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),did);await page.goto(`${url.replace(/\/$/,'')}/#/cases/${cid}`);await page.getByRole('button',{name:'Overview',exact:true}).click();}
async function review(request:APIRequestContext,did:string,cid:string,view:any,decision='APPROVE',operation_id=randomUUID()){
  return request.post(`/api/v1/cases/${cid}/draft-reviews?demonstration_id=${did}`,{headers:mutationHeaders,data:{schema_version:'1',operation_id,expected_case_revision:view.case_revision,draft_version_id:view.draft.id,payload_hash:view.draft.payload_hash,expected_review_epoch:view.review_epoch,decision}});
}

test('exact supported edit, approve and reject are durable versions without sending',async({page,request})=>{
  const copy=await createCopy(request);const cid=copy.cases[0].id;
  await investigate(request,copy.id,cid);const initial=await readyDraft(request,copy.id,cid);
  expect(initial.draft.exact_text).toContain('INR 80,000.00');
  await openReview(page,copy.id,cid);
  await expect(page.getByLabel('Draft text')).toHaveValue(initial.draft.exact_text);
  await page.getByLabel('Draft text').fill(initial.draft.exact_text.replace('Hello ','Hi '));
  await expect(page.getByRole('button',{name:'Approve exact saved version'})).toBeDisabled();
  await page.getByRole('button',{name:'Save unapproved version'}).click();
  await expect(page.getByText(/Version 2/).first()).toBeVisible();
  await page.getByRole('button',{name:'Approve exact saved version'}).click();
  await expect(page.locator('#case-draft').getByText(/Approval recorded/)).toBeVisible();
  await page.setViewportSize({width:390,height:844});await page.addStyleTag({content:'html{font-size:200%}'});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
  await expect(page.getByLabel('Draft text')).toBeVisible();await page.screenshot({path:fileURLToPath(new URL('../../.runtime/gate-iv-draft-review-narrow.png',import.meta.url)),fullPage:true});
  let view=await caseView(request,copy.id,cid);expect(view.review_state).toBe('APPROVED');
  const operationId=randomUUID();const rejected=await review(request,copy.id,cid,view,'REJECT',operationId);expect(rejected.status()).toBe(200);
  const repeated=await review(request,copy.id,cid,view,'REJECT',operationId);expect(await repeated.json()).toEqual(await rejected.json());
  view=await caseView(request,copy.id,cid);expect(view.review_state).toBe('REJECTED');expect(view.draft_reviews).toHaveLength(2);
  expect(view.draft_reviews[0].exact_text).toBe(view.draft.exact_text);
  expect((await request.post(`/api/v1/cases/${cid}/send?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:{schema_version:'1',operation_id:randomUUID()}})).ok()).toBe(false);
  expect(await page.getByRole('button',{name:/send/i}).count()).toBe(0);
});

test('unsupported amount, fee, assertion, instructions and placeholder can be saved but not approved',async({request})=>{
  const copy=await createCopy(request,'FV-11-AMOUNT');const cid=copy.cases[0].id;
  await investigate(request,copy.id,cid);let view=await readyDraft(request,copy.id,cid);const original=view.draft.exact_text;
  for(const text of [original.replace('80,000.00','90,000.00'),original+'\nA late fee of INR 500 is due.',original+'\nYou have not paid.',original+'\nPay to bank account 123.',original+'\n[PAYMENT LINK]']){
    const saved=await request.post(`/api/v1/cases/${cid}/draft-versions?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:{schema_version:'1',operation_id:randomUUID(),expected_case_revision:view.case_revision,investigation_id:view.draft.investigation_id,parent_version_id:view.draft.id,recipient:view.draft.recipient,exact_text:text}});
    expect(saved.status()).toBe(201);view=await caseView(request,copy.id,cid);expect(view.draft.validation_status).toBe('INVALID');
    expect((await review(request,copy.id,cid,view)).status()).toBe(409);
  }
});

test('customer clarification is neutral while WAIT and internal verification explain no draft',async({request})=>{
  const copy=await createCopy(request,'FV-13');const cid=copy.cases[2].id;
  await investigate(request,copy.id,cid);const view=await readyDraft(request,copy.id,cid);
  expect(view.current_result.action).toBe('VERIFY_PAYMENT');expect(view.draft.exact_text).toMatch(/reference or receipt/);expect(view.draft.exact_text).not.toMatch(/overdue balance|have not paid|60,000/);
  const baseline=await createCopy(request);
  for(const [index,reason] of [[1,'WAIT_NO_CUSTOMER_DRAFT'],[2,'INTERNAL_VERIFICATION_NO_CUSTOMER_DRAFT']] as const){
    await investigate(request,baseline.id,baseline.cases[index].id);const noDraft=await readyDraft(request,baseline.id,baseline.cases[index].id);expect(noDraft.draft).toBeNull();expect(noDraft.no_draft_reason).toBe(reason);
  }
});

test('new evidence, changed heads and successful superseding results block old approval',async({request})=>{
  const copy=await createCopy(request,'FV-17-EVIDENCE');const cid=copy.cases[0].id;
  await investigate(request,copy.id,cid);const original=await readyDraft(request,copy.id,cid);
  expect((await review(request,copy.id,cid,original)).status()).toBe(200);
  await confirmScenarioEvent(request,copy.id,cid,'PK-001-U1');
  const stale=await caseView(request,copy.id,cid);expect(stale.review_state).toBe('INVALIDATED');expect((await review(request,copy.id,cid,stale)).status()).toBe(409);
  await investigate(request,copy.id,cid);const newer=await readyDraft(request,copy.id,cid);
  expect(newer.current_result.investigation_id).not.toBe(original.draft.investigation_id);expect(newer.draft).toBeNull();expect(newer.no_draft_reason).toBe('WAIT_NO_CUSTOMER_DRAFT');
  const oldReview={...newer,draft:original.draft};expect((await review(request,copy.id,cid,oldReview)).status()).toBe(409);
});

test('lost save response reconciles after reload with exactly one new immutable version',async({page,request})=>{
  const copy=await createCopy(request);const cid=copy.cases[0].id;await investigate(request,copy.id,cid);const initial=await readyDraft(request,copy.id,cid);
  await openReview(page,copy.id,cid);const changed=initial.draft.exact_text.replace('Hello ','Hi ');
  await page.getByLabel('Draft text').fill(changed);
  let operationId='';const routePattern=`**/api/v1/cases/${cid}/draft-versions?*`;
  await page.route(routePattern,async route=>{operationId=route.request().postDataJSON().operation_id;expect((await route.fetch()).status()).toBe(201);await route.abort('connectionreset');});
  await page.getByRole('button',{name:'Save unapproved version'}).click();await expect(page.getByText(/Connection unavailable/).first()).toBeVisible();
  await page.unroute(routePattern);await page.reload();await page.getByRole('button',{name:'Overview',exact:true}).click();
  await expect(page.locator('#case-draft').getByText('New unapproved version saved.')).toBeVisible();await expect(page.getByLabel('Draft text')).toHaveValue(changed);
  const view=await caseView(request,copy.id,cid);expect(view.draft.version).toBe(2);
  expect((await request.get(`/api/v1/operations/${operationId}?demonstration_id=${copy.id}`)).status()).toBe(200);
});

test('failed rerun invalidates approval and requires fresh explicit approval after unchanged evidence',async({playwright,page})=>{
  const server=await isolatedServer(0,'rerun-fails');await server.start();const request=await playwright.request.newContext({baseURL:server.url});
  try{
    const copy=await createCopy(request,'FV-17-UNCHANGED');const cid=copy.cases[0].id;await investigate(request,copy.id,cid);let view=await readyDraft(request,copy.id,cid);expect((await review(request,copy.id,cid,view)).status()).toBe(200);
    await openReview(page,copy.id,cid,server.url);await page.getByRole('button',{name:'Investigate case',exact:true}).click();
    await expect(page.getByRole('button',{name:'Approve exact saved version'})).toBeDisabled();
    await expect(page.getByText(/Investigation incomplete:/)).toBeVisible();
    view=await caseView(request,copy.id,cid);expect(view.review_state).toBe('INVALIDATED');expect(view.draft_reviews).toHaveLength(1);
    await expect(page.getByRole('button',{name:'Approve exact saved version'})).toBeEnabled();await page.getByRole('button',{name:'Approve exact saved version'}).click();
    await expect(page.locator('#case-draft').getByText(/Approval recorded/)).toBeVisible();view=await caseView(request,copy.id,cid);expect(view.review_state).toBe('APPROVED');expect(view.draft_reviews).toHaveLength(2);expect(view.draft_reviews[1].review_epoch).toBeGreaterThan(view.draft_reviews[0].review_epoch);
  }finally{await request.dispose();await server.stop();}
});

test('failed draft retry preserves its saved recommendation and succeeds independently',async({playwright,page})=>{
  const server=await isolatedServer(0,'draft-fails-once');await server.start();const request=await playwright.request.newContext({baseURL:server.url});
  try{
    const copy=await createCopy(request);const cid=copy.cases[0].id;const result=await investigate(request,copy.id,cid);const failed=await readyDraft(request,copy.id,cid);expect(failed.draft_generation_state).toBe('FAILED');
    await openReview(page,copy.id,cid,server.url);await page.getByRole('button',{name:'Retry failed draft step'}).click();await expect(page.getByLabel('Draft text')).toBeVisible();
    const ready=await readyDraft(request,copy.id,cid);expect(ready.current_result.result_hash).toBe(result.result.result_hash);expect(ready.draft_generation_state).toBe('READY');
  }finally{await request.dispose();await server.stop();}
});
test('FV-17 evidence arriving during a failed rerun keeps prior approval invalidated',async({playwright})=>{
  const server=await isolatedServer(0,'rerun-fails');await server.start();const request=await playwright.request.newContext({baseURL:server.url});
  try{
    const copy=await createCopy(request,'FV-17-EVIDENCE');const cid=copy.cases[0].id;await investigate(request,copy.id,cid);const initial=await readyDraft(request,copy.id,cid);
    expect((await review(request,copy.id,cid,initial)).status()).toBe(200);
    await confirmScenarioEvent(request,copy.id,cid,'FV-17-EVIDENCE-RUN-START');const before=await caseView(request,copy.id,cid);
    const started=await request.post(`/api/v1/cases/${cid}/investigations?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:{schema_version:'1',operation_id:randomUUID(),expected_case_revision:before.case_revision,retry_of:null}});
    expect(started.status()).toBe(202);const id=(await started.json()).investigation_id;
    await confirmScenarioEvent(request,copy.id,cid,'PK-001-U1');
    await expect.poll(async()=> (await (await request.get(`/api/v1/investigations/${id}?demonstration_id=${copy.id}`)).json()).status).toBe('INCOMPLETE');
    const after=await caseView(request,copy.id,cid);expect(after.latest_completed_result.result_hash).toBe(initial.current_result.result_hash);expect(after.current_result).toBeNull();expect(after.review_state).toBe('INVALIDATED');expect((await review(request,copy.id,cid,after)).status()).toBe(409);
  }finally{await request.dispose();await server.stop();}
});
test('FV-17 successful supersession and changed edit head block old approvals even without new evidence',async({request})=>{
  const copy=await createCopy(request,'FV-17-SUPERSEDED');const cid=copy.cases[0].id;await investigate(request,copy.id,cid);const original=await readyDraft(request,copy.id,cid);
  expect((await review(request,copy.id,cid,original)).status()).toBe(200);
  await investigate(request,copy.id,cid);let newer=await readyDraft(request,copy.id,cid);expect(newer.draft.id).not.toBe(original.draft.id);expect((await review(request,copy.id,cid,{...newer,draft:original.draft})).status()).toBe(409);
  const head=newer.draft;
  const base={schema_version:'1',operation_id:randomUUID(),expected_case_revision:newer.case_revision,investigation_id:head.investigation_id,parent_version_id:head.id,recipient:head.recipient,exact_text:head.exact_text.replace('Hello ','Hi ')};
  const saved=await request.post(`/api/v1/cases/${cid}/draft-versions?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:base});expect(saved.status()).toBe(201);
  newer=await caseView(request,copy.id,cid);expect((await review(request,copy.id,cid,{...newer,draft:head})).status()).toBe(409);
  const wrong=await request.post(`/api/v1/cases/${cid}/draft-versions?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:{...base,operation_id:randomUUID(),expected_case_revision:newer.case_revision,parent_version_id:newer.draft.id,recipient:'Unregistered recipient'}});expect(wrong.status()).toBe(422);
});
test('pending save outcome survives Review to History navigation and unlocks every consumer',async({page,request})=>{
  const copy=await createCopy(request);const cid=copy.cases[0].id;await investigate(request,copy.id,cid);const original=await readyDraft(request,copy.id,cid);await openReview(page,copy.id,cid);
  const text=original.draft.exact_text.replace('Hello ','Hi ');await page.getByLabel('Draft text').fill(text);
  let release!:()=>void;const delayed=new Promise<void>(resolve=>{release=resolve;});const pattern=`**/api/v1/cases/${cid}/draft-versions?*`;
  await page.route(pattern,async route=>{await delayed;await route.fulfill({response:await route.fetch()});});
  try{
    await page.getByRole('button',{name:'Save unapproved version'}).click();await page.getByRole('button',{name:'History',exact:true}).click();
    await expect(page.getByRole('button',{name:'Accept recommendation'})).toBeDisabled();release();
    await expect(page.getByRole('button',{name:'Accept recommendation'})).toBeEnabled();await expect(page.getByRole('button',{name:'Preview selected fictional update'})).toBeEnabled();
    await page.getByRole('button',{name:'Overview',exact:true}).click();await expect(page.getByLabel('Draft text')).toHaveValue(text);await expect(page.getByRole('button',{name:'Approve exact saved version'})).toBeEnabled();expect((await caseView(request,copy.id,cid)).draft.version).toBe(2);
  }finally{release();await page.unroute(pattern);}
});
