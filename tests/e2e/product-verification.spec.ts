import {mkdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {test,expect,type Page} from './support/test';

const shots=fileURLToPath(new URL('../../.runtime/product-ux-shots/',import.meta.url));
mkdirSync(shots,{recursive:true});
const unwanted=/\bdemo(?:nstration)?s?\b|\bfictional\b|\bsample\b|course-demo|START-HERE|docs\//i;
async function preview(page:Page,name:string,content:string){
  await page.getByLabel('Upload file',{exact:true}).setInputFiles({name,mimeType:'text/csv',buffer:Buffer.from(content)});
  await page.getByRole('button',{name:'Preview file',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview',exact:true})).toBeVisible();
}
async function confirm(page:Page){
  await expect(page.locator('.intake-preview [role=alert]')).toHaveCount(0);
  await page.getByLabel('I reviewed this preview and confirm the records are correct.',{exact:true}).check();
  await page.getByRole('button',{name:'Confirm import',exact:true}).click();
  await expect(page.getByRole('heading',{name:'Import preview',exact:true})).toHaveCount(0);
}

test('product verification surfaces use uploads and neutral wording on desktop and mobile',async({page,request})=>{
  test.setTimeout(90_000);
  await page.goto('/#/dashboard');
  await page.getByRole('button',{name:/^Workspace/}).click();
  await page.getByRole('link',{name:'New workspace',exact:true}).click();
  await preview(page,'customers.csv','customer_id,customer_name\nC1,Cobalt Services\n');
  await confirm(page);
  const did=await page.evaluate(()=>localStorage.getItem('selected_demonstration_id'));
  expect(did).toBeTruthy();
  await page.getByRole('link',{name:/^Step 2 /}).click();
  const header='invoice_id,customer_id,amount,currency,issued_at,due_at\n';
  await preview(page,'invoices.csv',header+Array.from({length:7},(_,i)=>`INV-${i+1},C1,1200,INR,2026-10-01,2026-10-20`).join('\n'));
  await expect(page.locator('.intake-preview [role=alert]')).toContainText('Up to six invoices are supported per workspace.');
  expect(await page.locator('body').innerText()).not.toMatch(unwanted);
  await preview(page,'invoices.csv',header+'INV-1,C1,1200,INR,2026-10-01,2026-10-20\n');
  await confirm(page);
  const response=await request.get(`/api/v1/demonstrations/${did}/cases`);
  expect(response.status()).toBe(200);
  const cid=(await response.json()).cases[0].id;
  const routes=[['dashboard','#/dashboard'],['cases','#/cases'],['assistant','#/assistant'],['approvals','#/approvals'],['case',`#/cases/${cid}`],['history',`#/cases/${cid}?section=history`],...[1,2,3,4,5,6].map(n=>[`upload-${n}`,`#/upload?step=${n}`])];
  for(const width of [1440,390]){
    await page.setViewportSize({width,height:900});
    for(const [name,hash] of routes){
      await page.goto(`/${hash}`);
      await expect(page.getByRole('heading',{level:1})).toBeVisible();
      await expect(page.getByText('Loading saved workspaces…',{exact:true})).toHaveCount(0);
      await expect(page.locator('.workspace-toggle')).toContainText('Imported records');
      await expect(page.getByText(/Internal verification environment/)).toBeVisible();
      expect(await page.locator('body').innerText()).not.toMatch(unwanted);
      await expect(page.locator('a[href*="/samples/"]')).toHaveCount(0);
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
      await page.screenshot({path:`${shots}${name}-${width}.png`,fullPage:true});
    }
    await expect(page.getByRole('button',{name:/^Workspace/})).toHaveAttribute('aria-expanded','false');
    await page.getByRole('button',{name:/^Workspace/}).click();
    await expect(page.getByRole('combobox',{name:'Workspace',exact:true})).toHaveValue(did!);
    await page.getByText('Workspace details',{exact:true}).click();
    await page.getByText('Delete workspace',{exact:true}).click();
    await page.getByRole('button',{name:'Review workspace deletion',exact:true}).click();
    await expect(page.getByRole('button',{name:'Delete this workspace',exact:true})).toBeDisabled();
    expect(await page.locator('body').innerText()).not.toMatch(unwanted);
    await page.screenshot({path:`${shots}workspace-${width}.png`,fullPage:true});
    await page.getByRole('button',{name:/^Workspace/}).click();
  }
});
