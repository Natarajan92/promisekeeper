import { randomUUID } from 'node:crypto';
import { test,expect,type APIRequestContext,type Page } from './support/test';
import { createCopy,investigate,mutationHeaders,confirmScenarioEvent } from './support/scenarioEvents';
import { isolatedServer } from './support/server';
import { readAvailable, type RetryableReadError } from './support/statusReads';
import { showAllCases } from './support/fixtures';

async function detail(request:APIRequestContext,did:string,cid:string){return (await request.get(`/api/v1/cases/${cid}?demonstration_id=${did}`)).json();}
async function openCase(page:Page,did:string,caseCode='PK-003',url='/'){
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),did);await page.goto(url);
  await page.getByRole('link',{name:/^Cases/}).click();await showAllCases(page);await page.getByRole('button',{name:new RegExp(caseCode)}).first().click();await page.getByRole('button',{name:'History',exact:true}).click();
}
async function closeCase(request:APIRequestContext,did:string,cid:string){const view=await detail(request,did,cid);const command={schema_version:'1',operation_id:randomUUID(),expected_case_revision:view.case_revision,investigation_id:view.current_result.investigation_id,confirmed_result_hash:view.current_result.result_hash,confirm:true};const response=await request.post(`/api/v1/cases/${cid}/closure?demonstration_id=${did}`,{headers:mutationHeaders,data:command});expect(response.status()).toBe(200);return {command,response:await response.json()};}

test('PK-003 preview, settlement, advice disposition and explicit closure preserve the original result',async({page,request})=>{
  const copy=await createCopy(request);const cid=copy.cases[2].id;const earlier=await investigate(request,copy.id,cid);
  await openCase(page,copy.id);await expect(page.getByRole('button',{name:'Review case closure',exact:true})).toBeDisabled();
  await page.getByLabel('Fictional update').selectOption('PK-003-U1');await page.getByRole('button',{name:'Preview selected fictional update'}).click();
  await expect(page.getByText(/Exact update preview/)).toBeVisible();await page.getByLabel('I reviewed this exact fictional update').check();await page.getByRole('button',{name:'Confirm fictional update'}).click();
  await expect(page.getByText(/evidence changed/i).first()).toBeVisible();await expect(page.getByRole('button',{name:'Review case closure',exact:true})).toBeDisabled();
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();await expect(page.getByRole('button',{name:'Review case closure',exact:true})).toBeEnabled();
  await page.getByLabel('Advice decision reason (optional)').fill('The settlement evidence is clear.');await page.getByRole('button',{name:'Accept recommendation'}).click();await expect(page.getByText('Decision saved.').first()).toBeVisible();
  expect((await detail(request,copy.id,cid)).lifecycle).toBe('OPEN');
  await page.getByRole('button',{name:'Review case closure',exact:true}).click();await page.getByLabel('Confirm closure of invoice CR-312').check();await page.getByRole('button',{name:'Confirm case closure'}).click();
  await expect(page.getByText(/PK-003 \/ CR-312 \/ CLOSED/)).toBeVisible();const closed=await detail(request,copy.id,cid);expect(closed.lifecycle).toBe('CLOSED');
  const old=await (await request.get(`/api/v1/investigations/${earlier.investigation_id}?demonstration_id=${copy.id}`)).json();expect(old.result).toEqual(earlier.result);expect(old.result.action).toBe('VERIFY_PAYMENT');
  // Reload keeps the case route, so the same case page reopens.
  await page.reload();await expect(page.getByRole('heading',{level:1,name:copy.cases[2].client})).toBeVisible();await page.getByRole('button',{name:'History',exact:true}).click();
  await page.getByRole('button',{name:'Review case reopening'}).click();await page.getByLabel('Confirm reopening of invoice CR-312').check();await page.getByRole('button',{name:'Confirm case reopening'}).click();
  await expect(page.getByText(/PK-003 \/ CR-312 \/ OPEN/)).toBeVisible();
  const history=await (await request.get(`/api/v1/cases/${cid}/history?demonstration_id=${copy.id}&limit=100`)).json();expect(history.events.filter((e:any)=>e.event_type==='CASE_CLOSED')).toHaveLength(1);expect(history.events.filter((e:any)=>e.event_type==='CASE_REOPENED')).toHaveLength(1);
  expect((await detail(request,copy.id,cid)).owner_dispositions[0]).toMatchObject({decision:'ACCEPT',reason:'The settlement evidence is clear.'});
});

test('exact closure confirmation replays once and wrong/stale hashes cannot close',async({request})=>{
  const copy=await createCopy(request);const cid=copy.cases[2].id;await confirmScenarioEvent(request,copy.id,cid,'PK-003-U1');await investigate(request,copy.id,cid);let view=await detail(request,copy.id,cid);
  const invalid={schema_version:'1',operation_id:randomUUID(),expected_case_revision:view.case_revision,investigation_id:view.current_result.investigation_id,confirmed_result_hash:'f'.repeat(64),confirm:true};
  expect((await request.post(`/api/v1/cases/${cid}/closure?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:invalid})).status()).toBe(409);
  const closed=await closeCase(request,copy.id,cid);const replay=await request.post(`/api/v1/cases/${cid}/closure?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:closed.command});expect(await replay.json()).toEqual(closed.response);
  const operation=await request.get(`/api/v1/operations/${closed.command.operation_id}?demonstration_id=${copy.id}`);expect(await operation.json()).toEqual(closed.response);
  view=await detail(request,copy.id,cid);expect(view.lifecycle).toBe('CLOSED');expect(view.allowed_commands.start_investigation.allowed).toBe(false);
});

test('history preserves exact drafts, decisions and source versions through real backend restart',async({playwright,page})=>{
  const server=await isolatedServer();await server.start();const request=await playwright.request.newContext({baseURL:server.url});
  try{
    const copy=await createCopy(request);const cid=copy.cases[0].id;await investigate(request,copy.id,cid);let view:any;
    await expect.poll(async()=>{view=await detail(request,copy.id,cid);return view.draft_generation_state;}).toBe('READY');const original=view.draft;
    const reviewed=await request.post(`/api/v1/cases/${cid}/draft-reviews?demonstration_id=${copy.id}`,{headers:mutationHeaders,data:{schema_version:'1',operation_id:randomUUID(),expected_case_revision:view.case_revision,draft_version_id:original.id,payload_hash:original.payload_hash,expected_review_epoch:view.review_epoch,decision:'REJECT'}});expect(reviewed.status()).toBe(200);
    const before=await (await request.get(`/api/v1/cases/${cid}/history?demonstration_id=${copy.id}&limit=100`)).json();await server.stop();await server.start();
    const after=await (await request.get(`/api/v1/cases/${cid}/history?demonstration_id=${copy.id}&limit=100`)).json();expect(after).toEqual(before);
    const exact=await (await request.get(`/api/v1/draft-versions/${original.id}?demonstration_id=${copy.id}`)).json();expect(exact.draft_version).toEqual(original);
    await openCase(page,copy.id,'PK-001',server.url);await page.getByRole('button',{name:'Inspect saved draft'}).first().click();await expect(page.getByRole('article').getByText(original.exact_text,{exact:true})).toBeVisible();
    await page.getByRole('button',{name:'Inspect investigation'}).first().click();await expect(page.getByText('Historical recommendation: FOLLOW_UP')).toBeVisible();
    await page.getByRole('button',{name:/PK-001-I1/}).last().click();await expect(page.getByRole('dialog')).toBeVisible();await expect(page.getByRole('dialog').getByText(/Fictional invoice NS-104/)).toBeVisible();
  }finally{await request.dispose();await server.stop();}
});

test('deleting the selected copy clears its browser selection and preserves another copy and receipts',async({page,request})=>{
  const removed=await createCopy(request);const kept=await createCopy(request);await openCase(page,removed.id,'PK-001');
  await page.getByRole('button',{name:/^Workspace/}).click();await page.getByText('Delete selected demonstration',{exact:true}).click();await page.getByRole('button',{name:'Review selected-copy deletion'}).click();await page.getByLabel('Confirm deletion of this selected demonstration').check();await page.getByRole('button',{name:'Delete this demonstration'}).click();
  await expect.poll(()=>page.evaluate(()=>localStorage.getItem('selected_demonstration_id'))).not.toBe(removed.id);
  const copies=await (await request.get('/api/v1/demonstrations')).json();expect(copies.demonstrations.some((d:any)=>d.id===removed.id)).toBe(false);expect(copies.demonstrations.some((d:any)=>d.id===kept.id)).toBe(true);
  expect((await request.get(`/api/v1/demonstrations/${kept.id}/cases`)).status()).toBe(200);
});
test('later conflicting evidence on a closed case requires explicit reopening and preserves closure history',async({playwright,page})=>{
  const server=await isolatedServer(0,'closed-conflict');await server.start();const request=await playwright.request.newContext({baseURL:server.url});
  try{
    const copy=await createCopy(request);const cid=copy.cases[2].id;await confirmScenarioEvent(request,copy.id,cid,'PK-003-U1');const settled=await investigate(request,copy.id,cid);await closeCase(request,copy.id,cid);
    await openCase(page,copy.id,'PK-003',server.url);await page.getByLabel('Fictional update').selectOption('TEST-PK-003-CONFLICT');await page.getByRole('button',{name:'Preview selected fictional update'}).click();await page.getByLabel('I reviewed this exact fictional update').check();await page.getByRole('button',{name:'Confirm fictional update'}).click();
    await expect(page.getByText(/Review required:.*evidence changed/i)).toBeVisible();let view=await detail(request,copy.id,cid);expect(view.lifecycle).toBe('CLOSED');expect(view.current_result).toBeNull();expect(view.latest_completed_result.result_hash).toBe(settled.result.result_hash);await expect(page.getByRole('button',{name:'Investigate case',exact:true})).toBeDisabled();
    await page.getByRole('button',{name:'Review case reopening'}).click();await page.getByLabel('Confirm reopening of invoice CR-312').check();await page.getByRole('button',{name:'Confirm case reopening'}).click();await expect(page.getByRole('button',{name:'Investigate case',exact:true})).toBeEnabled();
    await page.getByRole('button',{name:'Investigate case',exact:true}).click();await expect.poll(async()=>{view=await detail(request,copy.id,cid);return view.current_result?.action;}).toBe('VERIFY_PAYMENT');expect(view.current_result.financial_facts.certainty).toBe('UNKNOWN');
    const history=await (await request.get(`/api/v1/cases/${cid}/history?demonstration_id=${copy.id}&limit=100`)).json();expect(history.events.filter((e:any)=>e.event_type==='CASE_CLOSED')).toHaveLength(1);expect(history.events.filter((e:any)=>e.event_type==='CASE_REOPENED')).toHaveLength(1);
  }finally{await request.dispose();await server.stop();}
});
for(const destination of ['Overview','another copy'] as const){
  test(`deletion outcome survives navigation to ${destination} without clearing another selected copy`,async({page,request})=>{
    const removed=await createCopy(request);const kept=await createCopy(request);await openCase(page,removed.id,'PK-001');
    let release!:()=>void;const delayed=new Promise<void>(resolve=>{release=resolve;});const pattern=`**/api/v1/demonstrations/${removed.id}/deletion`;
    let entered!:()=>void;const routeEntered=new Promise<void>(resolve=>{entered=resolve;});
    const handlers:Promise<void>[]=[];const readErrors:RetryableReadError[]=[];
    await page.route(pattern,route=>{
      entered();
      const handler=(async()=>{await delayed;await route.fulfill({response:await route.fetch()});})();
      handlers.push(handler);
      return handler;
    });
    try{
      await page.getByRole('button',{name:/^Workspace/}).click();await page.getByText('Delete selected demonstration',{exact:true}).click();await page.getByRole('button',{name:'Review selected-copy deletion'}).click();await page.getByLabel('Confirm deletion of this selected demonstration').check();await page.getByRole('button',{name:'Delete this demonstration'}).click();
      await routeEntered;
      if(destination==='Overview')await page.getByRole('button',{name:'Overview',exact:true}).click();else await page.getByRole('combobox',{name:'Demonstration copy'}).selectOption(kept.id);
      release();const listingDeadline=Date.now()+7_000;await expect.poll(async()=>{
        const observed=await readAvailable(request,'/api/v1/demonstrations',readErrors,Math.max(1,listingDeadline-Date.now()));
        if(observed===null)return 'UNOBSERVED';
        expect(Array.isArray(observed.demonstrations)).toBe(true);
        return observed.demonstrations.some((d:any)=>d.id===removed.id);
      }).toBe(false);
      await expect.poll(()=>page.evaluate(()=>localStorage.getItem('selected_demonstration_id'))).not.toBe(removed.id);
      if(destination==='another copy')await expect.poll(()=>page.evaluate(()=>localStorage.getItem('selected_demonstration_id'))).toBe(kept.id);
    }finally{
      release();
      try {await Promise.all(handlers);}
      finally {
        await page.unroute(pattern);
        if(readErrors.length)await test.info().attach('deletion-listing-read-errors',{body:JSON.stringify(readErrors,null,2),contentType:'application/json'});
      }
    }
  });
}
