import {readFileSync,mkdirSync} from 'node:fs';
import {execFileSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
import path from 'node:path';
import {test,expect,type Page} from './support/test';

test.use({actionTimeout:10_000});
const repo=fileURLToPath(new URL('../../',import.meta.url));
let folder=path.join(repo,'docs/demo-import/synthetic-pack');
let manifest=JSON.parse(readFileSync(path.join(folder,'EXPECTED-RESULTS.json'),'utf8'));
test.beforeAll(()=>{
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  if(manifest.as_of!==today){
    folder=path.join(repo,'.runtime/synthetic-pack',`browser-${Date.now()}`);mkdirSync(folder,{recursive:true});
    execFileSync(path.join(repo,'backend/.venv/Scripts/python.exe'),['-m','promisekeeper.fixtures.synthetic_pack','--output',folder],{cwd:repo,windowsHide:true});
    manifest=JSON.parse(readFileSync(path.join(folder,'EXPECTED-RESULTS.json'),'utf8'));
  }
});

async function preview(page:Page,kind:string,name:string,cid?:string,contextOnly=false){
  await page.getByRole('combobox',{name:'File type',exact:true}).selectOption(kind);
  if(cid)await page.getByRole('combobox',{name:'Attach communication to invoice',exact:true}).selectOption(cid);
  await page.getByLabel('Upload file').setInputFiles(path.join(folder,name));
  if(['customer_email','remittance_email','whatsapp'].includes(kind))await page.getByRole('combobox',{name:'Who sent this message?',exact:true}).selectOption('CUSTOMER');
  if(contextOnly){
    await page.getByText('Optional: supporting context only',{exact:true}).click();
    await page.getByLabel(/I reviewed unsupported wording as supporting context only/).check();
  }
  await page.getByRole('button',{name:'Preview file',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview'})).toBeVisible();
}
async function upload(page:Page,kind:string,name:string,cid?:string,contextOnly=false){
  await preview(page,kind,name,cid,contextOnly);await expect(page.locator('.intake-preview [role=alert]')).toHaveCount(0);
  await page.getByLabel('I reviewed this preview and confirm the records are correct.').check();
  if(kind==='allocations')await page.getByLabel('I checked the settled receipts and the existing invoice allocations in this export.').check();
  await page.getByRole('button',{name:'Confirm import',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview'})).toHaveCount(0);
  await expect(page.locator('.intake-workspace-summary')).toBeVisible();
}
// Navigation only: open the Upload page (if needed) and the given step of its stepper.
async function step(page:Page,n:number){
  if(!page.url().includes('#/upload'))await page.getByRole('navigation',{name:'Pages'}).getByRole('link',{name:/^Upload/}).click();
  await page.getByRole('navigation',{name:'Upload steps'}).getByRole('link',{name:new RegExp(`^Step ${n} `)}).click();
  await expect(page.getByRole('heading',{level:2,name:new RegExp(`^Step ${n} ·`)})).toBeVisible();
}
async function openCase(page:Page,name:RegExp){
  await page.getByRole('navigation',{name:'Pages'}).getByRole('link',{name:/^Cases/}).click();
  await page.getByRole('button',{name}).click();
}
async function cover(page:Page){
  const rows=page.locator('.intake-invoice');
  for(let i=0;i<await rows.count();i++){
    const row=rows.nth(i);const button=row.getByRole('button',{name:/^Confirm ledger review/});
    if(await button.count()){await row.getByRole('checkbox').check();await button.click();await expect(row).toContainText('Payment records reviewed through');}
  }
}
async function startNew(page:Page){
  const discovered=page.waitForResponse(response=>response.url().endsWith('/api/v1/demonstrations')&&response.request().method()==='GET');
  await page.goto('/#/upload?step=1');await discovered;
  await expect(page.getByText('Loading saved workspaces…',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('combobox',{name:'File type',exact:true})).toBeVisible();
  const fresh=page.getByLabel('Create a new imported workspace instead');
  if(await fresh.count())await fresh.check();
}

test('nuanced synthetic files: six invoices, split paise, invalid previews, approved copy and delayed settlement',async({page,request,context})=>{
  test.setTimeout(180_000);
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  await startNew(page);
  await upload(page,'customers','01-customers.csv');
  const did=await page.evaluate(()=>localStorage.getItem('selected_demonstration_id'));
  await step(page,2);await upload(page,'invoices','02-invoices.csv');await step(page,3);await upload(page,'payments','03-receipts-initial.csv');
  const endpoint=`/api/v1/demonstrations/${did}/intake`;
  const state=async()=>(await (await request.get(endpoint)).json());
  const data=await state(),ids:Record<string,string>=Object.fromEntries(data.cases.map((c:any)=>[c.invoice_id,c.id]));
  expect(data.payments).toHaveLength(9);expect(data.payments.every((p:any)=>p.allocations.length===0)).toBe(true);
  const missing=data.payments.find((p:any)=>p.transaction_ref==='MYSTERY-T1');expect(missing.candidates).toEqual([]);
  expect(data.payments.find((p:any)=>p.transaction_ref==='ECON-T1').candidates.map((c:any)=>c.invoice_id)).toEqual(['ECON-101','ECON-102']);
  await step(page,5);await expect(page.locator('.intake-receipt').filter({has:page.getByRole('heading',{name:'NOVA-PENDING',exact:true})})).toBeVisible();
  await expect(page.getByRole('button',{name:'Confirm allocation for NOVA-PENDING',exact:true})).toHaveCount(0);
  await expect(page.getByRole('button',{name:'Confirm allocation for KITE-REVERSED',exact:true})).toHaveCount(0);
  await page.getByText('Optional: import existing allocations',{exact:true}).click();
  await upload(page,'allocations','03a-existing-allocations.csv');
  for(const item of manifest.manual_allocations){
    const receipt=page.locator('.intake-receipt').filter({has:page.getByRole('heading',{name:item.transaction_ref,exact:true})});
    await receipt.getByRole('combobox',{name:`Invoice for ${item.transaction_ref}`,exact:true}).selectOption(ids[item.invoice_id]);
    await receipt.getByLabel(`Allocation amount for ${item.transaction_ref} (INR)`).fill(item.amount);
    await receipt.getByLabel('I checked this settled receipt and its invoice allocation.').check();
    const before=(await state()).payments.find((p:any)=>p.transaction_ref===item.transaction_ref).remaining_minor;
    await receipt.getByRole('button',{name:`Confirm allocation for ${item.transaction_ref}`,exact:true}).click();
    await expect.poll(async()=>(await state()).payments.find((p:any)=>p.transaction_ref===item.transaction_ref).remaining_minor).not.toBe(before);
    await expect(page.getByRole('button',{name:'Refresh imported records'})).toBeEnabled();
  }
  expect((await state()).payments.find((p:any)=>p.transaction_ref==='NOVA-T1').remaining_minor).toBe('2000000');
  await step(page,4);for(const item of manifest.documents)await upload(page,item.kind,item.path,ids[item.invoice_id]);
  // These are intentional negative demonstrations, not valid-file imports.
  for(const item of [manifest.rejected.find((x:any)=>x.path.endsWith('pending-allocation.csv')),manifest.rejected.find((x:any)=>x.path.endsWith('multiple-amounts.txt')),manifest.rejected.find((x:any)=>x.path.endsWith('shared-date-alternatives.txt'))]){
    const before=await state();await preview(page,item.kind,item.path,item.invoice_id?ids[item.invoice_id]:undefined);
    await expect(page.locator('.intake-preview [role=alert]')).toBeVisible();
    await expect(page.getByRole('button',{name:'Confirm import',exact:true})).toHaveCount(0);
    expect(await state()).toEqual(before);
  }
  await step(page,6);await cover(page);
  await page.getByRole('button',{name:'Start morning review',exact:true}).click();
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.')).toBeVisible({timeout:45_000});
  const read=async(invoice:string)=>(await (await request.get(`/api/v1/cases/${ids[invoice]}?demonstration_id=${did}`)).json());
  for(const item of manifest.cases){const view=await read(item.invoice_id);expect(view.current_result.action).toBe(item.action);expect(view.current_result.financial_facts.balance.minor_units).toBe(item.remainder_minor);expect(view.lifecycle).toBe('OPEN');}
  await openCase(page,/PK-003.*Kite Creative Studio/);await expect(page.getByRole('heading',{name:'Communication review'})).toBeVisible();
  const draft=(await read('KITE-201')).draft.exact_text;
  await page.getByRole('button',{name:'Approve exact saved version',exact:true}).click();await page.getByRole('button',{name:'Copy approved message',exact:true}).click();
  expect((await page.evaluate(()=>navigator.clipboard.readText())).replaceAll('\r\n','\n')).toBe(draft);
  await page.screenshot({path:'.runtime/synthetic-pack/morning-review.png'});
  const original=(await read('ECON-101')).current_result;
  await step(page,3);await upload(page,'payments','05-later/receipts-later.csv');
  // The earlier approval no longer offers a copy once new records arrive (checked where that case shows its message review).
  await openCase(page,/PK-003.*Kite Creative Studio/);await expect(page.getByRole('heading',{name:'Communication review'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Copy approved message',exact:true})).toHaveCount(0);
  await step(page,5);await page.getByText('Optional: import existing allocations',{exact:true}).click();
  await upload(page,'allocations','05-later/allocation-later.csv');await step(page,6);await cover(page);
  await openCase(page,/PK-001.*Econcity Private Limited/);
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();await expect(page.getByText('COMPLETE result saved.',{exact:true})).toBeVisible({timeout:30_000});
  const later=await read('ECON-101');expect(later.current_result.action).toBe('CLOSE');expect(later.current_result.financial_facts.balance.minor_units).toBe('0');expect(later.lifecycle).toBe('OPEN');
  const history=await (await request.get(`/api/v1/investigations/${original.investigation_id}?demonstration_id=${did}`)).json();expect(history.result).toEqual(original);
});

test('an end user can preserve context-only evidence and gets a limited result without a false closure',async({page,request})=>{
  test.setTimeout(60_000);
  await startNew(page);
  await upload(page,'customers','01-customers.csv');await step(page,2);await upload(page,'invoices','02-invoices.csv');
  const did=await page.evaluate(()=>localStorage.getItem('selected_demonstration_id'));
  const data=await (await request.get(`/api/v1/demonstrations/${did}/intake`)).json();
  const cid=data.cases.find((c:any)=>c.invoice_id==='ECON-102').id;
  await step(page,4);await upload(page,'whatsapp','07-explore/supporting-context.txt',cid,true);await step(page,6);await cover(page);
  await openCase(page,/PK-002.*Econcity Private Limited/);
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();
  await expect(page.getByText('LIMITED result saved.',{exact:true})).toBeVisible({timeout:30_000});
  const view=await (await request.get(`/api/v1/cases/${cid}?demonstration_id=${did}`)).json();
  expect(view.current_result.status).toBe('LIMITED');expect(view.current_result.reason_code).toBe('MISSING_EXTRACTION');
  expect(view.current_result.financial_facts.balance.minor_units).toBe('4000000');expect(view.allowed_commands.close.allowed).toBe(false);
  await page.getByRole('button',{name:'History',exact:true}).click();
  await expect(page.getByRole('button',{name:'Review case closure',exact:true})).toBeDisabled();
});
