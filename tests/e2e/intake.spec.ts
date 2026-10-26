import {test,expect,type Page} from './support/test';
import {fileURLToPath} from 'node:url';

test.use({actionTimeout:10_000});

const sample=(name:string)=>fileURLToPath(new URL(`../../docs/demo-import/${name}`,import.meta.url));
async function upload(page:Page,kind:string,file:string,cid?:string){
  await page.getByRole('combobox',{name:'File type',exact:true}).selectOption(kind);
  if(cid)await page.getByRole('combobox',{name:'Attach communication to invoice',exact:true}).selectOption(cid);
  await page.getByLabel('Upload file').setInputFiles(sample(file));
  if(['customer_email','remittance_email','whatsapp'].includes(kind))await page.getByRole('combobox',{name:'Who sent this message?',exact:true}).selectOption('CUSTOMER');
  await page.getByRole('button',{name:'Preview file',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview'})).toBeVisible();
  await expect(page.locator('.intake-preview [role=alert]')).toHaveCount(0);
  if(['customer_email','remittance_email','whatsapp'].includes(kind))await expect(page.locator('.intake-extracted blockquote').first()).toBeVisible();
  await page.getByLabel('I reviewed this preview and confirm the records are correct.').check();
  if(kind==='allocations')await page.getByLabel('I checked the settled receipts and the existing invoice allocations in this export.').check();
  await page.getByRole('button',{name:'Confirm import',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview'})).toHaveCount(0);
  await expect(page.locator('.intake-workspace-summary')).toBeVisible();
}
async function allocate(page:Page,ref:string,cid:string){
  const receipt=page.locator('.intake-receipt').filter({has:page.getByRole('heading',{name:ref,exact:true})});
  await receipt.getByRole('combobox',{name:`Invoice for ${ref}`,exact:true}).selectOption(cid);
  await receipt.getByLabel('I checked this settled receipt and its invoice allocation.').check();
  await receipt.getByRole('button',{name:`Confirm allocation for ${ref}`,exact:true}).click();
  await expect(receipt).toContainText('Fully allocated');
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
async function coverage(page:Page){
  const rows=page.locator('.intake-invoice');
  for(let i=0;i<await rows.count();i++){
    const row=rows.nth(i),button=row.getByRole('button',{name:/^Confirm ledger review for/});
    if(await button.count()){
      await row.getByRole('checkbox').check();await button.click();
      await expect(row).toContainText('Payment records reviewed through');
    }
  }
}

test('separate files cover onboarding, matching, messages, morning review, approval and delayed settlement',async({page,request,context})=>{
  test.setTimeout(180_000); // Full six-step journey; individual product deadlines are unchanged.
  await context.grantPermissions(['clipboard-read','clipboard-write']);
  await page.setViewportSize({width:1280,height:850});await page.goto('/#/upload?step=1');
  await upload(page,'customers','customers.csv');
  const did=await page.evaluate(()=>localStorage.getItem('selected_demonstration_id'));
  expect(did).toBeTruthy();
  await step(page,2);await upload(page,'invoices','invoices.csv');
  await step(page,3);await upload(page,'payments','payments-initial.csv');
  const endpoint=`/api/v1/demonstrations/${did}/intake`;
  const data=await (await request.get(endpoint)).json();
  expect(data.cases.map((c:any)=>c.invoice_id)).toEqual(['EC-101','EC-102','AD-201']);
  expect(data.payments.every((p:any)=>p.allocations.length===0)).toBe(true);
  const econ=data.cases[0].id,promise=data.cases[1].id,acme=data.cases[2].id;
  await step(page,5);
  await page.locator('.intake-receipt').filter({has:page.getByRole('heading',{name:'ECON-T1',exact:true})}).getByText(/^Review suggested invoices/).click();
  await expect(page.locator('.intake-candidate').first()).toContainText('Econcity Private Limited');
  await page.screenshot({path:'.runtime/csv-reconciliation-demo/import-desktop.png',fullPage:true});
  await page.screenshot({path:'.runtime/csv-reconciliation-demo/import-desktop-viewport.png'});
  await page.getByText('Optional: import existing allocations',{exact:true}).click();
  await upload(page,'allocations','allocations.csv');
  await allocate(page,'ECON-T1',econ);await allocate(page,'ECON-T2',econ);
  await step(page,4);
  for(const [kind,file,cid] of [
    ['remittance_email','remittance-email.eml',econ],['customer_email','customer-promise.eml',promise],
    ['customer_email','customer-payment-claim.eml',econ],['whatsapp','whatsapp-promise.txt',acme],
    ['whatsapp','whatsapp-paid.txt',econ]])await upload(page,kind,file,cid);
  await step(page,6);await coverage(page);
  await page.getByText(/^Original uploaded files and communication/).click();
  await page.getByText('Inspect original file: remittance-email.eml',{exact:true}).click();
  await expect(page.locator('.intake-original').filter({hasText:'Inspect original file: remittance-email.eml'}).locator('pre')).toContainText('UTR: ECON-T1.');
  await page.setViewportSize({width:390,height:850});
  await page.addStyleTag({content:'html{font-size:200%}'});
  expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
  await page.screenshot({path:'.runtime/csv-reconciliation-demo/import-mobile.png',fullPage:true});
  await page.locator('.upload-stepper').scrollIntoViewIfNeeded();
  await page.screenshot({path:'.runtime/csv-reconciliation-demo/import-mobile-viewport.png'});
  await page.setViewportSize({width:1280,height:850});await page.addStyleTag({content:'html{font-size:100%}'});
  await page.getByRole('button',{name:'Start morning review',exact:true}).click();
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.')).toBeVisible({timeout:45_000});
  const read=async(cid:string)=>(await request.get(`/api/v1/cases/${cid}?demonstration_id=${did}`)).json();
  const before=await read(econ);
  expect(before.current_result.action).toBe('VERIFY_PAYMENT');
  expect((await read(promise)).current_result.action).toBe('WAIT');
  const follow=await read(acme);expect(follow.current_result.action).toBe('FOLLOW_UP');
  await openCase(page,/PK-003.*Acme Design Studio/);
  await expect(page.getByRole('heading',{name:'Communication review'})).toBeVisible();
  await page.getByRole('button',{name:'Approve exact saved version',exact:true}).click();
  await page.getByRole('button',{name:'Copy approved message',exact:true}).click();
  expect((await page.evaluate(()=>navigator.clipboard.readText())).replaceAll('\r\n','\n')).toBe(follow.draft.exact_text);
  await step(page,3);
  await upload(page,'payments','payments-later.csv');
  // The earlier approval no longer offers a copy once new records arrive (checked where that case shows its message review).
  await openCase(page,/PK-003.*Acme Design Studio/);await expect(page.getByRole('heading',{name:'Communication review'})).toBeVisible();
  await expect(page.getByRole('button',{name:'Copy approved message',exact:true})).toHaveCount(0);
  await step(page,5);await allocate(page,'ECON-T3',econ);await step(page,6);await coverage(page);
  await openCase(page,/PK-001.*Econcity Private Limited/);
  await page.getByRole('button',{name:'Investigate case',exact:true}).click();
  await expect(page.getByText('COMPLETE result saved.',{exact:true})).toBeVisible({timeout:30_000});
  const after=await read(econ);
  expect(after.current_result.action).toBe('CLOSE');expect(after.lifecycle).toBe('OPEN');
  expect(after.current_result.financial_facts.balance.minor_units).toBe('0');
  expect(after.current_result.claims.every((c:any)=>c.resolved)).toBe(true);
  const original=await (await request.get(`/api/v1/investigations/${before.current_result.investigation_id}?demonstration_id=${did}`)).json();
  expect(original.result).toEqual(before.current_result);
  await page.getByRole('button',{name:'History',exact:true}).click();
  await page.getByRole('button',{name:'Review case closure',exact:true}).click();
  await page.locator('.confirmation-panel').getByRole('checkbox').check();
  await page.getByRole('button',{name:'Confirm case closure',exact:true}).click();
  await expect.poll(async()=>(await read(econ)).lifecycle).toBe('CLOSED');
  await page.reload();await expect(page.getByText('Imported data cutoff',{exact:true})).toBeVisible();
  expect((await (await request.get(endpoint)).json()).documents).toHaveLength(5);
});
