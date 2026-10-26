import {test,expect,type Page} from './support/test';

test.use({actionTimeout:10_000});
const day=(offset:number)=>new Date(Date.now()+offset*86400000).toISOString().slice(0,10);
async function file(page:Page,kind:string,text:string,cid?:string,role='CUSTOMER'){
  await page.getByRole('combobox',{name:'File type',exact:true}).selectOption(kind);
  if(cid)await page.getByRole('combobox',{name:'Attach communication to invoice',exact:true}).selectOption(cid);
  await page.getByLabel('Upload file').setInputFiles({name:kind==='whatsapp'?'reviewed.txt':'reviewed.csv',mimeType:'text/plain',buffer:Buffer.from(text)});
  if(cid)await page.getByRole('combobox',{name:'Who sent this message?',exact:true}).selectOption(role);
}
// Navigation only: open the given step of the Upload page stepper.
async function step(page:Page,n:number){
  await page.getByRole('navigation',{name:'Upload steps'}).getByRole('link',{name:new RegExp(`^Step ${n} `)}).click();
  await expect(page.getByRole('heading',{level:2,name:new RegExp(`^Step ${n} ·`)})).toBeVisible();
}
async function preview(page:Page){await page.getByRole('button',{name:'Preview file',exact:true}).click();await expect(page.getByRole('heading',{name:'Import preview'})).toBeVisible();}
async function confirm(page:Page){
  await expect(page.locator('.intake-preview [role=alert]')).toHaveCount(0);
  await page.getByLabel('I reviewed this preview and confirm these are fictional sample records.').check();
  await page.getByRole('button',{name:'Confirm import',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview'})).toHaveCount(0);
}

test('reviewed senders, raw bank credit, unsafe wording, rupee weekday and Hinglish reach trustworthy saved advice',async({page,request})=>{
  test.setTimeout(120_000);
  const discovered=page.waitForResponse(r=>r.url().endsWith('/api/v1/demonstrations')&&r.request().method()==='GET');
  await page.goto('/#/upload?step=1');await discovered;await expect(page.getByText('Loading saved demonstrations…',{exact:true})).toHaveCount(0);
  await expect(page.getByRole('combobox',{name:'File type',exact:true})).toBeVisible();
  const fresh=page.getByLabel('Create a new imported workspace instead');if(await fresh.count())await fresh.check();
  await file(page,'customers','customer_id,customer_name\nECON,Econcity Private Limited\n');await preview(page);await confirm(page);
  const did=await page.evaluate(()=>localStorage.getItem('selected_demonstration_id'));
  await step(page,2);await file(page,'invoices',`invoice_id,customer_id,amount,currency,issued_at,due_at\nEV-101,ECON,1000,INR,${day(-90)},${day(-30)}\nEV-102,ECON,1000,INR,${day(-60)},${day(-20)}\n`);await preview(page);await confirm(page);
  const state=async()=>(await (await request.get(`/api/v1/demonstrations/${did}/intake`)).json());
  let data=await state();const first=data.cases.find((c:any)=>c.invoice_id==='EV-101').id,second=data.cases.find((c:any)=>c.invoice_id==='EV-102').id;
  await step(page,3);await file(page,'payments',`Date,Description,Credit,Debit\n${day(-5)},Econcity deposit,400.25,\n${day(-4)},Expense,,20\n`);await preview(page);
  await expect(page.locator('.intake-preview')).toContainText('generated source fingerprints');
  await expect(page.locator('.intake-preview')).toContainText('Skipped row');await confirm(page);
  data=await state();expect(data.payments).toHaveLength(1);expect(data.payments[0].allocations).toEqual([]);expect(data.payments[0].status).toBe('UNKNOWN');
  await step(page,5);const ref=data.payments[0].transaction_ref,receipt=page.locator('.intake-receipt').filter({has:page.getByRole('heading',{name:ref,exact:true})});
  await receipt.getByRole('combobox',{name:`Invoice for ${ref}`,exact:true}).selectOption(first);
  await receipt.getByLabel('I checked this settled receipt and its invoice allocation.').check();
  await receipt.getByRole('button',{name:`Confirm allocation for ${ref}`,exact:true}).click();await expect(receipt).toContainText('Fully allocated');
  await step(page,4);const source=(body:string)=>`Sender: Econ accounts\nSent: ${day(-1)}T10:00:00+05:30\n${body}\n`;
  for(const [role,text] of [['OWNER',`We will pay INR 599.75 by ${day(10)}.`],['CUSTOMER',`We will pay INR 599.75 by ${day(10)} after finance approval.`],['CUSTOMER',`She said: "We will pay INR 599.75 by ${day(10)}."`]]){
    const before=await state();await file(page,'whatsapp',source(text),first,role);await preview(page);
    await expect(page.locator('.intake-preview [role=alert]')).toBeVisible();await expect(page.getByRole('button',{name:'Confirm import',exact:true})).toHaveCount(0);expect(await state()).toEqual(before);
  }
  await file(page,'whatsapp',source('We will pay ₹599.75 by next Friday.'),first);await preview(page);
  await expect(page.locator('.intake-preview')).toContainText('strictly next occurrence');await expect(page.getByText('Interpreted currency',{exact:true})).toBeVisible();await confirm(page);
  await file(page,'whatsapp',source(`Hum INR 1000 ${day(10)} ko pay kar denge.`),second);await preview(page);await confirm(page);
  await step(page,6);const rows=page.locator('.intake-invoice');for(let i=0;i<await rows.count();i++){const row=rows.nth(i);await row.getByRole('checkbox').check();await row.getByRole('button',{name:/Confirm ledger review/}).click();await expect(row).toContainText('Payment records reviewed through');}
  await page.getByRole('button',{name:'Start morning review',exact:true}).click();
  await expect(page.getByText('Review complete. Choose a case to see its recommendation.')).toBeVisible({timeout:45_000});
  for(const [cid,balance] of [[first,'59975'],[second,'100000']]){
    const view=await (await request.get(`/api/v1/cases/${cid}?demonstration_id=${did}`)).json();expect(view.current_result.action).toBe('WAIT');expect(view.current_result.financial_facts.balance).toEqual({currency:'INR',minor_units:balance});expect(view.lifecycle).toBe('OPEN');expect(view.draft_reviews).toEqual([]);
  }
  await page.screenshot({path:'.runtime/eval-fixes/reviewed-intake.png'});
});
