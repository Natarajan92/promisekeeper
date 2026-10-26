import {execFileSync} from 'node:child_process';
import {randomUUID} from 'node:crypto';
import {mkdirSync, readFileSync} from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {test, expect, type Page} from './support/test';

type Allocation={transaction_ref:string;invoice_id:string;amount:string;hint_required:boolean};
type Document={path:string;kind:string;invoice_id:string;sender_role:string};
type Expected={invoice_id:string;customer_name:string;action:string;balance_minor:string};
type Manifest={as_of:string;documents:Document[];allocations:Allocation[];expected:Expected[];refused:Document[];
  finale:{path:string;kind:string;invoice_id:string;action:string;balance_minor:string;allocations:Allocation[]}};

const repo=fileURLToPath(new URL('../../',import.meta.url));
const folder=path.join(repo,'.runtime/course-demo-e2e');
const shots=path.join(repo,'.runtime/ux-shots');
let manifest:Manifest;

test.use({actionTimeout:10_000,viewport:{width:1440,height:900}});
test.beforeAll(()=>{
  mkdirSync(folder,{recursive:true});mkdirSync(shots,{recursive:true});
  // The production generator uses today's IST date when --as-of is omitted.
  execFileSync(path.join(repo,'backend/.venv/Scripts/python.exe'),
    ['-m','promisekeeper.fixtures.course_demo_pack','--out',folder],
    {cwd:repo,windowsHide:true,env:{...process.env,PK_AGENT_MODE:'STUB'}});
  manifest=JSON.parse(readFileSync(path.join(folder,'EXPECTED-RESULTS.json'),'utf8')) as Manifest;
  const today=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Kolkata',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  expect(manifest.as_of).toBe(today);
});

async function pageLink(page:Page,name:string){
  await page.getByRole('navigation',{name:'Pages'}).getByRole('link',{name:new RegExp(`^${name}`)}).click();
}

async function step(page:Page,number:number){
  if(!page.url().includes('#/upload'))await pageLink(page,'Upload');
  await page.getByRole('navigation',{name:'Upload steps'}).getByRole('link',{name:new RegExp(`^Step ${number} `)}).click();
  await expect(page.getByRole('heading',{level:2,name:new RegExp(`^Step ${number} ·`)})).toBeVisible();
}

async function preview(page:Page,kind:string,file:string,caseId?:string){
  await page.getByRole('combobox',{name:'File type',exact:true}).selectOption(kind);
  await page.getByLabel('Upload file',{exact:true}).setInputFiles(path.join(folder,file));
  if(caseId){
    await page.getByRole('combobox',{name:'Who sent this message?',exact:true}).selectOption('CUSTOMER');
    await page.getByRole('combobox',{name:'Attach communication to invoice',exact:true}).selectOption(caseId);
  }
  await page.getByRole('button',{name:'Preview file',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview',exact:true})).toBeVisible();
}

async function upload(page:Page,kind:string,file:string,caseId?:string){
  await preview(page,kind,file,caseId);
  await expect(page.locator('.intake-preview [role=alert]')).toHaveCount(0);
  if(caseId)await expect(page.locator('.intake-extracted blockquote').first()).toBeVisible();
  await page.getByLabel('I reviewed this preview and confirm these are fictional sample records.',{exact:true}).check();
  await page.getByRole('button',{name:'Confirm import',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview',exact:true})).toHaveCount(0);
  await expect(page.locator('.intake-workspace-summary')).toBeVisible();
}

async function allocate(page:Page,item:Allocation,ids:Record<string,string>){
  const receipt=page.locator('.intake-receipt').filter({has:page.getByRole('heading',{name:item.transaction_ref,exact:true})});
  if(item.hint_required){
    await receipt.getByText(/^Review suggested invoices/).click();
    await expect(receipt.locator('.intake-candidate').filter({hasText:item.invoice_id})).toBeVisible();
  }
  await receipt.getByRole('combobox',{name:`Invoice for ${item.transaction_ref}`,exact:true}).selectOption(ids[item.invoice_id]);
  await receipt.getByLabel(`Allocation amount for ${item.transaction_ref} (INR)`,{exact:true}).fill(item.amount);
  const confirm=receipt.getByRole('button',{name:`Confirm allocation for ${item.transaction_ref}`,exact:true});
  await expect(confirm).toBeDisabled();
  await receipt.getByLabel('I checked this settled receipt and its invoice allocation.',{exact:true}).check();
  await confirm.click();
  await expect(receipt).toContainText('Fully allocated');
}

async function coverage(page:Page){
  const rows=page.locator('.intake-invoice');
  await expect(rows).toHaveCount(6);
  for(let index=0;index<6;index++){
    const row=rows.nth(index);
    const confirm=row.getByRole('button',{name:/^Confirm ledger review for/});
    await expect(confirm).toBeDisabled();
    await row.getByRole('checkbox').check();
    await confirm.click();
    await expect(row).toContainText('Payment records reviewed through');
  }
}

async function screenshot(page:Page,name:string){
  expect(page.viewportSize()).toEqual({width:1440,height:900});
  await page.evaluate(()=>window.scrollTo(0,0));
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:path.join(shots,`course-demo-${name}.png`)});
  await page.screenshot({path:path.join(shots,`course-demo-${name}-full.png`),fullPage:true});
}

test('course demo pack runs end to end through every page',async({page,request,context})=>{
  test.setTimeout(180_000); // Six upload steps and the later-statement finale, as in the existing intake journey.
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  const health=await (await request.get('/api/v1/health')).json();
  expect(health.agent_mode).toBe('STUB');
  // Retain a separate imported workspace to prove "New upload workspace" never appends to it.
  const originalCommand={schema_version:'1',operation_id:randomUUID(),kind:'customers',filename:'01-customers.csv',
    content:readFileSync(path.join(folder,'01-customers.csv'),'utf8'),demonstration_id:null};
  const originalPreview=await request.post('/api/v1/intake/previews',{headers:{'X-PromiseKeeper-Request':'1'},data:originalCommand});
  expect(originalPreview.ok()).toBe(true);
  const originalChecked=await originalPreview.json();expect(originalChecked.errors).toEqual([]);
  const originalCommit=await request.post('/api/v1/intake/commits',{headers:{'X-PromiseKeeper-Request':'1'},
    data:{...originalCommand,operation_id:randomUUID(),confirmed_preview_hash:originalChecked.preview_hash,confirm:true,fictional_data:true,settled_confirmed:false}});
  expect(originalCommit.ok()).toBe(true);
  const originalDid=(await originalCommit.json()).demonstration_id;
  expect(originalDid).toBeTruthy();
  const originalUrl=`/api/v1/demonstrations/${originalDid}/intake`;
  const originalResponse=await request.get(originalUrl);expect(originalResponse.ok()).toBe(true);
  const originalSnapshot=await originalResponse.json();
  await page.addInitScript(id=>localStorage.setItem('selected_demonstration_id',id),originalDid);
  const discovered=page.waitForResponse(response=>response.url().endsWith('/api/v1/demonstrations')&&response.request().method()==='GET');
  await page.goto('/#/dashboard');await discovered;
  await expect(page.getByText('Loading saved demonstrations…',{exact:true})).toHaveCount(0);
  await page.getByRole('button',{name:/^Workspace/}).click();
  await expect(page.getByRole('combobox',{name:'Demonstration copy',exact:true})).toHaveValue(originalDid);
  await page.getByRole('link',{name:'New upload workspace',exact:true}).click();
  await expect(page.getByRole('heading',{level:1,name:'Bring in your records',exact:true})).toBeVisible();
  await expect(page.getByRole('combobox',{name:'File type',exact:true})).toBeVisible();
  expect(await page.evaluate(()=>localStorage.getItem('selected_demonstration_id'))).toBeNull();
  await expect(page.getByLabel('Create a new imported workspace instead',{exact:true})).toHaveCount(0);
  await upload(page,'customers','01-customers.csv');
  const did=await page.evaluate(()=>localStorage.getItem('selected_demonstration_id'));
  expect(did).toBeTruthy();expect(did).not.toBe(originalDid);
  expect(await (await request.get(originalUrl)).json()).toEqual(originalSnapshot);
  const intakeUrl=`/api/v1/demonstrations/${did}/intake`;
  const state=async()=>{
    const response=await request.get(intakeUrl);expect(response.ok()).toBe(true);return response.json();
  };
  await step(page,2);await upload(page,'invoices','02-invoices.csv');
  await step(page,3);await upload(page,'payments','03-bank-statement.csv');
  const initial=await state();
  const ids:Record<string,string>=Object.fromEntries(initial.cases.map((item:any)=>[item.invoice_id,item.id]));
  expect(initial.cases).toHaveLength(6);
  expect(initial.payments).toHaveLength(3); // The bank statement's debit is intentionally skipped.
  expect(initial.payments.every((payment:any)=>payment.allocations.length===0)).toBe(true);
  expect(initial.payments.map((payment:any)=>payment.transaction_ref).sort()).toEqual(manifest.allocations.map(item=>item.transaction_ref).sort());

  await step(page,4);
  for(const document of manifest.documents)await upload(page,document.kind,document.path,ids[document.invoice_id]);
  const beforeRefusal=await state();
  const refused=manifest.refused[0];
  await preview(page,refused.kind,refused.path,ids[refused.invoice_id]);
  await expect(page.locator('.intake-preview [role=alert]')).toBeVisible();
  await expect(page.getByRole('button',{name:'Confirm import',exact:true})).toHaveCount(0);
  expect(await state()).toEqual(beforeRefusal);

  await step(page,5);
  await expect(page.getByText('Name and address similarities are suggestions. A confirmed customer still needs an explicit invoice allocation.',{exact:true})).toBeVisible();
  for(const allocation of manifest.allocations)await allocate(page,allocation,ids);
  const matched=await state();
  expect(matched.payments.every((payment:any)=>payment.remaining_minor==='0')).toBe(true);
  expect(matched.cases.find((item:any)=>item.invoice_id==='MT-1001').remaining_minor).toBe('4800000');
  await step(page,6);await coverage(page);
  await expect(page.getByRole('button',{name:'Start morning review',exact:true})).toBeEnabled();
  await screenshot(page,'upload');
  await page.getByRole('button',{name:'Start morning review',exact:true}).click();
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.',{exact:true})).toBeVisible({timeout:45_000});
  const readCase=async(invoice:string)=>{
    const response=await request.get(`/api/v1/cases/${ids[invoice]}?demonstration_id=${did}`);
    expect(response.ok()).toBe(true);return response.json();
  };
  for(const expected of manifest.expected){
    const view=await readCase(expected.invoice_id);
    expect(view.current_result.action).toBe(expected.action);
    expect(view.current_result.financial_facts.balance.minor_units).toBe(expected.balance_minor);
    expect(view.freshness).toBe('CURRENT');expect(view.lifecycle).toBe('OPEN');
  }
  const originalArun=(await readCase(manifest.finale.invoice_id)).current_result;
  const meera=await readCase('MT-1001');
  const savedDraft=meera.draft.exact_text;
  expect(savedDraft).toBeTruthy();

  await page.getByRole('link',{name:'Go to Dashboard',exact:true}).click();
  const total=manifest.expected.reduce((sum,item)=>sum+BigInt(item.balance_minor),0n);
  const totalText=new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(total)/100);
  await expect(page.getByRole('region',{name:'Still to collect',exact:true}).locator('.dash-total-amount')).toHaveText(totalText);
  await expect(page.getByRole('list',{name:'Follow up today',exact:true})).toContainText('Meera Textiles');
  await screenshot(page,'dashboard');

  await pageLink(page,'Cases');
  await expect(page.getByRole('heading',{level:1,name:'Cases',exact:true})).toBeVisible();
  await screenshot(page,'cases');
  await page.getByRole('button',{name:/PK-001.*Meera Textiles/}).click();
  await expect(page.getByRole('heading',{level:1,name:'Meera Textiles',exact:true})).toBeVisible();
  const quote=readFileSync(path.join(folder,'04-messages/meera-whatsapp-hinglish.txt'),'utf8').split('\n').find(line=>line.startsWith('Hum '));
  expect(quote).toBeTruthy();
  await expect(page.getByRole('region',{name:'What happened',exact:true}).locator('blockquote')).toContainText(quote!);
  await expect(page.locator('.suggestion-card').getByText('Our suggestion',{exact:true})).toBeVisible();
  await expect(page.locator('.suggestion-card').getByRole('heading',{level:2,name:'Follow up on the overdue balance',exact:true})).toBeVisible();
  await screenshot(page,'case');

  await pageLink(page,'Approvals');
  await expect(page.getByRole('heading',{level:1,name:'Your approvals',exact:true})).toBeVisible();
  const meeraApproval=page.locator('.approval-items').getByRole('link').filter({hasText:'Meera Textiles'});
  await expect(meeraApproval).toContainText('Reminder');
  await meeraApproval.click();
  await expect(page.getByLabel('Draft text',{exact:true})).toHaveValue(savedDraft);
  await page.getByRole('button',{name:'Approve exact saved version',exact:true}).click();
  await expect(page.getByRole('button',{name:'Copy approved message',exact:true})).toBeEnabled();
  await page.getByRole('button',{name:'Copy approved message',exact:true}).click();
  expect((await page.evaluate(()=>navigator.clipboard.readText())).replaceAll('\r\n','\n')).toBe(savedDraft);
  await expect(page.getByRole('region',{name:'Approved message handoff',exact:true})).toContainText('Nothing has been sent.');
  const approved=await readCase('MT-1001');
  expect(approved.review_state).toBe('APPROVED');expect(approved.draft.exact_text).toBe(savedDraft);
  await screenshot(page,'approvals');

  await pageLink(page,'Assistant');
  await expect(page.getByRole('heading',{level:1,name:'Assistant at work',exact:true})).toBeVisible();
  const team=page.getByRole('region',{name:'Your digital team',exact:true});
  await expect(team).toBeVisible();
  await expect(team.getByRole('list',{name:'Your digital team',exact:true}).getByRole('listitem')).toHaveCount(10);
  const plan=page.getByRole('list',{name:"Today's plan",exact:true});
  await expect(plan.getByRole('listitem')).toHaveCount(6);
  for(const expected of manifest.expected)await expect(plan).toContainText(expected.customer_name);
  await page.getByRole('combobox',{name:'Case to follow',exact:true}).selectOption(ids['MT-1001']);
  await expect(page.getByRole('list',{name:'Steps for Meera Textiles',exact:true})).toBeVisible();
  await screenshot(page,'assistant');

  await step(page,3);await upload(page,manifest.finale.kind,manifest.finale.path);
  await step(page,5);
  for(const allocation of manifest.finale.allocations)await allocate(page,allocation,ids);
  await step(page,6);await coverage(page);
  await pageLink(page,'Cases');
  await page.getByRole('button',{name:/PK-002.*Arun Traders/}).click();
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();
  await expect(page.getByText('COMPLETE result saved.',{exact:true})).toBeVisible({timeout:30_000});
  const finale=await readCase(manifest.finale.invoice_id);
  expect(finale.current_result.action).toBe(manifest.finale.action);
  expect(finale.current_result.financial_facts.balance.minor_units).toBe(manifest.finale.balance_minor);
  expect(finale.current_result.claims).toHaveLength(1);
  expect(finale.current_result.claims.every((claim:any)=>claim.resolved)).toBe(true);
  expect(finale.lifecycle).toBe('OPEN'); // A Close suggestion still requires explicit owner closure.
  await expect(page.locator('.suggestion-card').getByRole('heading',{level:2,name:'Review case closure',exact:true})).toBeVisible();
  const history=await request.get(`/api/v1/investigations/${originalArun.investigation_id}?demonstration_id=${did}`);
  expect(history.ok()).toBe(true);expect((await history.json()).result).toEqual(originalArun);
  expect(await (await request.get(originalUrl)).json()).toEqual(originalSnapshot);
  await screenshot(page,'arun-finale');
});
